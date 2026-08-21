#!/usr/bin/env python
"""Prove the framework runs for a city it has never seen. NO FRAMEWORK EDIT.

    python tests/check_city_agnostic.py
    python tests/check_city_agnostic.py --keep    leave the fixture for inspection

Goal G2 says "a second city built from `config/schema/` alone, no framework
edit", and its state has been *"structurally in place, never exercised"* for the
whole life of the restructure. Structurally in place is a claim. This exercises
it, which is the same standard the rest of this repository is held to: establish
reach by CHANGING A VALUE AND WATCHING THE OUTPUT CHANGE, never by reading code.

**It invents no observation.** Fabricating a city's census, counts or patronage
would breach the hard constraint that no unsupported number may be presented as
observed. So the fixture is not a study and does not pretend to be one: it is
the reference city's OWN DECLARATIONS with a different IDENTITY stamped on them
- a different projection, base year, seed, day-type vocabulary, mode vocabulary
and scenario set - plus a deliberate perturbation of a few declared values. It
is built in a temporary directory at test time and deleted afterwards.

What that proves, and what it does not:

  PROVES  the input contract admits a second city; the resolver resolves it; the
          config emitter writes THAT CITY's values; and the framework carries no
          value belonging to the reference city, because if it did the emitted
          config would still show it.
  DOES NOT prove a scenario runs end to end. That needs a real network, plans
          and schedule for the second city, which is data acquisition rather
          than a property of the framework.

The assertions are DIFFERENCES, not equalities: a check that the second city's
config merely parses would pass even if every value were the first city's.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CITIES = os.path.join(REPO, 'cities')
FIXTURE = 'contractfixture'
FIXTURE_DIR = os.path.join(CITIES, FIXTURE)

# Every mode name any city in this repository uses, so a `[selector]` can be
# recognised as a mode rather than as some other parameterset key.
ALL_MODE_NAMES = {'car', 'ride', 'pt', 'bike', 'walk', 'bus', 'rail',
                  'light_rail', 'tram', 'ferry', 'car_passenger'}

_state = {'pass': 0, 'fail': 0}


def check(ok, label):
    _state['pass' if ok else 'fail'] += 1
    print(('PASS  ' if ok else 'FAIL  ') + label)
    return ok


def _read(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write('\n')


# --------------------------------------------------------------------------
# the fixture: the reference city's declarations, a different identity
# --------------------------------------------------------------------------
# Every value here is a TRANSFORMATION of the reference city's own declaration,
# never an invented observation. The identity values are deliberately unlike the
# reference city's so that a framework constant that had leaked would show up as
# the reference city's value surviving into the fixture's config.
IDENTITY = {
    'crs_epsg': 32633,                 # a different projected CRS entirely
    'crs_datum': 'WGS 84',
    'crs_zone': 'UTM Zone 33N',
    'base_year': 2031,
    'seed': 19990101,
    'day_types': ['MON', 'SUN'],       # two day types, differently named
    'modes': ['car', 'pt', 'walk'],    # THREE modes, not five
    'scenarios': ['X0', 'X1'],
    'base_scenario': 'X0',
}

# Declared values perturbed so the emitted config must differ numerically. Each
# stays inside the field's declared sweep, so the fixture is a legal city rather
# than a stress test.
PERTURB = {
    'RUN.machine.threads': 3,
    'RUN.machine.event_handler_threads': 2,
    'RUN.qsim.end_time_h': 28,
    'RUN.replanning.fraction_to_disable_innovation': 0.7,
    'RUN.scoring.brain_exp_beta': 1.5,
    'A.network.max_link_length_m': 250.0,
    'A.parking.max_stay_min': 90.0,
}


MODE_SELECTOR = re.compile(r'\[([a-z_]+)\]')


def _foreign_mode(field, modes):
    """Does this field's binding name a mode this city does not run?"""
    for bind in ('matsim_param', 'sumo_param', 'pt2matsim_osm_param',
                 'pt2matsim_mapper_param'):
        for sel in MODE_SELECTOR.findall(str(field.get(bind) or '')):
            if sel != '*' and sel in ALL_MODE_NAMES and sel not in modes:
                return True
    return False


def build_fixture(reference):
    """Write a complete second city from the reference city's declarations."""
    ref_dir = os.path.join(CITIES, reference)
    if os.path.isdir(FIXTURE_DIR):
        shutil.rmtree(FIXTURE_DIR)

    # 1. the descriptor: same SHAPE, different identity.
    doc = _read(os.path.join(ref_dir, 'city.json'))
    doc['id'] = FIXTURE
    doc['name'] = 'Contract fixture city'
    doc['description'] = ('NOT A STUDY AND NOT A PLACE. Built by '
                          'tests/check_city_agnostic.py to prove the framework '
                          'runs for a city it has never seen. It carries the '
                          'reference city2019s declarations under a different '
                          'identity and no observation of its own.')
    doc['crs'] = {'epsg': IDENTITY['crs_epsg'], 'datum': IDENTITY['crs_datum'],
                  'zone': IDENTITY['crs_zone'], 'units': 'm'}
    doc['base_year'] = IDENTITY['base_year']
    doc['seed'] = IDENTITY['seed']
    doc['day_types'] = list(IDENTITY['day_types'])
    doc['modes'] = list(IDENTITY['modes'])
    doc['boundary']['selector'] = ['Fixture Core']
    doc['boundary']['external_tier']['selector'] = ['Fixture Ring']
    doc['mode_share_target']['filter_value'] = 'Fixture Core'
    doc['mode_share_target']['geography'] = 'Fixture Core, both ends'
    doc['intervention'] = {'name': 'Fixture intervention',
                           'base_scenario': IDENTITY['base_scenario'],
                           'scenarios': list(IDENTITY['scenarios'])}
    _write(os.path.join(FIXTURE_DIR, 'city.json'), doc)

    # 2. the registry, with the identity-bearing fields moved onto the fixture.
    for name in sorted(os.listdir(os.path.join(ref_dir, 'registry'))):
        if not name.endswith('.json'):
            continue
        layer = _read(os.path.join(ref_dir, 'registry', name))
        # A field whose binding names a MODE in its selector belongs to that
        # mode, and a city that does not run the mode does not declare the
        # field - required_fields.json says so itself ("a city with no light
        # rail has no use for A.lightrail.dwell_fixed_s"). Dropping them is what
        # a real three-mode city would do, and it is what makes the emitted
        # config carry three modes rather than the reference city's five.
        layer['fields'] = {k: f for k, f in layer.get('fields', {}).items()
                           if not _foreign_mode(f, IDENTITY['modes'])}
        for key, field in layer['fields'].items():
            if key in PERTURB:
                field['value'] = PERTURB[key]
            if key == 'B.seed.master' or key.endswith('.seed'):
                field['value'] = IDENTITY['seed']
            if key == 'RUN.mode_choice.modes':
                field['value'] = list(IDENTITY['modes'])
            if key == 'RUN.mode_choice.chain_based_modes':
                field['value'] = ['car']
            if key == 'RUN.routing.network_modes':
                field['value'] = ['car']
            if key == 'RUN.travel_time.analysed_modes':
                field['value'] = ['car']
            if key == 'E.matrix.day_types':
                field['value'] = list(IDENTITY['day_types'])
            if key == 'E.matrix.scenario_ids':
                field['value'] = list(IDENTITY['scenarios'])
            if key == 'E.matrix.reference_scenario':
                field['value'] = IDENTITY['base_scenario']
            # Per-mode tables must span the fixture's OWN mode vocabulary, not
            # the reference city's: a five-mode table under a three-mode city is
            # exactly the mismatch a second city exposes.
            if isinstance(field.get('value'), dict) and field['value'] \
                    and set(field['value']) >= set(IDENTITY['modes']):
                field['value'] = {m: v for m, v in field['value'].items()
                                  if m in IDENTITY['modes']}
        _write(os.path.join(FIXTURE_DIR, 'registry', name), layer)

    # 3. overlays: one per declared day type and scenario, plus a run overlay.
    for day in IDENTITY['day_types']:
        _write(os.path.join(FIXTURE_DIR, 'overlays', 'day', '%s.json' % day),
               {'overlay': day, 'description': 'fixture day type', 'set': {}})
    for sid in IDENTITY['scenarios']:
        _write(os.path.join(FIXTURE_DIR, 'overlays', 'scenarios', '%s.json' % sid),
               {'overlay': sid, 'description': 'fixture scenario',
                'applies_to': {'scenario': [sid]}, 'set': {}})
    _write(os.path.join(FIXTURE_DIR, 'overlays', 'runs', 'smoke.json'),
           {'overlay': 'smoke', 'description': 'fixture smoke run',
            'set': {'RUN.controler.last_iteration': 250}})

    # 4. geometry, at the reference city's shape with the fixture's own numbers
    #    kept out of any plausible place - it is not a location on Earth.
    _write(os.path.join(FIXTURE_DIR, 'geometry', 'analysis_extents.json'),
           {'description': 'fixture extents', 'crs': 'EPSG:4326', 'extents': {}})
    _write(os.path.join(FIXTURE_DIR, 'geometry', 'scenario_alignments.json'),
           {'description': 'fixture alignments', 'crs': 'EPSG:4326',
            'alignments': {}, 'anchors': {}})

    # 5. the directories city.py requires a runnable city to have.
    for sub in ('extract', 'data', 'networks', 'schedules', 'demand',
                'scenarios', 'params'):
        os.makedirs(os.path.join(FIXTURE_DIR, sub), exist_ok=True)
    return FIXTURE_DIR


# --------------------------------------------------------------------------
def emit_for(city_id, scenario, day):
    """Emit a MATSim config for one city, in a SUBPROCESS.

    A subprocess because `city.py` and `registry` resolve the city at import and
    cache it; re-importing them in one process would test the cache rather than
    the framework.
    """
    script = (
        'import json, os, sys\n'
        'sys.path.insert(0, %r)\n'
        'sys.path.insert(0, %r)\n'
        'import registry\n'
        'from registry import param_config\n'
        'import city\n'
        'cfg = registry.load(scenario=%r, day=%r, run="smoke")\n'
        'runtime = {\n'
        '  "global.coordinateSystem": (city.crs(), "identity", "city.json"),\n'
        '  "network.inputNetworkFile": ("n", "path", ""),\n'
        '  "plans.inputPlansFile": ("p", "path", ""),\n'
        '  "transit.transitScheduleFile": ("s", "path", ""),\n'
        '  "transit.vehiclesFile": ("v", "path", ""),\n'
        '  "controler.outputDirectory": ("o", "path", ""),\n'
        '  "parking.priceFile": ("k", "path", ""),\n'
        '  "qsim.flowCapacityFactor": (cfg.get("RUN.sample.fraction"), "derived", "f"),\n'
        '  "qsim.storageCapacityFactor": (cfg.get("RUN.sample.fraction"), "derived", "f"),\n'
        '  "parking.chargedStartHour": (0.0, "derived", "fixture"),\n'
        '  "parking.chargedEndHour": (0.0, "derived", "fixture"),\n'
        '  "scoring.waitingPt": (-1.0, "derived", "fixture"),\n'
        '  "scoring.utilityOfLineSwitch": (-1.0, "derived", "fixture"),\n'
        '  "scoring.modeParams[*].constant": ({m: 0.0 for m in '
        'cfg.get("RUN.mode_choice.modes")}, "derived", "fixture"),\n'
        '  "scoring.modeParams[*].marginalUtilityOfTraveling_util_hr": '
        '({m: -1.0 for m in cfg.get("RUN.mode_choice.modes")}, "derived", "fixture"),\n'
        '  "scoring.activityParams[*].minimalDuration": '
        '({a: 60 for a in cfg.get("C.scoring.activity_typical_duration_s")}, '
        '"derived", "fixture", param_config.HHMMSS, "seconds"),\n'
        '}\n'
        'leaks = param_config.closure("matsim", cfg, runtime)\n'
        'assert not leaks, leaks\n'
        'sys.stdout.write(param_config.emit("matsim", cfg, runtime))\n'
        % (os.path.join(REPO, 'src'), os.path.join(REPO, 'src', 'registry'),
           scenario, day)
    )
    env = dict(os.environ, CITYSIM_CITY=city_id)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True,
                       text=True, env=env, cwd=REPO)
    if r.returncode != 0:
        raise SystemExit('emitting for %s failed:\n%s' % (city_id, r.stderr))
    return r.stdout


def params_of(xml):
    out = {}
    for line in xml.splitlines():
        if '<param name="' in line:
            name = line.split('<param name="', 1)[1].split('"', 1)[0]
            value = line.split('value="', 1)[1].split('"', 1)[0]
            out.setdefault(name, []).append(value)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--keep', action='store_true',
                    help='leave the fixture city on disk for inspection')
    ap.add_argument('--reference', default=os.environ.get('CITYSIM_CITY', 'newcastle'))
    a = ap.parse_args()

    framework_before = framework_digest()
    build_fixture(a.reference)
    try:
        run_checks(a.reference)
        check(framework_digest() == framework_before,
              'no framework file changed while a second city was built and run')
    finally:
        if not a.keep and os.path.isdir(FIXTURE_DIR):
            shutil.rmtree(FIXTURE_DIR, ignore_errors=True)

    print('\nPASS %d   FAIL %d' % (_state['pass'], _state['fail']))
    return 1 if _state['fail'] else 0


def framework_digest():
    """A hash of every framework source, so "no framework edit" is checked."""
    import hashlib
    h = hashlib.sha256()
    for root in ('src', 'config/schema', 'run.py'):
        full = os.path.join(REPO, root)
        paths = [full] if os.path.isfile(full) else []
        for base, dirs, names in os.walk(full):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            paths += [os.path.join(base, n) for n in sorted(names)]
        for p in sorted(paths):
            with open(p, 'rb') as f:
                h.update(f.read())
    return h.hexdigest()


def run_checks(reference):
    # 1. the portable contract admits the fixture, with no framework edit.
    r = subprocess.run([sys.executable, 'src/registry/check_city.py',
                        '--city', FIXTURE], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0 and 'FAIL 0' in r.stdout.replace('  ', ' '),
          'check_city accepts a city the framework has never seen')
    if r.returncode != 0:
        print(r.stdout[-1500:])

    # 2. it emits a config, and that config is THIS city's.
    ref_day = _read(os.path.join(CITIES, reference, 'city.json'))['day_types'][0]
    ref_scn = _read(os.path.join(CITIES, reference,
                                 'city.json'))['intervention']['base_scenario']
    fixture_xml = emit_for(FIXTURE, IDENTITY['base_scenario'], IDENTITY['day_types'][0])
    reference_xml = emit_for(reference, ref_scn, ref_day)
    check(bool(fixture_xml.strip()), 'the second city emits a MATSim config')

    fx, rf = params_of(fixture_xml), params_of(reference_xml)

    # 3. THE ASSERTIONS ARE DIFFERENCES. A config that merely parses would pass
    #    even if every value in it belonged to the reference city.
    check(fx['coordinateSystem'] == ['EPSG:%d' % IDENTITY['crs_epsg']]
          and fx['coordinateSystem'] != rf['coordinateSystem'],
          'the projection is the fixture city\'s, not the reference city\'s')
    check(fx['randomSeed'] == [str(IDENTITY['seed'])]
          and fx['randomSeed'] != rf['randomSeed'],
          'the seed is the fixture city\'s')
    # Three numberOfThreads params, two owners: RUN.machine.threads writes the
    # global and qsim pair (one field, deliberately - 9.5) and
    # RUN.machine.event_handler_threads writes eventsManager's (9.56). Compared
    # as a multiset so the assertion does not depend on module order.
    check(sorted(fx['numberOfThreads'])
          == sorted([str(PERTURB['RUN.machine.threads'])] * 2
                    + [str(PERTURB['RUN.machine.event_handler_threads'])])
          and fx['numberOfThreads'] != rf['numberOfThreads'],
          'a perturbed declared value reaches the config')
    check(fx['endTime'] == ['28:00:00'] and fx['endTime'] != rf['endTime'],
          'the day window is the fixture city\'s, converted to hh:mm:ss')
    check(fx['fractionOfIterationsToDisableInnovation'] == ['0.7'],
          'the innovation cutoff is the fixture city\'s')
    check(fx['BrainExpBeta'] == ['1.5'] and fx['BrainExpBeta'] != rf['BrainExpBeta'],
          'the logit scale is the fixture city\'s')
    check(fx['maxStayMinutes'] != rf['maxStayMinutes'],
          'the parking max stay is the fixture city\'s')

    # 4. the MODE VOCABULARY follows the city. Three modes, not five.
    # `mode` keys both the SCORED modeParams sets and the teleported
    # routing-helper sets; the vocabulary assertion is about the former, so
    # helper modes (non_network_walk, the access stub - DECISIONS.md 9.54)
    # are excluded rather than counted as a fourth scored mode.
    helper_modes = {'non_network_walk'}
    modes = sorted(set(fx['mode']) - helper_modes)
    check(modes == sorted(IDENTITY['modes']),
          'the scored modes are the fixture city\'s %s, not the reference '
          'city\'s %s' % (sorted(IDENTITY['modes']),
                          sorted(set(rf['mode']) - helper_modes)))
    check(fx['modes'] == [','.join(IDENTITY['modes'])],
          'the mode-choice mode list is the fixture city\'s')

    # 5. nothing of the reference city survives into the fixture's config.
    ref_doc = _read(os.path.join(CITIES, reference, 'city.json'))
    leaked = sorted({t for t in ({ref_doc['name'].split()[0]}
                                 | set(ref_doc['boundary']['selector']))
                     if t.lower() in fixture_xml.lower()})
    check(not leaked,
          'no reference-city name appears anywhere in the second city\'s config'
          + ('' if not leaked else ': %s' % leaked))


if __name__ == '__main__':
    sys.exit(main())
