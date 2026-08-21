#!/usr/bin/env python
"""Run one assembled scenario x day type, deterministically and resumably.

Takes a set out of `scenarios/matsim/<S>/<DAY>/` and runs it at a sample
fraction, writing everything derived into the run directory so the committed
inputs are never modified in place. A run is identified by its own parameters,
so re-invoking with the same ones is a no-op rather than a repeat.

**Resumable, not restartable.** MATSim has no mid-run checkpoint, so "resume"
here means: a completed run is detected and skipped. A run that died leaves no
`_run.json` and is repeated from the start.

**Deterministic.** One seed, fixed thread count recorded in the run record
(MATSim's mobsim partitions by thread count, so it is part of the run's
identity, not a performance knob), and a nested hash-based subsample.

**It cannot read a validation target.** This module opens the scenario inputs,
the plans and the toolchain. Nothing else. The fit statistic lives in
`src/calibrate/`, and the holdout rows are never opened by either.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'analyse'))
from sample_population import subsample_plans, scale_transit_capacity  # noqa: E402
import registry  # noqa: E402
# The run emits its config through the SAME registry-driven path the builder
# uses. Importing the builder is deliberate: two code paths writing one config
# is how the shipped config and the run config came to disagree.
sys.path.insert(0, os.path.join(HERE, '..', 'build'))
import build_matsim_run_inputs as build_inputs  # noqa: E402
import city  # noqa: E402
import summarise_run  # noqa: E402
from registry import outputs  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
JAVA = os.path.join(REPO, '.tools', 'jdk', 'bin', 'java.exe')
JAR = os.path.join(REPO, '.tools', 'jars', 'pt2matsim-26.6-shaded.jar')
CLASSES = os.path.join(REPO, '.tools', 'classes')
# Our entry point, not MATSim's: it rebinds PermissibleModesCalculator so `ride`
# can be withheld from a person with nobody to drive them (DECISIONS.md 15,
# src/java/citysim/). The pinned jar is unchanged - this ADDS classes beside it.
MAIN = 'citysim.CitysimControler'
JAVA_SRC = os.path.join(REPO, 'src', 'java')


def controler_sha256():
    """Hash the committed source of the entry point this run will execute.

    The run name is built from the scenario and the registry values, so it
    cannot see the controler. That was harmless while the controler only
    rebound ride availability; issue #28 made it decide how `ride` gets its
    travel time, which moves every mode share. A result produced before that
    change and one produced after are different results with the same name, so
    the run record carries this and `main` refuses to resume across a change.

    Sources are hashed, not the compiled classes: javac output is not
    guaranteed byte-identical across JDK builds, and the source is what is
    committed and reviewable.
    """
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(JAVA_SRC, '*', '*.java'))):
        h.update(os.path.basename(p).encode('utf-8'))
        with open(p, 'rb') as f:
            h.update(f.read())
    return h.hexdigest()


SETS = city.path('scenarios', 'matsim')
PLANS = city.path('demand', 'plans', 'matsim')
RESULTS = os.path.join(REPO, 'results')


def fwd(p):
    return p.replace(os.sep, '/')


def setp(text, name, value, count=1):
    return re.sub(r'(<param name="%s" value=")[^"]*(")' % re.escape(name),
                  lambda m: m.group(1) + str(value) + m.group(2), text, count=count)


def set_mode_param(text, mode, name, value):
    """Set one scoring parameter inside a specific modeParams block."""
    pat = (r'(<parameterset type="modeParams">\s*<param name="mode" value="%s"[^>]*>'
           r'(?:(?!</parameterset>).)*?<param name="%s" value=")[^"]*(")'
           % (re.escape(mode), re.escape(name)))
    new, n = re.subn(pat, lambda m: m.group(1) + str(value) + m.group(2),
                     text, count=1, flags=re.S)
    if not n:
        raise SystemExit('no modeParams/%s/%s in the config' % (mode, name))
    return new


def build_config(src_dir, run_dir, scenario, day, fraction, seed, overrides, cfg):
    """EMIT this run's config from this run's resolution, not patch the shipped one.

    It used to read the committed `config.xml` and rewrite six parameters into
    it. That meant a run overlay could only ever move those six: any other field
    it set was accepted by the resolver, validated against its sweep, written
    into `_config.json` as the run's provenance - and could not reach the model,
    because the shipped config still carried the builder's value. The snapshot
    said one thing and the run did another, which is this repository's signature
    defect wearing the provenance record as a disguise.

    The config is now built from the SAME registry-driven emitter the builder
    uses, against the scenario, day, run overlay, environment and --set layers
    this run actually resolved. Every declared field reaches the model or the
    closure check fails.
    """
    base = os.path.join(SETS, scenario)

    plans_src = os.path.join(PLANS, 'population_%s.xml.gz' % day)
    plans_dst = os.path.join(run_dir, 'plans.xml.gz')
    veh_src = os.path.join(src_dir, 'transitVehicles.xml.gz')
    veh_dst = os.path.join(run_dir, 'transitVehicles.xml.gz')
    if fraction >= 1.0:
        n_in = n_out = n_hhless = None
        plans_dst, veh_dst = plans_src, veh_src
        scaled = []
    else:
        n_in, n_out, n_hhless = subsample_plans(
            plans_src, plans_dst, fraction, seed,
            cfg.get('RUN.sample.unit'))
        # The sampling UNIT is declared (DECISIONS.md 9.45). A person-wise
        # sample shreds households, and every household-coupled mechanism
        # then depends on the fraction rather than on the demand - which is
        # the one thing a sample fraction must not decide.
        # The switch DECIDES this now. It was declared as "not optional in
        # practice - at a 10% sample an unscaled bus carries 700 real people, so
        # capacity never binds and crowding silently disappears" and then read
        # by nothing, which is the failure it warns about.
        if cfg.get('RUN.sample.transit_capacity_scaling'):
            scaled = scale_transit_capacity(
                veh_src, veh_dst, fraction,
                cfg.get('RUN.sample.transit_capacity_floor'))
        else:
            shutil.copyfile(veh_src, veh_dst)
            scaled = []

    # The parking price table sits beside the scenario network, one per scenario.
    # Checked rather than assumed: a config that lost its price file would run
    # with free parking and look exactly like a correct run (issue #33).
    price_src = os.path.join(base, 'parking_prices.tsv')
    if not os.path.exists(price_src):
        raise SystemExit(
            'no parking price table at %s. Regenerate the run inputs with '
            'build_matsim_run_inputs.py.' % price_src)

    # Both capacity factors are identities on the sample fraction, and NEITHER
    # is a choice. Checked here, in 0.1 s, rather than in the JVM a second
    # later: MATSim's GlobalConfigGroup.checkConsistency throws when the two
    # differ by more than global.relativeTolerance, which defaults to 0.0.
    storage = fraction ** cfg.get('RUN.sample.storage_capacity_exponent')
    if abs(storage - fraction) > 1e-12:
        raise SystemExit(
            'storageCapacityFactor (%g) must equal flowCapacityFactor (%g). MATSim '
            'enforces this and states that raising storage above flow "is no longer '
            'needed since the qsim became a lot more deterministic". '
            'RUN.sample.storage_capacity_exponent is 1.0 by derivation, not by '
            'assumption - see DECISIONS.md 15.' % (storage, fraction))

    build_inputs.check_scoring_order(cfg)
    scoring = build_inputs.scoring_from_c1(
        cfg, json.load(open(build_inputs.PARAMS, encoding='utf-8')),
        purpose_share())
    # The per-main-mode vehicle types are REGENERATED from this run's own
    # resolution, not copied from the shipped set: B.freight.pce is a swept
    # field, and a run overlay moving it must move the truck the mobsim
    # actually loads (DECISIONS.md 9.49).
    mode_veh = build_inputs.write_mode_vehicles(
        os.path.join(run_dir, 'vehicles.xml'), cfg)
    paths = dict(
        output=fwd(os.path.join(run_dir, 'output')),
        network=fwd(os.path.join(base, 'network.xml.gz')),
        plans=fwd(plans_dst),
        schedule=fwd(os.path.join(src_dir, 'transitSchedule.xml.gz')),
        vehicles=fwd(veh_dst),
        mode_vehicles=fwd(mode_veh),
        parking_prices=fwd(price_src),
        fraction=fraction)
    config_path = build_inputs.write_config(
        os.path.join(run_dir, 'config.xml'), cfg, scoring, day, paths)

    # Raw MATSim overrides (`--set ride.constant=-3.4`) are applied after the
    # emission, deliberately: they are an escape hatch BELOW the registry, for
    # probing a parameter directly, and they are recorded in the run record so a
    # result carries them. A registry field must never be varied this way -
    # --config-set is checked against the declared sweep and this is not.
    if overrides:
        text = open(config_path, encoding='utf-8').read()
        for key, value in sorted(overrides.items()):
            if '.' in key:
                mode, name = key.split('.', 1)
                text = set_mode_param(text, mode, name, value)
            else:
                text = setp(text, key, value)
        open(config_path, 'w', encoding='utf-8', newline='\n').write(text)
    return config_path, dict(persons_in=n_in, persons_kept=n_out,
                             unit=cfg.get('RUN.sample.unit'),
                             persons_without_household=n_hhless,
                             transit_capacity_scaled=sorted(set(scaled)))


_PURPOSE_SHARE = {}


def purpose_share():
    """The HTS purpose weights the C1 translation is averaged over.

    Read from the run-inputs report the builder wrote, not recomputed: the
    weights come from a pandas read of the HTS tables, and a run should not
    depend on that at start-up. The DERIVED SCORING is still recomputed here
    against this run's own resolution, so a run overlay moving the transfer
    penalty moves utilityOfLineSwitch with it - which is the whole point of
    emitting rather than patching.
    """
    if not _PURPOSE_SHARE:
        report = os.path.join(SETS, '_run_inputs_report.json')
        if not os.path.exists(report):
            raise SystemExit(
                'no %s. The run inputs must be assembled before a run: '
                'python src/build/build_matsim_run_inputs.py' % report)
        doc = json.load(open(report, encoding='utf-8'))
        if 'purpose_share' not in doc:
            raise SystemExit(
                '%s predates the registry-driven config emitter and carries no '
                'purpose_share. Regenerate the run inputs.' % report)
        _PURPOSE_SHARE.update(doc['purpose_share'])
    return _PURPOSE_SHARE


ITER_RE = re.compile(r'### ITERATION (\d+) (BEGINS|ENDS)')
TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}),(\d{3})')


def iteration_times(log):
    """Wall seconds per iteration, from the controller's own markers."""
    import datetime as dt
    begins, out = {}, {}
    with open(log, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = ITER_RE.search(line)
            t = TS_RE.match(line)
            if not m or not t:
                continue
            ts = (dt.datetime.strptime(t.group(1), '%Y-%m-%dT%H:%M:%S').timestamp()
                  + int(t.group(2)) / 1000.0)
            if m.group(2) == 'BEGINS':
                begins[int(m.group(1))] = ts
            elif int(m.group(1)) in begins:
                out[int(m.group(1))] = round(ts - begins[int(m.group(1))], 2)
    return out


def resolve(scenario, day, run_config=None, set_overrides=None):
    """Resolve the input registry for this run, and fail loudly if it will not.

    `RUN.controler.last_iteration` is declared UNOBTAINED, so this raises unless
    the caller supplied one. That is deliberate: DECISIONS.md 9.7 shows 100 and
    250 are both measurably too low and no justified value has been measured, so
    the registry refuses to invent one rather than shipping another guess.
    """
    try:
        return registry.load(scenario=scenario, day=day, run=run_config,
                             set=set_overrides)
    except registry.RegistryError as e:
        raise SystemExit(str(e))


def start_live_view(run_dir, cfg):
    """Serve this run's live view and return its url, or None.

    One server per run, on its own port. `RUN.monitor.port` is the FIRST port
    tried, not the only one, so concurrent runs each get their own view instead
    of competing for a single fixed port.

    It can never stop a run. The server thread is a daemon and every failure
    here is reported and swallowed: a run that dies because its instrumentation
    could not bind a socket is worse than a run with no instrumentation. The
    import is deferred for the same reason - the view is optional, the run is
    not.
    """
    if not cfg.get('RUN.monitor.enabled'):
        return None
    try:
        import run_view                                   # noqa: PLC0415
        return run_view.serve(run_dir, port=cfg.get('RUN.monitor.port'),
                              poll_s=cfg.get('RUN.monitor.poll_s'),
                              background=True)
    except Exception as exc:                              # noqa: BLE001
        print('live view unavailable: %s' % exc, flush=True)
        return None


def run(scenario, day, cfg, overrides, tag=None, force=False):
    src_dir = os.path.join(SETS, scenario, day)
    if not os.path.isdir(src_dir):
        raise SystemExit('no run inputs at %s' % src_dir)

    fraction = cfg.get('RUN.sample.fraction')
    try:
        iterations = cfg.get('RUN.controler.last_iteration')
    except registry.RegistryError as e:
        raise SystemExit('%s\n\nSet it with --iterations N, --set '
                         'RUN.controler.last_iteration=N, or a run overlay.' % e)
    threads = cfg.get('RUN.machine.threads')
    xmx = cfg.get('RUN.machine.xmx')
    seed = cfg.get('RUN.machine.seed')

    name = tag or '%s_%s_f%s_i%d_s%d' % (scenario, day, ('%g' % fraction).replace('.', ''),
                                         iterations, seed)
    if overrides and not tag:
        name += '_' + '_'.join('%s%s' % (k.replace('.', ''), v)
                               for k, v in sorted(overrides.items()))
    run_dir = os.path.join(RESULTS, name)
    record = os.path.join(run_dir, '_run.json')
    controler = controler_sha256()
    if os.path.exists(record) and not force:
        prior = json.load(open(record, encoding='utf-8'))
        if prior.get('controler_sha256') == controler:
            print('resume: %s already complete' % name, flush=True)
            return prior
        # The run name is built from the scenario and the registry values, which
        # cannot see the controler's own source. Without this check a completed
        # run would be handed back after the model's behaviour had changed -
        # silently, and with no way to tell the two apart afterwards. Issue #28
        # changed how `ride` gets its travel time and moved every mode share, so
        # a stale result reused here would be indistinguishable from a real one.
        print('re-running %s: the controler changed since it was produced\n'
              '  recorded %s\n  current  %s'
              % (name, (prior.get('controler_sha256') or 'not recorded')[:16],
                 controler[:16]), flush=True)
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir, exist_ok=True)

    # `iterations`, `threads` and every other declared value reach the config
    # through `cfg`, not through this call: they are registry fields, and the
    # emitter reads them from the same resolution the snapshot records.
    config_path, sample = build_config(src_dir, run_dir, scenario, day, fraction,
                                       seed, overrides, cfg)
    snapshot = cfg.write_snapshot(os.path.join(run_dir, '_config.json'))
    log = os.path.join(run_dir, 'matsim.log')
    classpath = os.pathsep.join([JAR, CLASSES])
    # -Xms equal to -Xmx: the 9.57 arm grew the heap 7 -> 27 GB across the run
    # with full-GC stalls visible during the it-110 routing pathology; a
    # pre-sized heap removes the growth path. Wall-time only - the JVM heap
    # schedule cannot change a model output.
    cmd = [JAVA, '-Xms%s' % xmx, '-Xmx%s' % xmx, '-XX:+UseParallelGC',
           '-cp', classpath, MAIN, config_path]
    # The live view, announced before MATSim starts so the url is on screen for
    # the whole run rather than after it. It reads the run directory and never
    # writes to it.
    view_url = start_live_view(run_dir, cfg)
    print('live view: %s' % (view_url or 'disabled (RUN.monitor.enabled)'),
          flush=True)
    t0 = time.time()
    with open(log, 'w', encoding='utf-8', errors='replace') as lf:
        rc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                              cwd=run_dir).wait()
    wall = time.time() - t0
    if rc != 0:
        print('FAILED rc=%d after %.0fs - see %s' % (rc, wall, log), flush=True)
        return dict(name=name, rc=rc, wall_s=round(wall, 1))

    per = iteration_times(log)
    steady = sorted(v for k, v in per.items() if k > 0)
    doc = dict(name=name, scenario=scenario, day=day, fraction=fraction,
               iterations=iterations, threads=threads, xmx=xmx, seed=seed,
               overrides=overrides, rc=rc, wall_s=round(wall, 1),
               median_iteration_s=steady[len(steady) // 2] if steady else None,
               config_snapshot=os.path.relpath(snapshot, run_dir).replace(os.sep, '/'),
               controler_sha256=controler,
               **sample)
    # The run record must meet its declared contract before it is written; a
    # completed run without a config snapshot cannot state what produced it.
    try:
        outputs.write_checked(record, doc, 'run')
    except outputs.OutputError as e:
        raise SystemExit(str(e))
    print('%s rc=0 wall=%.0fs median iteration %.1fs'
          % (name, wall, doc['median_iteration_s'] or -1), flush=True)
    # A finished run should not leave its telemetry, its log and three JSON files
    # for someone to interpret. Close it out with a summary in both dialects -
    # `_summary.json` against its declared schema, and `SUMMARY.md` for a person.
    # It reports the state of the RUN and refuses to report a finding: no mode
    # share, no fit statistic, no validation target. A failure here is logged and
    # never raised, because the run itself succeeded and its record is written.
    try:
        summarise_run.summarise(run_dir)
    except Exception as e:                                   # noqa: BLE001
        print('summary could not be written: %s' % e, flush=True)
    return doc


def parse_override(s):
    key, _, value = s.partition('=')
    if not value:
        raise SystemExit('override must be key=value, got %r' % s)
    return key, value


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scenario', default='S2')
    ap.add_argument('--day', default='WEEKDAY', choices=['WEEKDAY', 'SAT', 'SUN'])
    ap.add_argument('--run-config', metavar='TAG',
                    help='a committed overlay under config/runs/<TAG>.json - the '
                         'reproducible way to vary a run')
    ap.add_argument('--fraction', type=float,
                    help='shorthand for --set RUN.sample.fraction=...')
    ap.add_argument('--iterations', type=int,
                    help='shorthand for --set RUN.controler.last_iteration=... . '
                         'There is still no default: DECISIONS.md 9.7 shows 100 and '
                         '250 are both too low, no justified value has been measured, '
                         'and the registry declares the field UNOBTAINED so it refuses '
                         'to invent one')
    ap.add_argument('--threads', type=int,
                    help='shorthand for --set RUN.machine.threads=...')
    ap.add_argument('--xmx', help='shorthand for --set RUN.machine.xmx=...')
    ap.add_argument('--seed', type=int, help='shorthand for --set RUN.machine.seed=...')
    ap.add_argument('--tag')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--config-set', action='append', default=[], metavar='KEY=VALUE',
                    help='registry override, e.g. RUN.sample.fraction=0.10. Checked '
                         'against the declared sweep; a held-fixed field is refused')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='MATSim config override; "ride.constant=-3.4" targets a '
                         'modeParams block, "brainExpBeta=2" a plain param')
    a = ap.parse_args()

    # the convenience flags are shorthand for registry overrides, so they go
    # through exactly the same sweep and held-fixed guards as everything else
    overrides = registry.parse_set(a.config_set)
    for flag, key in (('fraction', 'RUN.sample.fraction'),
                      ('iterations', 'RUN.controler.last_iteration'),
                      ('threads', 'RUN.machine.threads'),
                      ('xmx', 'RUN.machine.xmx'),
                      ('seed', 'RUN.machine.seed')):
        value = getattr(a, flag)
        if value is not None:
            overrides[key] = value

    cfg = resolve(a.scenario, a.day, a.run_config, overrides)
    run(a.scenario, a.day, cfg, dict(parse_override(s) for s in a.set),
        a.tag, a.force)


if __name__ == '__main__':
    main()
