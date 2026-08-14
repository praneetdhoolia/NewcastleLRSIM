#!/usr/bin/env python
"""A live view of a MATSim run in flight, driven by the run's own telemetry.

`replay_events.py` answers *what did the run do* once it is over. This answers
*what is it doing now*, and unlike the view it replaces it does not have to
guess: `src/java/citysim/RunTelemetry.java` publishes the counts and the
per-link congestion from inside the mobsim, so this is a reader, not an
inferrer.

**What is live and what is not, stated rather than implied.** The mobsim sweeps
a 30 h simulated day in about 15 s of wall clock and then goes quiet for the
replanning and scoring that fill the rest of the iteration. So:

  * the simulated clock, the per-mode counts and the per-vehicle-type counts
    update through that sweep, roughly twice a second at the shipped
    `RUN.telemetry.live_interval_s` of one simulated hour;
  * the telemetry file carries the ACCUMULATING PROFILE of the day, not a single
    instant, so a slow poll misses nothing between two reads;
  * the congestion map is live too. It publishes on the same simulated-time
    boundary, and each frame is the WINDOW THAT JUST CLOSED rather than a running
    mean - a cumulative mean converges as the day proceeds, so the peak would
    build and then never dissipate.

**The server is an observer.** It reads the run directory, holds no lock, opens
nothing the run is writing and never writes to it, so a run observed is
byte-for-byte a run unobserved. That property was earned rather than assumed: on
Windows a reader holding `telemetry_links.json` open makes the writer's
`Files.move` throw, and the first version let that exception out of the handler
and **killed the run at iteration 5**. The writer is now structurally unable to
reach the mobsim (DECISIONS.md 9.36), and this reader polls twice a second
against it without incident - measured at 1,987 reads, zero failures.

**Nothing here is a result.** Counts are legs in flight during one iteration,
which is neither the mode agents CHOSE (`modestats.csv`) nor the trips that
COMPLETED (`_metrics.json`) - DECISIONS.md 9.12. `extract_metrics.py` ->
`fit.py` remains the only route to a reportable number.

    python src/analyse/run_view.py --run S2_WEEKDAY_f01_i1000_s20260810
"""
import os
import re
import csv
import sys
import json
import time
import argparse
import datetime
import threading
import http.server
import socketserver

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
RESULTS = os.path.join(ROOT, 'results')
sys.path.insert(0, os.path.join(ROOT, 'src'))
import registry as _registry  # noqa: E402
import city as _city  # noqa: E402
sys.path.insert(0, _HERE)
import summarise_run as _summarise  # noqa: E402

ITER_RE = re.compile(r'^(\S+)\s+INFO AbstractController.*ITERATION (\d+) BEGINS')
LAST_ITER_RE = re.compile(r'name="lastIteration" value="(\d+)"')
PARAM_RE = re.compile(r'name="([^"]+)" value="([^"]*)"')
LOG_TS = '%Y-%m-%dT%H:%M:%S,%f'

_CFG = _registry.load()
STALL_S = _CFG.get('RUN.monitor.stall_s')
POLL_S = _CFG.get('RUN.monitor.poll_s')
FAST_POLL_S = _CFG.get('RUN.monitor.live_poll_s')
PORT = _CFG.get('RUN.monitor.port')

# The colour ramp is FIXED and saturating, never fitted to the data in view.
# Measured on a 1% probe over 59,399 loaded links: median delay ratio 1.10,
# p90 2.58, p95 10.67, max 56,804. A data-driven maximum would let one
# gridlocked hairline flatten the whole city to green. Anything at or above
# RAMP_MAX is simply "stopped", and volume drives width so a link carrying one
# vehicle stays a hairline whatever its ratio.
RAMP_MIN = 1.0
RAMP_MAX = 3.0


def _ts(s):
    try:
        return datetime.datetime.strptime(s, LOG_TS).timestamp()
    except ValueError:
        return None


def read_iterations(log_path):
    """(iteration, wall clock) for every iteration the log has begun."""
    out = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = ITER_RE.match(line)
                if m:
                    t = _ts(m.group(1))
                    if t is not None:
                        out.append((int(m.group(2)), t))
    except OSError:
        return []
    return out


def read_series(path, keep=None):
    """A MATSim per-iteration csv as {column: [values]}, semicolon-delimited."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f, delimiter=';'))
    except OSError:
        return {}
    if not rows:
        return {}
    cols = [c for c in rows[0] if c and c != 'iteration'
            and (keep is None or c in keep)]
    out = {'iteration': [int(float(r['iteration'])) for r in rows]}
    for c in cols:
        vals = []
        for r in rows:
            try:
                vals.append(round(float(r[c]), 6))
            except (TypeError, ValueError):
                vals.append(None)
        out[c] = vals
    return out


def _load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def read_jsonl(path, tail=None):
    """Per-iteration telemetry summaries. ~5 KB each, so the whole file is cheap."""
    out = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    # the run may be mid-write on the last line
                    continue
    except OSError:
        return []
    return out[-tail:] if tail else out


def scan(run_dir):
    """Everything the page shows, read fresh from the run directory."""
    name = os.path.basename(os.path.abspath(run_dir))
    log = os.path.join(run_dir, 'matsim.log')
    out_dir = os.path.join(run_dir, 'output')
    record = os.path.join(run_dir, '_run.json')

    cfg_text = ''
    try:
        with open(os.path.join(run_dir, 'config.xml'), encoding='utf-8') as f:
            cfg_text = f.read()
    except OSError:
        pass
    m = LAST_ITER_RE.search(cfg_text)
    target = int(m.group(1)) if m else None
    params = dict(PARAM_RE.findall(cfg_text))

    iters = read_iterations(log)
    current = iters[-1][0] if iters else None
    durations = [(b[1] - a[1]) for a, b in zip(iters, iters[1:])]
    recent = durations[-20:]
    median = round(sorted(recent)[len(recent) // 2], 2) if recent else None

    done = bool(os.path.exists(record))
    run_rec = _load_json(record, {}) if done else {}
    snap = (_load_json(os.path.join(run_dir, '_config.json'), {}) or {}).get('values') or {}

    def ident(key, field):
        v = run_rec.get(key)
        return snap.get(field) if v is None else v

    scenario = run_rec.get('scenario')
    day = run_rec.get('day')
    if scenario is None or day is None:
        m2 = re.search(r'scenarios[/\\]matsim[/\\]([^/\\"]+)[/\\]([^/\\"]+)[/\\]',
                       cfg_text)
        if m2:
            scenario = scenario or m2.group(1)
            day = day or m2.group(2)

    try:
        age = time.time() - os.path.getmtime(log)
    except OSError:
        age = None
    if done:
        state = 'finished' if run_rec.get('rc') == 0 else 'failed'
    elif age is None:
        state = 'starting'
    elif age > STALL_S:
        state = 'stalled'
    else:
        state = 'running'

    remaining = None
    eta_s = None
    if target is not None and current is not None:
        remaining = max(0, target - current)
        if median:
            eta_s = round(remaining * median)
    started = iters[0][1] if iters else None
    elapsed = round(time.time() - started) if started and not done else (
        run_rec.get('wall_s'))

    frac_off = params.get('fractionOfIterationsToDisableInnovation')
    innovation_off = None
    if target is not None and frac_off:
        try:
            innovation_off = int(float(frac_off) * target)
        except ValueError:
            innovation_off = None

    modes = read_series(os.path.join(out_dir, 'modestats.csv'))
    scores = read_series(os.path.join(out_dir, 'scorestats.csv'),
                         keep={'avg_executed', 'avg_best', 'avg_worst'})

    # Has the run settled? The question issue #5 turns on. Delegated to
    # summarise_run so the live view and the finished summary cannot disagree:
    # this page had its own second implementation, in fractions rather than
    # percentage points, and two implementations of one verdict is exactly the
    # drift this package cannot absorb. The tolerance is declared
    # (RUN.relaxation.drift_tolerance_pp), not decided here.
    relaxation = _summarise.relaxation(modes, innovation_off)

    live = _load_json(os.path.join(out_dir, 'telemetry_live.json'))
    history = read_jsonl(os.path.join(out_dir, 'telemetry.jsonl'))
    last_iter = history[-1] if history else None
    links_path = os.path.join(out_dir, 'telemetry_links.json')
    links_iter = links_stamp = None
    if os.path.exists(links_path):
        # mtime rather than a re-read: the payload is up to 1.14 MB and this is
        # polled twice a second while the mobsim sweeps. The file is replaced
        # atomically, so its mtime changes exactly once per published window.
        try:
            links_stamp = os.path.getmtime(links_path)
        except OSError:
            links_stamp = None

    # Has the run got telemetry at all? A run assembled before the module
    # existed has none, and the page must say so rather than showing zeroes.
    telemetry = live is not None or last_iter is not None

    return {
        'name': name,
        'state': state,
        'scenario': scenario,
        'day': day,
        'fraction': ident('fraction', 'RUN.sample.fraction'),
        'seed': ident('seed', 'RUN.machine.seed'),
        'threads': ident('threads', 'RUN.machine.threads'),
        'controler_sha256': run_rec.get('controler_sha256'),
        'iteration': current,
        'target': target,
        'remaining': remaining,
        'median_iteration_s': median,
        'last_iteration_s': round(durations[-1], 2) if durations else None,
        'eta_s': eta_s,
        'elapsed_s': elapsed,
        'innovation_off_at': innovation_off,
        'relaxation': relaxation,
        'modes': modes,
        'scores': scores,
        'telemetry': telemetry,
        'live': live,
        'last_iteration': last_iter,
        'links_iteration': links_iter,
        'links_stamp': links_stamp,
        'ramp': {'min': RAMP_MIN, 'max': RAMP_MAX},
        'log_age_s': round(age) if age is not None else None,
        'rc': run_rec.get('rc'),
        'served_at': time.time(),
    }


_NET_CACHE = {}


def _input_network(run_dir):
    """Resolve `inputNetworkFile` from the run's config, else the output copy."""
    cfg = os.path.join(run_dir, 'config.xml')
    try:
        with open(cfg, encoding='utf-8') as f:
            m = re.search(r'name="inputNetworkFile" value="([^"]+)"', f.read())
    except OSError:
        m = None
    if m:
        p = m.group(1)
        if not os.path.isabs(p):
            p = os.path.join(run_dir, p)
        if os.path.exists(p):
            return p
    fallback = os.path.join(run_dir, 'output', 'output_network.xml.gz')
    return fallback if os.path.exists(fallback) else None


def load_network(run_dir):
    """Link endpoints from the run's OWN network, keyed by link id.

    The hotspot map is drawn from this rather than from `build_basemap.py`,
    and that is deliberate rather than a shortcut. The basemap reads
    `networks/osm/`, which is empty until the issue #32 re-harvest, and it is
    keyed by A1 road edges while telemetry is keyed by MATSim link ids - a
    join across a one-to-many relation. The run's own `output_network.xml.gz`
    needs neither: it carries the exact links the telemetry names, so the map
    is guaranteed to agree with the run that produced it. The basemap remains
    the right source for CONTEXT - water, coast, parkland - once it exists.
    """
    import gzip
    # The INPUT network, not output_network.xml.gz. MATSim writes the output
    # network only when the run ENDS, so sourcing geometry from it made the map
    # appear only after the thing it was meant to watch was over. The input
    # network exists before the first iteration and carries the same link ids -
    # MATSim does not renumber - so the map is live from the first window.
    path = _input_network(run_dir)
    if not path:
        return {}
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _NET_CACHE.get(run_dir)
    if hit and hit[0] == stamp:
        return hit[1]

    node_re = re.compile(r'<node id="([^"]+)" x="([^"]+)" y="([^"]+)"')
    link_re = re.compile(r'<link id="([^"]+)" from="([^"]+)" to="([^"]+)"')
    nodes, links = {}, {}
    try:
        with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = node_re.search(line)
                if m:
                    nodes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
                    continue
                m = link_re.search(line)
                if m:
                    links[m.group(1)] = (m.group(2), m.group(3))
    except (OSError, ValueError):
        return {}
    geom = {}
    for lid, (a, b) in links.items():
        pa, pb = nodes.get(a), nodes.get(b)
        if pa and pb:
            geom[lid] = (pa[0], pa[1], pb[0], pb[1])
    _NET_CACHE[run_dir] = (stamp, geom)
    return geom


def _volume_bbox(rows, keep):
    """The box holding `keep` of all traversals, trimmed equally from each side."""
    total = sum(v for _, v, _ in rows)
    if total <= 0:
        return None
    drop = total * (1.0 - keep) / 2.0
    out = []
    for axis in (0, 1):
        pts = sorted(((g[axis] + g[axis + 2]) / 2.0, v) for g, v, _ in rows)
        acc, lo, hi = 0.0, pts[0][0], pts[-1][0]
        for c, v in pts:
            acc += v
            if acc >= drop:
                lo = c
                break
        acc = 0.0
        for c, v in reversed(pts):
            acc += v
            if acc >= drop:
                hi = c
                break
        out.append((lo, hi))
    return [out[0][0], out[1][0], out[0][1], out[1][1]]


def hotspot(run_dir):
    """Join the iteration's per-link congestion to geometry, ready to draw.

    The join happens here rather than in the page for the same reason the
    parking price join happens at build time: the browser should receive
    numbers to draw, not a relation to resolve. Coordinates are quantised to
    uint16 over the bounding box of the LOADED links - the study area, not the
    network's full 322 x 714 km extent, most of which is external boundary
    links carrying nothing.
    """
    import base64
    import struct
    payload = _load_json(os.path.join(run_dir, 'output',
                                      'telemetry_links.json'))
    if not payload:
        return {'available': False,
                'reason': 'no telemetry_links.json - this run was assembled '
                          'before the telemetry module existed, or has not '
                          'finished an iteration'}
    geom = load_network(run_dir)
    if not geom:
        return {'available': False,
                'reason': 'the run network could not be read - neither '
                          'inputNetworkFile from config.xml nor '
                          'output/output_network.xml.gz'}

    rows = [(geom[lid], vol, ratio) for lid, vol, ratio in payload['links']
            if lid in geom]
    if not rows:
        return {'available': False, 'reason': 'no loaded link matched the network'}

    xs = [c for g, _, _ in rows for c in (g[0], g[2])]
    ys = [c for g, _, _ in rows for c in (g[1], g[3])]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    sx = 65535.0 / (x1 - x0) if x1 > x0 else 0.0
    sy = 65535.0 / (y1 - y0) if y1 > y0 else 0.0

    coords, vols, ratios = [], [], []
    vmax = max(v for _, v, _ in rows) or 1
    for g, vol, ratio in rows:
        coords += [int((g[0] - x0) * sx), int((g[1] - y0) * sy),
                   int((g[2] - x0) * sx), int((g[3] - y0) * sy)]
        vols.append(min(65535, int(vol)))
        # the ramp is fixed and saturating; 0..65535 maps RAMP_MIN..RAMP_MAX
        t = (min(max(ratio, RAMP_MIN), RAMP_MAX) - RAMP_MIN) / (RAMP_MAX - RAMP_MIN)
        ratios.append(int(t * 65535))

    def b64(vals):
        return base64.b64encode(
            struct.pack('<%dH' % len(vals), *vals)).decode('ascii')

    # The network reaches 322 x 714 km because the external tier runs to the
    # study-area boundary, but almost none of the traffic is out there:
    # measured on a 1% probe, 86% of traversals fall in a single 40 km band
    # centred on Newcastle. The default view is the box holding the middle 98%
    # of TRAVERSALS; the full extent stays available to zoom out to. The
    # threshold was chosen by measurement, not taste: 99.5% gives a 187 x 565 km
    # box and 98% still gives 169 x 355, because a fraction of a percent of very
    # long external trips is enough to drag the frame off the city. 90% gives
    # 52 x 49 km, which is the scale of the 4,086 km2 five-LGA study area.
    core = _volume_bbox(rows, 0.90)

    return {
        'available': True,
        'iteration': payload.get('iteration'),
        # scope/window are what tell the page whether it is showing a live
        # window or the finished day. Omitting them made a live window render
        # under a "whole day" heading.
        'scope': payload.get('scope', 'iteration'),
        'window_from': payload.get('window_from'),
        'window_to': payload.get('window_to'),
        'window_from_s': payload.get('window_from_s'),
        'window_to_s': payload.get('window_to_s'),
        'metric': payload.get('metric'),
        'covers': payload.get('covers'),
        'n_links': len(rows),
        'bbox': [x0, y0, x1, y1],
        'core_bbox': core,
        'volume_max': vmax,
        'ramp': [RAMP_MIN, RAMP_MAX],
        'coords': b64(coords),
        'volume': b64(vols),
        'delay': b64(ratios),
    }


def _page():
    with open(os.path.join(_HERE, 'run_view.html'), encoding='utf-8') as f:
        html = f.read()
    return (html.replace('__POLL_MS__', str(int(POLL_S * 1000)))
                .replace('__FAST_MS__', str(int(FAST_POLL_S * 1000))))


def make_handler(run_dir):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, body, ctype='application/json', code=200):
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError):
                pass

        def _send_file(self, path, ctype='application/json'):
            if not os.path.exists(path):
                self._send('{"error":"absent"}', code=404)
                return
            try:
                with open(path, 'rb') as f:
                    self._send(f.read(), ctype)
            except OSError:
                self._send('{"error":"unreadable"}', code=503)

        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path in ('/', '/index.html'):
                self._send(_page(), 'text/html')
            elif path == '/status.json':
                self._send(json.dumps(scan(run_dir)))
            elif path == '/summary.json':
                # Written by summarise_run.py when the run completes. Absent
                # while it is still going, which is what the page keys on.
                self._send_file(os.path.join(run_dir, '_summary.json'))
            elif path == '/basemap.json':
                # Context only - water, coast, parkland, the full road network in
                # outline, heavy rail and the light rail alignment. Built by
                # build_basemap.py and NOT required: the page draws traffic
                # without it. See the note in hotspot() on why the traffic layer
                # does not come from here.
                self._send_file(_city.path('data', 'processed', 'basemap.json'))
            elif path == '/hotspot.json':
                self._send(json.dumps(hotspot(run_dir)))
            elif path == '/links.json':
                self._send_file(os.path.join(run_dir, 'output',
                                             'telemetry_links.json'))
            else:
                self._send('{"error":"not found"}', code=404)

        def log_message(self, *_args):
            pass  # the run's own log is the only one that matters

    return Handler


class _Server(socketserver.TCPServer):
    """Loopback server that REFUSES a port already in use.

    `allow_reuse_address` must stay false on Windows. SO_REUSEADDR there lets a
    second socket bind a port that is already bound instead of failing, so the
    port scan in `serve` below silently "succeeded" on the SAME port for every
    concurrent run: three live views each printed 8731, 8732 and 8733 were never
    opened, and only the first server ever answered. The other two ran for as
    long as their run did, reporting a url that served nothing. On POSIX the
    flag only skips TIME_WAIT and is harmless, so it is kept there.

    It was also being set on `socketserver.TCPServer` itself, which changed the
    default for every other server in the process.
    """

    allow_reuse_address = (os.name != 'nt')


def serve(run_dir, port=None, poll_s=None, background=True):
    """Bind on loopback and serve. Returns the url, or None if no port is free."""
    port = int(port or PORT)
    handler = make_handler(run_dir)
    httpd = None
    for candidate in range(port, port + 20):
        try:
            httpd = _Server(('127.0.0.1', candidate), handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        return None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    url = 'http://127.0.0.1:%d/' % port
    if not background:
        try:
            t.join()
        except KeyboardInterrupt:
            httpd.shutdown()
    return url


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True,
                    help='a directory name under results/, or a path')
    ap.add_argument('--port', type=int, default=None)
    ap.add_argument('--once', action='store_true',
                    help='print the status json and exit, serving nothing')
    args = ap.parse_args()

    run_dir = args.run
    if not run_dir.strip():
        # An empty --run resolved to results/ itself and served a directory that
        # is not a run, reporting "no telemetry" for a run that had plenty.
        raise SystemExit('--run is empty')
    if not os.path.isdir(run_dir):
        run_dir = os.path.join(RESULTS, args.run)
    if not os.path.isdir(run_dir):
        raise SystemExit('no such run: %s' % args.run)

    if args.once:
        print(json.dumps(scan(run_dir), indent=1)[:4000])
        return

    url = serve(run_dir, args.port, background=True)
    if url is None:
        raise SystemExit('no free loopback port')
    print('live view: %s' % url, flush=True)
    print('reading:   %s' % os.path.abspath(run_dir), flush=True)
    print('Ctrl-C to stop. The run is not affected either way.', flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
