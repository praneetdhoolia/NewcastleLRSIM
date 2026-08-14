#!/usr/bin/env python
"""Where one city's inputs live, and the only module that knows.

`config/schema/` is portable - what any city must supply and what shape it must
be in. `cities/<city>/` is one instance of it: that city's registry values, its
scenario/day/run overlays, its acquisition adapters, and every byte of data,
network, schedule, demand and scenario artefact derived from them.

The split is not cosmetic. Before it, 338 path literals across 46 framework
scripts named `data/`, `networks/`, `schedules/`, `demand/`, `scenarios/` and
`params/` as though a repository could only ever hold one city - and the OSM
harvest box in the extract layer clipped 87 of 1,500 core SA1s out of the road
network for three phases precisely because a typed-in constant cannot be wrong
in a way anyone notices. A second city inheriting those literals inherits the
same class of defect.

    import city
    city.path('data/processed/network/A1_road_edges.csv')

Paths returned are ABSOLUTE, so a script works from any working directory. The
argument stays city-relative, which is deliberate: it is exactly the path
recorded in that city's `data/MANIFEST.csv`, so the manifest describes a city
rather than repeating the city's own name on all 376 of its rows.

The city is selected by `CITYSIM_CITY` (default `newcastle`) - the same
selector the registry resolver uses, and an environment prefix that is itself a
suburb name awaiting rename.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CITIES_DIR = os.path.join(REPO, 'cities')

# Environment variables the FRAMEWORK reserves for itself. They select and
# locate a city; they are not registry field overrides, and the resolver must
# skip them when it reads `CITYSIM_*` from the environment.
#
# It did not. Setting CITYSIM_CITY to anything at all - INCLUDING ITS OWN
# DEFAULT - made every `registry.load()` raise "env CITYSIM_CITY matches no
# registry field", so the city selector documented in README.md, docs/README.md
# and .claude/CLAUDE.md could not be used. Nobody had set it: one city, and the
# default is applied when the variable is absent. The bug surfaced the first
# time a second city was actually exercised.
DEFAULT_CITY = 'newcastle'
CITY_ENV = 'CITYSIM_CITY'
RESERVED_ENV = (CITY_ENV, 'CITYSIM_REPO')

# `or` rather than a get() default: an EMPTY variable is not a city, and it
# resolved to `cities/` itself - which then failed several hundred lines
# later with 'no registry fields found', naming a directory nobody set.
CITY = os.environ.get(CITY_ENV, '').strip() or DEFAULT_CITY
CITY_DIR = os.path.join(CITIES_DIR, CITY)

SCHEMA_DIR = os.path.join(REPO, 'config', 'schema')

# The subdirectories of a city that the framework knows by name. A city that is
# missing one of these is not runnable, and `check_city.py` says so before a run
# starts rather than at the first read.
LAYERS = ('registry', 'overlays', 'extract', 'data', 'networks', 'schedules',
          'demand', 'scenarios', 'params')


class CityError(Exception):
    """A city that cannot be resolved. Always fatal - never fall back."""


def path(*parts):
    """Absolute path to a city-relative location. Does not require it to exist."""
    return os.path.join(CITY_DIR, *parts)


def rel(absolute):
    """Inverse of `path`: an absolute path back to its city-relative form.

    Used when writing the manifest and any other record that must describe the
    city rather than this checkout's location on disk.
    """
    return os.path.relpath(absolute, CITY_DIR).replace(os.sep, '/')


def available():
    """Every city this repository carries, whether or not it is complete."""
    if not os.path.isdir(CITIES_DIR):
        return []
    return sorted(d for d in os.listdir(CITIES_DIR)
                  if os.path.isdir(os.path.join(CITIES_DIR, d)))


def require(city=None):
    """Fail loudly, and early, on a city that is not there.

    Reports what IS there, because the common cause is a typo in CITYSIM_CITY
    and the common symptom without this is a FileNotFoundError several hundred
    lines into a build.
    """
    name = city or CITY
    directory = os.path.join(CITIES_DIR, name)
    if not os.path.isdir(directory):
        raise CityError('no city %r at %s\navailable: %s'
                        % (name, directory, ', '.join(available()) or 'none'))
    missing = [d for d in LAYERS if not os.path.isdir(os.path.join(directory, d))]
    if missing:
        raise CityError('city %r is missing: %s' % (name, ', '.join(missing)))
    return directory


# --------------------------------------------------------------------------
# the descriptor: identity values that used to be typed into framework modules
# --------------------------------------------------------------------------
_DESCRIPTOR = {}


def descriptor(name=None):
    """This city's `city.json`, parsed once and cached.

    Everything here was previously a literal in a framework module - the CRS in
    seven of them, the mode-share filter value in three. A framework constant
    that happens to be one city's value is the same defect as a typed-in
    rectangle: it is invisible until a second city is tried.
    """
    key = name or CITY
    if key not in _DESCRIPTOR:
        path_ = os.path.join(CITIES_DIR, key, 'city.json')
        if not os.path.exists(path_):
            raise CityError('city %r has no city.json at %s' % (key, path_))
        with open(path_, encoding='utf-8') as f:
            _DESCRIPTOR[key] = json.load(f)
    return _DESCRIPTOR[key]


def crs():
    """The projected CRS every metric layer is in, as an EPSG string."""
    return 'EPSG:%d' % descriptor()['crs']['epsg']


def crs_label():
    """The CRS with its datum spelled out, for records a person reads.

    The datum is not decoration: EPSG:28356 is GDA94 and EPSG:7856 is its
    GDA2020 counterpart, and this repository labelled the first as the second
    in four documents at once.
    """
    c = descriptor()['crs']
    parts = [c['datum']] + ([c['zone']] if c.get('zone') else [])
    return 'EPSG:%d (%s)' % (c['epsg'], ' / '.join(parts))


def target_lga():
    """The literal the observed mode-share series is filtered on."""
    return descriptor()['mode_share_target']['filter_value']


def base_year():
    return descriptor()['base_year']


def geometry(name):
    """A declared geometry document from this city's `geometry/` directory.

    Coordinates that were typed into framework build scripts live here instead:
    a rectangle in a script is invisible, and one of them clipped 87 core SA1s
    out of the road network for three phases before anyone noticed.
    """
    path_ = os.path.join(CITY_DIR, 'geometry', '%s.json' % name)
    if not os.path.exists(path_):
        raise CityError('city %r declares no geometry %r (expected %s)'
                        % (CITY, name, path_))
    with open(path_, encoding='utf-8') as f:
        return json.load(f)


def extent(name):
    """One declared extent as the (s, w, n, e) dict the build scripts expect."""
    doc = geometry('analysis_extents')['extents']
    if name not in doc:
        raise CityError('city %r declares no extent %r (has: %s)'
                        % (CITY, name, ', '.join(sorted(doc))))
    e = doc[name]
    return dict(s=e['south'], w=e['west'], n=e['north'], e=e['east'])
