#!/usr/bin/env python
"""Write a tool's config FROM the registry, so a literal has nowhere to live.

    import param_config
    xml = param_config.emit('matsim', cfg, runtime)

The repository's signature defect - a declared value that reaches nothing, or a
default that is right by accident - had one structural cause in the run inputs:
the MATSim config was a hand-written template with `{substitution}` holes, so
every parameter nobody had cut a hole for stayed a literal. Forty-seven of them
did. Six had registry fields carrying a `matsim_param` binding that the template
ignored, which is the worst case of all - right by accident, and silently wrong
the moment anyone swept the field.

Patching those literals one at a time leaves the template, and the template is
the defect: it is a place where typing a number is possible. This module removes
the place. The config is BUILT from the fields that declare a binding, so:

  * a parameter exists in the output only if a field claims it, or if the caller
    supplies it under a declared runtime role (a path, the city's own identity,
    or a value derived from declared fields);
  * `closure()` returns anything that came from neither, and `check_hardcoding`
    fails on a non-empty answer. There is no third source;
  * sweeping a field changes the config, because the config has no other
    opinion about the value. `reach()` proves that by nudging each field and
    watching the bytes move - the discipline the handover brief states as a
    rule ("change the value and watch the output change"), asserted rather than
    remembered.

**City-agnostic.** Nothing here names a place, a value or a unit. The structure
comes from `config/schema/param_config.json` (MATSim's own vocabulary, portable)
and the values come from `cities/<city>/registry/` through the resolver. A second
city supplies different values against the same bindings and the same emitter.

**Deterministic.** Modules in the declared order, parameters sorted within a
module, parameter sets sorted by key. Two resolutions of the same inputs give
byte-identical output, which is what lets `reach()` diff them at all.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, HERE)

import registry as _registry  # noqa: E402

SCHEMA = os.path.join(REPO, 'config', 'schema', 'param_config.json')
XML_DECL = '<?xml version="1.0" encoding="utf-8"?>'
TAB = '\t'

_SCHEMA_CACHE = {}


class ConfigError(Exception):
    """A binding that cannot be honoured. Always fatal - never emit a guess."""


def schema():
    if not _SCHEMA_CACHE:
        with io.open(SCHEMA, encoding='utf-8') as f:
            _SCHEMA_CACHE.update(json.load(f))
    return _SCHEMA_CACHE


def tool(name):
    spec = schema()['tools'].get(name)
    if spec is None:
        raise ConfigError('no tool %r in %s (have: %s)'
                          % (name, SCHEMA, ', '.join(sorted(schema()['tools']))))
    return spec


# --------------------------------------------------------------------------
# the binding grammar
# --------------------------------------------------------------------------
def parse_target(target):
    """'scoring.modeParams[bike].constant' -> ('scoring', 'modeParams', 'bike', 'constant').

    A plain 'qsim.endTime' gives (module, None, None, param). Anything else is a
    fault rather than a best guess: a binding the emitter cannot read is a value
    that would silently not be written, which is the failure this module exists
    to end.
    """
    text = target.strip()
    if '.' not in text:
        raise ConfigError('binding %r is not module.param' % target)
    module, _, rest = text.partition('.')
    if '[' not in rest:
        if '.' in rest:
            raise ConfigError('binding %r has a nested path but no [selector]' % target)
        return module, None, None, rest
    set_type, _, tail = rest.partition('[')
    selector, _, param = tail.partition(']')
    param = param.lstrip('.')
    if not selector or not param:
        raise ConfigError('binding %r is not module.setType[selector].param' % target)
    return module, set_type, selector, param


def targets_of(field, binding):
    """Every parameter one field writes to. A field may name more than one."""
    raw = field.get(binding)
    if not raw:
        return []
    return [parse_target(t) for t in str(raw).split(',') if t.strip()]


# --------------------------------------------------------------------------
# rendering a value
# --------------------------------------------------------------------------
HHMMSS = 'hh:mm:ss'

# How many seconds one unit of a declared field is worth, for the fields whose
# MATSim parameter is a clock string. Read from the field's own `units` rather
# than re-declared beside the format, so a field cannot say `hours` in one place
# and be treated as seconds in another.
SECONDS_PER_UNIT = {'hours': 3600, 'hour': 3600, 'h': 3600,
                    'minutes': 60, 'minute': 60, 'min': 60,
                    'seconds': 1, 'second': 1, 's': 1}


def render(value, fmt=None, units=None):
    """A registry value as MATSim reads it back.

    A list becomes a comma-separated string because that is how MATSim's config
    reader parses a multi-valued parameter; a bool becomes lower case for the
    same reason. Formatting is fixed here rather than at each call site so two
    builders cannot render the same field differently - which is how a value
    ends up right in one config and wrong in another.

    `fmt` carries the one case where a field's declared units and MATSim's
    parameter format genuinely differ: a clock time or a duration is declared in
    hours or seconds, because that is what it IS, and MATSim reads hh:mm:ss.
    The old template hid this by writing the string `30:00:00` as a literal
    beside a field declaring the number 30 - two representations of one value,
    which is the drift this registry exists to stop.
    """
    if fmt == HHMMSS:
        if units not in SECONDS_PER_UNIT:
            raise ConfigError('a %s parameter needs the field to declare time '
                              'units so the conversion is not guessed; got units '
                              '%r' % (HHMMSS, units))
        return hhmmss(float(value) * SECONDS_PER_UNIT[units])
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple)):
        return ','.join(render(v) for v in value)
    if isinstance(value, float):
        # %r would give 1e-05 for a small rate; MATSim wants a plain decimal.
        text = ('%.10f' % value).rstrip('0')
        return text + '0' if text.endswith('.') else text
    if value is None:
        raise ConfigError('a null value cannot be written to a config - an '
                          'unobtained field must be given a value by an overlay '
                          'or a run before its config is emitted')
    return str(value)


def hhmmss(seconds):
    """Seconds (or hours, if the caller has already converted) as hh:mm:ss.

    Hours beyond 24 are kept rather than wrapped: the day window here is 30 h so
    a 23:30 departure can arrive, and wrapping it to 06:00:00 would silently
    halve the simulated day.
    """
    total = int(round(float(seconds)))
    return '%02d:%02d:%02d' % (total // 3600, (total % 3600) // 60, total % 60)


# --------------------------------------------------------------------------
# collecting parameters
# --------------------------------------------------------------------------
def _resolve(cfg, key):
    """The resolved value, with the resolver's own refusal preserved."""
    return cfg.get(key, caller='src/registry/param_config.py')


def collect(name, cfg, runtime=None, fields=None):
    """{module: {param: (value, origin)}} and the parameter sets, from the registry.

    `runtime` supplies what a registry cannot: paths on this machine, the city's
    own identity, and values derived at build time from declared fields. Each
    entry is `param_path -> (value, role, note)` and every role must be one the
    schema declares, so "I needed somewhere to put it" is not a role.
    """
    spec = tool(name)
    binding = spec['binding']
    fields = fields if fields is not None else {k: cfg.field(k) for k in cfg.keys()}
    sets_spec = spec.get('parameter_sets', {})

    plain = {}          # module -> {param: (rendered, origin)}
    sets = {}           # module -> set_type -> key -> {param: (rendered, origin)}
    broadcast = []      # one value applied to every set of a type, applied last

    def put(module, param, value, origin):
        prior = plain.setdefault(module, {}).get(param)
        if prior is not None and prior[0] != value:
            raise ConfigError('%s.%s is written twice, as %r by %s and %r by %s'
                              % (module, param, prior[0], prior[1], value, origin))
        plain[module][param] = (value, origin)

    def put_set(module, set_type, key, param, value, origin):
        sets.setdefault(module, {}).setdefault(set_type, {}) \
            .setdefault(str(key), {})[param] = (value, origin)

    def place(module, set_type, selector, param, value, origin, fmt, units):
        """Write one binding's value, expanding a `[*]` selector.

        One path for a registry field and for a runtime value, because two
        paths is how the star expansion ends up implemented in one of them and
        not the other - and a `[*]` that silently emits a parameterset literally
        keyed `*` is a config MATSim accepts and nothing in it applies.
        """
        if set_type is None:
            put(module, param, render(value, fmt, units), origin)
            return
        if selector != '*':
            put_set(module, set_type, selector, param,
                    render(value, fmt, units), origin)
            return
        if not isinstance(value, (dict, list, tuple)):
            # A SCALAR against `[*]` is not membership - it is one value that
            # applies to EVERY set of this type, e.g. the same freespeedFactor
            # on all eighteen way defaults. Deferred, because the membership is
            # decided by the other bindings and may not be known yet.
            broadcast.append((module, set_type, param, value, origin, fmt, units))
            return
        # The value IS the membership: a dict gives one set per entry carrying
        # that entry's value, a list gives one set per member carrying only its
        # key - which is how a vocabulary declares its members.
        members = value.items() if isinstance(value, dict) \
            else [(v, None) for v in value]
        for member_key, member_value in members:
            if member_value is None:
                sets.setdefault(module, {}).setdefault(set_type, {}) \
                    .setdefault(str(member_key), {})
            else:
                put_set(module, set_type, member_key, param,
                        render(member_value, fmt, units), origin)

    for key in sorted(fields):
        field = fields[key]
        if not isinstance(field, dict):
            continue
        if not targets_of(field, binding):
            continue
        # A `computed` field has no value of its own - it is an identity the
        # harness evaluates at run time (flowCapacityFactor IS the sample
        # fraction). Its binding still records WHERE the result goes, so the
        # closure test can see the parameter is accounted for, but the value
        # must arrive under the `derived` runtime role. Emitting its declared
        # null would write the word "None" into a config.
        if field.get('status') == 'computed':
            for module, set_type, selector, param in targets_of(field, binding):
                target = ('%s.%s' % (module, param) if set_type is None
                          else '%s.%s[%s].%s' % (module, set_type, selector, param))
                if target not in (runtime or {}):
                    raise ConfigError(
                        '%s is declared `computed` and binds to %s, so the caller '
                        'must supply it under the `derived` runtime role with the '
                        'identity that produced it (%s)'
                        % (key, target,
                           (field.get('derived_from') or {}).get('identity', 'see the field')))
            continue
        fmt, units = field.get('%s_format' % binding.split('_')[0]), field.get('units')
        for module, set_type, selector, param in targets_of(field, binding):
            place(module, set_type, selector, param, _resolve(cfg, key), key,
                  fmt, units)

    for target, supplied in sorted((runtime or {}).items()):
        value, role, note, fmt, units = _unpack_runtime(target, supplied)
        if role not in schema()['runtime_roles']:
            raise ConfigError('%s is supplied with role %r, which %s does not '
                              'declare' % (target, role, SCHEMA))
        module, set_type, selector, param = parse_target(target)
        place(module, set_type, selector, param, value,
              '%s:%s' % (role, note or ''), fmt, units)

    # Broadcasts last, so they land on every set the other bindings created. A
    # broadcast that finds no set is a binding to a parameterset nothing else
    # populates, which is a fault rather than a silent no-op.
    for module, set_type, param, value, origin, fmt, units in broadcast:
        keys = sets.get(module, {}).get(set_type)
        if not keys:
            raise ConfigError('%s.%s[*].%s applies to every set of that type, but '
                              'no field creates one' % (module, set_type, param))
        for key in sorted(keys):
            put_set(module, set_type, key, param, render(value, fmt, units), origin)

    return spec, plain, sets, sets_spec


def _unpack_runtime(target, supplied):
    """(value, role, note[, format, units]) - the note is not optional in spirit.

    A runtime value is one the registry cannot hold: a path, the city's own
    identity, or something derived from declared fields. The note records WHICH,
    and it ends up in the closure report, so `derived` cannot become a place to
    put a number whose origin nobody wrote down.
    """
    if not isinstance(supplied, (tuple, list)) or not 2 <= len(supplied) <= 5:
        raise ConfigError('runtime entry %s must be (value, role[, note[, format'
                          '[, units]]]); got %r' % (target, supplied))
    padded = list(supplied) + [None] * (5 - len(supplied))
    return tuple(padded[:5])


# --------------------------------------------------------------------------
# emitting
# --------------------------------------------------------------------------
def emit(name, cfg, runtime=None, fields=None):
    """The config document, as text. Deterministic for deterministic inputs."""
    spec, plain, sets, sets_spec = collect(name, cfg, runtime, fields)
    order = list(spec.get('module_order', []))
    for module in sorted(set(plain) | set(sets)):
        if module not in order:
            order.append(module)
    attrs = spec.get('module_attributes', '')

    lines = [XML_DECL, spec['doctype'], '<%s>' % spec['root']]
    for module in order:
        if module not in plain and module not in sets:
            continue
        lines.append('%s<module name="%s"%s>' % (TAB, module, attrs))
        for param in sorted(plain.get(module, {})):
            value, _ = plain[module][param]
            lines.append('%s<param name="%s" value="%s" />' % (TAB * 2, param, value))
        for set_type in sorted(sets.get(module, {})):
            st = sets_spec.get(set_type)
            if st is None:
                raise ConfigError('parameterset type %r is not declared in %s'
                                  % (set_type, SCHEMA))
            repeat = st.get('repeat_over')
            repeats = [None]
            allowed_of_key = {}
            if repeat:
                repeats = _resolve(cfg, repeat['field'])
                restrict = repeat.get('restrict')
                if restrict:
                    # {set key -> [repeat values]}: a key absent from the dict
                    # is emitted for every repeat value. This is how a strategy
                    # is declared for SOME subpopulations (a boundary-tier
                    # agent's mode is measured data, not a choice) without a
                    # second weight table.
                    allowed_of_key = _resolve(cfg, restrict['field']) or {}
            for repeat_value in repeats:
                for key in sorted(sets[module][set_type]):
                    if (repeat_value is not None and key in allowed_of_key
                            and repeat_value not in allowed_of_key[key]):
                        continue
                    body = sets[module][set_type][key]
                    lines.append('%s<parameterset type="%s"%s>'
                                 % (TAB * 2, set_type, attrs))
                    lines.append('%s<param name="%s" value="%s" />'
                                 % (TAB * 3, st['key_param'], key))
                    if repeat_value is not None:
                        lines.append('%s<param name="%s" value="%s" />'
                                     % (TAB * 3, repeat['param'], render(repeat_value)))
                    for param in sorted(body):
                        value, _ = body[param]
                        lines.append('%s<param name="%s" value="%s" />'
                                     % (TAB * 3, param, value))
                    lines.append('%s</parameterset>' % (TAB * 2))
        lines.append('%s</module>' % TAB)
    lines += ['</%s>' % spec['root'], '']
    return '\n'.join(lines)


def write(path, name, cfg, runtime=None, fields=None):
    text = emit(name, cfg, runtime, fields)
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return path


# --------------------------------------------------------------------------
# the two checks that make this structural rather than stylistic
# --------------------------------------------------------------------------
def closure(name, cfg, runtime=None, fields=None):
    """Every parameter's origin. Anything not a field key or a role is a leak.

    Returns [(param_path, origin)] for parameters that came from neither the
    registry nor a declared runtime role. It is always empty by construction
    today - `collect` refuses an undeclared role - so this is a REGRESSION test
    on that construction, which is exactly the class of guarantee this
    repository keeps losing when somebody adds a convenience path.
    """
    spec, plain, sets, _ = collect(name, cfg, runtime, fields)
    known = set(cfg.keys())
    roles = set(schema()['runtime_roles'])
    leaks = []
    for module in sorted(plain):
        for param in sorted(plain[module]):
            _, origin = plain[module][param]
            if origin not in known and origin.split(':')[0] not in roles:
                leaks.append(('%s.%s' % (module, param), origin))
    for module in sorted(sets):
        for set_type in sorted(sets[module]):
            for key in sorted(sets[module][set_type]):
                for param in sorted(sets[module][set_type][key]):
                    _, origin = sets[module][set_type][key][param]
                    if origin not in known and origin.split(':')[0] not in roles:
                        leaks.append(('%s.%s[%s].%s' % (module, set_type, key, param),
                                      origin))
    return leaks


def bound_fields(name, fields=None):
    """Every field carrying this tool's binding."""
    binding = tool(name)['binding']
    fields = fields if fields is not None else _registry.load_registry()[0]
    return sorted(k for k, f in fields.items()
                  if isinstance(f, dict) and f.get(binding))


def nudge(value):
    """A different value of the same shape, for the reach test.

    Not a plausible value and not meant to be: it is only ever rendered into a
    throwaway config and compared. It must merely DIFFER, in every type the
    registry carries.
    """
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return type(value)(value + 1) if value != -1 else type(value)(0)
    if isinstance(value, str):
        return value + 'X'
    if isinstance(value, list):
        return list(value) + ['X'] if value else ['X']
    if isinstance(value, dict):
        return {k: nudge(v) for k, v in value.items()}
    return 'X'


def reach(name, cfg, runtime=None):
    """Which bound fields actually move the emitted config, proven by moving them.

    Returns (reaching, inert). A field in `inert` carries a binding, resolves,
    is written into the run's provenance snapshot - and changes nothing. That is
    the repository's signature defect, and this is the only check that can see
    it: `consumers` is a claim, a substring search finds the key in a comment,
    and reading the code has never once caught an instance.

    The nudge is applied to the RESOLVED value, not through an overlay, so a
    field that is held fixed or outside its sweep is still testable - the
    question here is whether the wiring exists, not whether the value is allowed.
    """
    fields, _ = _registry.load_registry()
    base = emit(name, cfg, runtime, fields)
    reaching, inert = [], []
    for key in bound_fields(name, fields):
        original = fields[key]
        # A `computed` field has no declared value to nudge - it is an identity
        # the caller evaluates and supplies under the `derived` runtime role.
        # Its reach is established the other way round and more strongly: the
        # emitter REFUSES to produce a config at all if the caller does not
        # supply it, so it cannot silently go missing.
        if original.get('status') == 'computed':
            continue
        try:
            probe = dict(original)
            probe['value'] = nudge(_resolve(cfg, key))
        except _registry.RegistryError:
            # An unobtained field with no override has no value to nudge. It
            # cannot be tested here and is not claimed to have been.
            continue
        patched = dict(fields)
        patched[key] = probe
        moved = _emit_with_override(name, cfg, runtime, patched, key, probe['value'])
        (reaching if moved != base else inert).append(key)
    return reaching, inert


def _emit_with_override(name, cfg, runtime, fields, key, value):
    """Emit with one field's value replaced, without mutating the resolution."""
    class _Shim(object):
        def __init__(self, inner):
            self._inner = inner

        def get(self, k, caller=None):
            if k == key:
                return value
            return self._inner.get(k, caller=caller)

        def field(self, k):
            return fields[k] if k in fields else self._inner.field(k)

        def keys(self):
            return self._inner.keys()

    return emit(name, _Shim(cfg), runtime, fields)
