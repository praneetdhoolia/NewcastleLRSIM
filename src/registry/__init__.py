#!/usr/bin/env python
"""The Wickham input registry: one resolved surface for every controllable value.

Every value the model consumes that is not read from an immutable raw download
is declared in `config/registry/*.json` with its units, its provenance and
either a sweep range or an explicit rule holding it fixed. This module resolves
those declarations into the values a script actually runs with, and refuses the
three things that would let the package drift:

**An unobtained input cannot acquire a point value by being read.** Fields with
`status: unobtained` carry `value: null` - SCATS phasing, charging dwell,
journey-linked Opal, the outer-loop tolerance and the iteration count. `get()`
raises on them. The caller must select a sweep member explicitly, which is
DECISIONS.md 0 and 13 enforced structurally rather than by discipline.

**An overlay cannot invent a field.** Overlays carry values only. A key that is
not already a registry field is rejected, so a run cannot introduce an input
outside the registry's provenance rules.

**A value cannot silently leave its sweep.** An overlay setting a field outside
its declared range is rejected unless that key is listed in the overlay's
`allow_outside_sweep` with a written justification - for deliberate stress
tests, never for routine runs.

Resolution order, lowest precedence first:

    config/registry/*.json      the declared values
    config/scenarios/<S>.json   per-scenario overlay
    config/day/<DAY>.json       per-day-type overlay
    config/runs/<tag>.json      per-run overlay
    WICKHAM_<DOTTED_KEY> env    environment override
    set= argument               programmatic / CLI override

Every resolution can be snapshotted with `snapshot()`, which records the value,
where it came from and which layer last touched it. `run_matsim.py` writes that
snapshot into the run directory, so a result always carries the exact inputs
that produced it.

Reads are logged. `consumers()` reports which script read which field, which is
how the `consumers` key in the registry is generated rather than hand-maintained.
"""
import copy
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
REGISTRY_DIR = os.path.join(REPO, 'config', 'registry')
SCHEMA_DIR = os.path.join(REPO, 'config', 'schema')
OVERLAY_DIRS = {'scenario': os.path.join(REPO, 'config', 'scenarios'),
                'day': os.path.join(REPO, 'config', 'day'),
                'run': os.path.join(REPO, 'config', 'runs')}
ENV_PREFIX = 'WICKHAM_'
SWEPT_SOURCES = ('measured', 'derived', 'literature', 'assumed')


class RegistryError(Exception):
    """A configuration fault. Always fatal - never fall back to a default."""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def _read_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def load_registry(registry_dir=None):
    """Merge every layer file into one {key: field} map, in sorted file order."""
    registry_dir = registry_dir or REGISTRY_DIR
    fields, origin = {}, {}
    for path in sorted(glob.glob(os.path.join(registry_dir, '*.json'))):
        doc = _read_json(path)
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        for key, field in doc.get('fields', {}).items():
            if key in fields:
                raise RegistryError('field %s declared twice: %s and %s'
                                    % (key, origin[key], rel))
            fields[key] = field
            origin[key] = rel
    if not fields:
        raise RegistryError('no registry fields found under %s' % registry_dir)
    return fields, origin


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def _sweep_interval(sweep):
    """The numeric [lo, hi] a sweep implies, or None if it is not an interval."""
    if isinstance(sweep, list) and len(sweep) == 2:
        return float(sweep[0]), float(sweep[1])
    if isinstance(sweep, dict) and 'interval' in sweep:
        return float(sweep['interval'][0]), float(sweep['interval'][1])
    return None


def _intrinsic_errors(fields):
    """The rules that matter, checked without a jsonschema dependency.

    CI installs nothing, so these run everywhere. `validate()` additionally
    runs the full JSON Schema when jsonschema happens to be importable.
    """
    errors = []
    for key, f in sorted(fields.items()):
        for req in ('value', 'units', 'source', 'status', 'description'):
            if req not in f:
                errors.append('%s: missing required key %r' % (key, req))
        if 'source' not in f or 'status' not in f:
            continue
        swept = f.get('sweep') is not None
        held = 'held_fixed' in f
        implied = 'derived_from' in f
        if f['source'] in SWEPT_SOURCES:
            if not swept and not held and not implied:
                errors.append('%s: source %r requires a sweep, a held_fixed rule or a '
                              'derived_from identity (proposal 8.1)' % (key, f['source']))
            if implied and f['source'] != 'derived':
                errors.append('%s: derived_from is only for source "derived", not %r'
                              % (key, f['source']))
            if 'decisions_ref' not in f:
                errors.append('%s: source %r requires a decisions_ref' % (key, f['source']))
        if f['status'] == 'unobtained':
            if f.get('value') is not None:
                errors.append('%s: status unobtained must carry value null - an unobtained '
                              'input may not be pinned (DECISIONS.md 0, 13)' % key)
            if not swept:
                errors.append('%s: status unobtained requires a sweep' % key)
    return errors


def validate(fields=None, strict_schema=True):
    """Return a list of problems. Empty means the registry is well formed."""
    if fields is None:
        fields, _ = load_registry()
    errors = _intrinsic_errors(fields)
    if not strict_schema:
        return errors
    try:
        import jsonschema
    except ImportError:
        return errors
    schema = _read_json(os.path.join(SCHEMA_DIR, 'field.schema.json'))
    schema.pop('$id', None)
    validator = jsonschema.Draft202012Validator(schema)
    for key, f in sorted(fields.items()):
        for e in sorted(validator.iter_errors(f), key=lambda x: list(x.path)):
            errors.append('%s: %s' % (key, e.message))
    return errors


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------
def _env_overrides():
    """WICKHAM_A_LIGHTRAIL_DWELL_FIXED_S -> A.lightrail.dwell_fixed_s, by matching."""
    out = {}
    for name, raw in os.environ.items():
        if not name.startswith(ENV_PREFIX) or name == ENV_PREFIX + 'REPO':
            continue
        out[name[len(ENV_PREFIX):]] = raw
    return out


def _match_env_key(env_name, keys):
    """An env name matches the field whose dotted key upper-cases to it."""
    for k in keys:
        if k.replace('.', '_').upper() == env_name.upper():
            return k
    return None


def _coerce(raw, current):
    """Parse an env/CLI string against the type the registry declares."""
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    if isinstance(current, bool):
        if text.lower() in ('true', '1', 'yes'):
            return True
        if text.lower() in ('false', '0', 'no'):
            return False
        raise RegistryError('cannot read %r as a boolean' % raw)
    if isinstance(current, int) and not isinstance(current, bool):
        return int(text)
    if isinstance(current, float):
        return float(text)
    if isinstance(current, (list, dict)) or current is None:
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text


class Config(object):
    """A resolved configuration. Immutable once built; every read is logged."""

    def __init__(self, fields, origin, layers):
        self._fields = fields
        self._origin = origin
        self._layers = layers          # ordered [(layer_name, {key: value})]
        self._resolved = {}
        self._from = {}
        for key, field in fields.items():
            self._resolved[key] = copy.deepcopy(field.get('value'))
            self._from[key] = origin[key]
        for name, values in layers:
            for key, value in values.items():
                self._resolved[key] = value
                self._from[key] = name
        self._reads = {}

    # -- access ------------------------------------------------------------
    def __contains__(self, key):
        return key in self._fields

    def field(self, key):
        try:
            return self._fields[key]
        except KeyError:
            raise RegistryError('no registry field %r' % key)

    def get(self, key, caller=None):
        """The resolved value. Raises for an unobtained field with no override."""
        field = self.field(key)
        value = self._resolved[key]
        if value is None and field['status'] == 'unobtained':
            raise RegistryError(
                '%s is UNOBTAINED and has no point value. %s Select a sweep member '
                'explicitly - e.g. cfg.sweep(%r) - or set it in an overlay with a '
                'justification. (DECISIONS.md %s)'
                % (key, field['description'].split('.')[0].strip() + '.',
                   key, field.get('decisions_ref', '0, 13')))
        self._reads.setdefault(key, set()).add(caller or _calling_script())
        return copy.deepcopy(value)

    def sweep(self, key):
        """The declared sweep, as an interval, a categorical list or a proportion."""
        field = self.field(key)
        sweep = field.get('sweep')
        if sweep is None:
            raise RegistryError('%s carries no sweep%s' % (
                key, ' - it is held fixed: ' + field['held_fixed']['rule']
                if 'held_fixed' in field else ''))
        self._reads.setdefault(key, set()).add(_calling_script())
        return copy.deepcopy(sweep)

    def source(self, key):
        return self.field(key)['source']

    def provenance(self, key):
        f = self.field(key)
        return dict(key=key, source=f['source'], status=f['status'], units=f['units'],
                    sweep=f.get('sweep'), held_fixed=f.get('held_fixed'),
                    decisions_ref=f.get('decisions_ref'), resolved_from=self._from[key],
                    declared_in=self._origin[key])

    # -- reporting ---------------------------------------------------------
    def keys(self):
        return sorted(self._fields)

    def unobtained(self):
        return sorted(k for k, f in self._fields.items() if f['status'] == 'unobtained')

    def consumers(self):
        return {k: sorted(v) for k, v in sorted(self._reads.items())}

    def snapshot(self):
        """Everything needed to reproduce this resolution, and nothing else."""
        return {
            'registry_fields': len(self._fields),
            'layers': [name for name, _ in self._layers],
            'values': {k: self._resolved[k] for k in sorted(self._fields)},
            'resolved_from': {k: self._from[k] for k in sorted(self._fields)},
            'provenance': {k: self.provenance(k) for k in sorted(self._fields)},
        }

    def write_snapshot(self, path):
        with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(self.snapshot(), f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write('\n')
        return path


def _calling_script():
    """Best-effort name of the script doing the read, for the consumers map."""
    try:
        return os.path.relpath(sys.argv[0], REPO).replace(os.sep, '/')
    except (ValueError, TypeError):
        return os.path.basename(sys.argv[0] or 'python')


def _check_values(items, fields, layer_name, allow=(), justification=None):
    """Any layer may set existing fields only, inside their sweep, not held fixed.

    This governs overlays, environment variables and programmatic/CLI overrides
    alike. Only a committed overlay can carry `allow_outside_sweep`, so escaping
    a declared range requires a written justification in a file under version
    control - never a flag typed at a shell.
    """
    allow = set(allow)
    justification = justification or {}
    values, errors = {}, []
    for key, value in sorted(items.items()):
        if key not in fields:
            errors.append('%s: sets %s, which is not a registry field. An overlay may not '
                          'introduce an input.' % (layer_name, key))
            continue
        field = fields[key]
        interval = _sweep_interval(field.get('sweep'))
        if interval and isinstance(value, (int, float)) and not isinstance(value, bool):
            lo, hi = interval
            if not (lo <= float(value) <= hi):
                if key not in allow:
                    errors.append('%s: sets %s to %r, outside its declared sweep [%g, %g]. '
                                  'List it in allow_outside_sweep with a justification if '
                                  'that is deliberate.' % (layer_name, key, value, lo, hi))
                elif key not in justification:
                    errors.append('%s: %s is in allow_outside_sweep with no justification.'
                                  % (layer_name, key))
        if 'held_fixed' in field and key not in allow:
            errors.append('%s: sets %s, which is HELD FIXED. %s Departure requires: %s'
                          % (layer_name, key, field['held_fixed']['rule'],
                             field['held_fixed'].get('departure_requires', 'a logged decision')))
            continue
        values[key] = value
    return values, errors


def _check_overlay(doc, fields, layer_name):
    """An overlay document, which may carry an allow_outside_sweep escape."""
    return _check_values(doc.get('set', {}), fields, layer_name,
                         doc.get('allow_outside_sweep', []),
                         doc.get('justification', {}))


def load(scenario=None, day=None, run=None, set=None, use_env=True,
         registry_dir=None, strict=True):
    """Resolve the registry through the overlay chain. Fatal on any fault."""
    fields, origin = load_registry(registry_dir)
    if strict:
        errors = validate(fields)
        if errors:
            raise RegistryError('registry is not well formed:\n  ' + '\n  '.join(errors))

    layers, problems = [], []
    for kind, name in (('scenario', scenario), ('day', day), ('run', run)):
        if not name:
            continue
        path = os.path.join(OVERLAY_DIRS[kind], '%s.json' % name)
        if not os.path.exists(path):
            if kind == 'run':
                continue                      # a run overlay is optional
            raise RegistryError('no %s overlay at %s' % (kind, path))
        doc = _read_json(path)
        values, errs = _check_overlay(doc, fields, '%s overlay %s' % (kind, name))
        problems.extend(errs)
        layers.append(('%s:%s' % (kind, name), values))

    if use_env:
        env_values = {}
        for env_name, raw in sorted(_env_overrides().items()):
            key = _match_env_key(env_name, fields)
            if key is None:
                problems.append('env %s%s matches no registry field'
                                % (ENV_PREFIX, env_name))
                continue
            env_values[key] = _coerce(raw, fields[key].get('value'))
        if env_values:
            checked, errs = _check_values(env_values, fields, 'env')
            problems.extend(errs)
            layers.append(('env', checked))

    if set:
        explicit = {}
        for key, value in sorted(set.items()):
            if key not in fields:
                problems.append('--set %s matches no registry field' % key)
                continue
            explicit[key] = _coerce(value, fields[key].get('value'))
        if explicit:
            checked, errs = _check_values(explicit, fields, 'set')
            problems.extend(errs)
            layers.append(('set', checked))

    if problems:
        raise RegistryError('configuration rejected:\n  ' + '\n  '.join(problems))
    return Config(fields, origin, layers)


def parse_set(pairs):
    """['A.b.c=1', ...] -> {'A.b.c': '1'}, for CLI wiring."""
    out = {}
    for item in pairs or []:
        key, sep, value = item.partition('=')
        if not sep:
            raise RegistryError('--set expects KEY=VALUE, got %r' % item)
        out[key.strip()] = value
    return out
