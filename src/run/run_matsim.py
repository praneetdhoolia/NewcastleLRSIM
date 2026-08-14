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
from sample_population import subsample_plans, scale_transit_capacity, SEED  # noqa: E402
import registry  # noqa: E402
import summarise_run  # noqa: E402
from registry import outputs  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
JAVA = os.path.join(REPO, '.tools', 'jdk', 'bin', 'java.exe')
JAR = os.path.join(REPO, '.tools', 'jars', 'pt2matsim-26.6-shaded.jar')
CLASSES = os.path.join(REPO, '.tools', 'classes')
# Our entry point, not MATSim's: it rebinds PermissibleModesCalculator so `ride`
# can be withheld from a person with nobody to drive them (DECISIONS.md 15,
# src/java/wickham/). The pinned jar is unchanged - this ADDS classes beside it.
MAIN = 'wickham.WickhamControler'
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


SETS = os.path.join(REPO, 'scenarios', 'matsim')
PLANS = os.path.join(REPO, 'demand', 'plans', 'matsim')
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


def build_config(src_dir, run_dir, scenario, day, fraction, iterations, threads,
                 seed, overrides, cfg):
    """Write a run config with absolute paths, so the committed set is untouched."""
    base = os.path.join(SETS, scenario)
    text = open(os.path.join(src_dir, 'config.xml'), encoding='utf-8').read()

    plans_src = os.path.join(PLANS, 'population_%s.xml.gz' % day)
    plans_dst = os.path.join(run_dir, 'plans.xml.gz')
    veh_src = os.path.join(src_dir, 'transitVehicles.xml.gz')
    veh_dst = os.path.join(run_dir, 'transitVehicles.xml.gz')
    if fraction >= 1.0:
        n_in = n_out = None
        plans_dst, veh_dst = plans_src, veh_src
        scaled = []
    else:
        n_in, n_out = subsample_plans(plans_src, plans_dst, fraction, seed)
        scaled = scale_transit_capacity(veh_src, veh_dst, fraction,
                                        cfg.get('RUN.sample.transit_capacity_floor'))

    text = setp(text, 'inputNetworkFile', fwd(os.path.join(base, 'network.xml.gz')))
    text = setp(text, 'transitScheduleFile',
                fwd(os.path.join(src_dir, 'transitSchedule.xml.gz')))
    text = setp(text, 'vehiclesFile', fwd(veh_dst))
    text = setp(text, 'inputPlansFile', fwd(plans_dst))
    # The parking price table sits beside the scenario network, one per
    # scenario, and the committed config names it relatively. A run directory is
    # not beside the scenario, so absolutise it like every other input. Checked
    # rather than assumed: `setp` is a silent no-op on a param it cannot find,
    # and a config that lost its price file would run with free parking and look
    # exactly like a correct run (issue #33).
    if 'name="priceFile"' in text:
        price_src = os.path.join(base, 'parking_prices.tsv')
        if not os.path.exists(price_src):
            raise SystemExit(
                'the config declares a parking price file but %s does not exist. '
                'Regenerate the run inputs with build_matsim_run_inputs.py.'
                % price_src)
        text = setp(text, 'priceFile', fwd(price_src))
    # Both factors are registry fields, and NEITHER is a choice. flowCapacityFactor
    # equals the sample fraction, the standard MATSim scaling rule; storage equals
    # flow, which MATSim enforces - it throws when the two differ by more than
    # global.relativeTolerance (default 0.0), and states that raising storage above
    # flow "is no longer needed since the qsim became a lot more deterministic".
    # See DECISIONS.md 15.
    storage_exponent = cfg.get('RUN.sample.storage_capacity_exponent')
    storage = fraction ** storage_exponent
    if abs(storage - fraction) > 1e-12:
        # Fail here, in 0.1 s, rather than in the JVM a second later: MATSim's
        # GlobalConfigGroup.checkConsistency throws when the two factors differ
        # by more than global.relativeTolerance, which defaults to 0.0.
        raise SystemExit(
            'storageCapacityFactor (%g) must equal flowCapacityFactor (%g). MATSim '
            'enforces this and states that raising storage above flow "is no longer '
            'needed since the qsim became a lot more deterministic". '
            'RUN.sample.storage_capacity_exponent is 1.0 by derivation, not by '
            'assumption - see DECISIONS.md 15.' % (storage, fraction))
    text = setp(text, 'flowCapacityFactor', '%.6g' % fraction)
    text = setp(text, 'storageCapacityFactor', '%.6g' % storage)
    text = setp(text, 'lastIteration', iterations)
    text = setp(text, 'outputDirectory', fwd(os.path.join(run_dir, 'output')))
    text = setp(text, 'randomSeed', seed)
    text = re.sub(r'(<param name="numberOfThreads" value=")[^"]*(")',
                  lambda m: m.group(1) + str(threads) + m.group(2), text)
    for key, value in sorted(overrides.items()):
        if '.' in key:
            mode, name = key.split('.', 1)
            text = set_mode_param(text, mode, name, value)
        else:
            text = setp(text, key, value)
    cfg = os.path.join(run_dir, 'config.xml')
    open(cfg, 'w', encoding='utf-8', newline='\n').write(text)
    return cfg, dict(persons_in=n_in, persons_kept=n_out,
                     transit_capacity_scaled=sorted(set(scaled)))


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

    config_path, sample = build_config(src_dir, run_dir, scenario, day, fraction,
                                       iterations, threads, seed, overrides, cfg)
    snapshot = cfg.write_snapshot(os.path.join(run_dir, '_config.json'))
    log = os.path.join(run_dir, 'matsim.log')
    classpath = os.pathsep.join([JAR, CLASSES])
    cmd = [JAVA, '-Xmx%s' % xmx, '-XX:+UseParallelGC', '-cp', classpath, MAIN, config_path]
    # The live view was removed and is being rebuilt. Its four RUN.monitor.*
    # registry fields are deliberately retained for the replacement and
    # currently REACH NOTHING - re-wire them when it lands.
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
