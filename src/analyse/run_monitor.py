#!/usr/bin/env python
"""A live view of a MATSim run in flight: progress, convergence, cost.

`replay_events.py` answers *what did the run do* once it is over, from the
event stream. This answers *what is it doing now*, and the two are deliberately
different instruments. A live map is not one of them: MATSim is not a real-time
simulator, and the measurement says why. Events are written only every
`RUN.controler.write_events_interval` iterations, and when they are written the
whole 30 h simulated day lands in about 50 s of wall clock - roughly 2,000x real
time - followed by minutes of silence. There is no steady stream to watch, so
what a live map would show is a flicker, then a blank screen. What actually
changes at a human pace is the run's PROGRESS and its CONVERGENCE, and that is
what this serves.

The page polls `/status.json`; nothing is precomputed and no state is kept, so
the server is a reader of the run directory and never a writer to it. It holds
no lock, opens no output the run is writing, and cannot alter a result: a run
observed is byte-for-byte a run unobserved.

**modestats is not a result.** The mode trajectory here is the mode agents
CHOSE, not trips that COMPLETED (DECISIONS.md 9.12), and the page says so on its
face. `extract_metrics.py` -> `fit.py` remains the only route to a reportable
number.

    python src/analyse/run_monitor.py --run S2_WEEKDAY_f01_i250_s20260810
"""
import os
import re
import csv
import sys
import json
import time
import errno
import threading
import argparse
import datetime
import http.server
import socketserver

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
RESULTS = os.path.join(ROOT, 'results')
sys.path.insert(0, os.path.join(ROOT, 'src'))
import registry as _registry  # noqa: E402

ITER_RE = re.compile(r'^(\S+)\s+INFO AbstractController.*ITERATION (\d+) BEGINS')
LAST_ITER_RE = re.compile(r'name="lastIteration" value="(\d+)"')
PARAM_RE = re.compile(r'name="([^"]+)" value="([^"]*)"')
# MATSim stamps its log in local time with a comma before the milliseconds
LOG_TS = '%Y-%m-%dT%H:%M:%S,%f'
# How long the log may go quiet before a run is called stalled rather than
# running. A registry field, not a literal - check_package.py tests the rule.
STALL_S = _registry.load().get('RUN.monitor.stall_s')


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
    # per-iteration wall time, from the gaps between successive begins
    durations = [(b[1] - a[1]) for a, b in zip(iters, iters[1:])]
    recent = durations[-20:]
    median = round(sorted(recent)[len(recent) // 2], 2) if recent else None

    done = bool(os.path.exists(record))
    run_rec = {}
    if done:
        try:
            with open(record, encoding='utf-8') as f:
                run_rec = json.load(f)
        except (OSError, ValueError):
            run_rec = {}
    # `_run.json` is written when the run ENDS, which is exactly when nobody is
    # watching. The resolved snapshot `_config.json` is written before MATSim
    # starts, so the run can identify itself from its first second.
    snap = {}
    try:
        with open(os.path.join(run_dir, '_config.json'), encoding='utf-8') as f:
            snap = json.load(f).get('values') or {}
    except (OSError, ValueError):
        snap = {}

    def ident(key, field):
        v = run_rec.get(key)
        return snap.get(field) if v is None else v

    # scenario and day are not registry fields - they name which assembled set
    # was run - so they come from the run record, else from the directory name
    # `inputPlansFile` points at the run's own subsample, so it names neither.
    # The transit schedule still points into the assembled set, whose path IS
    # scenario and day type.
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

    # innovation switches off at this fraction of the run: after it, no new
    # plans are created, so any remaining drift is the relaxation question
    # issue 5 turns on
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

    # post-innovation drift: the direct read on whether this run has relaxed
    drift = {}
    if innovation_off is not None and modes.get('iteration'):
        it = modes['iteration']
        try:
            i0 = next(i for i, v in enumerate(it) if v >= innovation_off)
        except StopIteration:
            i0 = None
        if i0 is not None and len(it) - 1 > i0:
            for k, v in modes.items():
                if k == 'iteration' or v[i0] is None or v[-1] is None:
                    continue
                drift[k] = round(v[-1] - v[i0], 5)

    return {
        'name': name,
        'state': state,
        'scenario': scenario,
        'day': day,
        'fraction': ident('fraction', 'RUN.sample.fraction'),
        'seed': ident('seed', 'RUN.machine.seed'),
        'threads': ident('threads', 'RUN.machine.threads'),
        'iteration': current,
        'target': target,
        'remaining': remaining,
        'median_iteration_s': median,
        'last_iteration_s': round(durations[-1], 2) if durations else None,
        'eta_s': eta_s,
        'elapsed_s': elapsed,
        'innovation_off_at': innovation_off,
        'post_innovation_drift': drift,
        'modes': modes,
        'scores': scores,
        'log_age_s': round(age) if age is not None else None,
        'rc': run_rec.get('rc'),
        'served_at': time.time(),
    }


PAGE = r"""<title>{name} - run monitor</title>
<style>
:root{{
  --panel:#0E1719; --edge:#1E2E2D; --ink:#DCE6E4; --muted:#7A918F;
  --land:#101617; --warn:#E06A5E; --ok:#8FD694;
  --car:#F0A93C; --ride:#E074AC; --pt:#4FD0E0; --walk:#8FD694; --bike:#9B8FE0;
  --mono:ui-monospace,"Cascadia Mono","SF Mono",Menlo,Consolas,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--land);color:var(--ink);font-family:var(--sans);
  font-size:14px;line-height:1.45}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:15px;font-weight:600;margin:0;letter-spacing:.01em}}
.sub{{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:4px}}
.card{{background:var(--panel);border:1px solid var(--edge);border-radius:10px;
  padding:18px 20px;margin-top:16px}}
.bar{{height:12px;background:#16211F;border-radius:6px;overflow:hidden;margin:14px 0 10px}}
.bar>i{{display:block;height:100%;background:linear-gradient(90deg,#2E7D6B,#4FD0E0);
  border-radius:6px;transition:width .4s ease}}
.row{{display:flex;flex-wrap:wrap;gap:26px;font-family:var(--mono);font-size:12px}}
.row b{{display:block;color:var(--muted);font-weight:400;font-size:11px;
  letter-spacing:.04em;text-transform:uppercase;margin-bottom:3px}}
.row span{{font-size:15px;color:var(--ink)}}
.pill{{display:inline-block;padding:2px 9px;border-radius:999px;font-family:var(--mono);
  font-size:11px;letter-spacing:.05em;text-transform:uppercase}}
.running{{background:#123A33;color:#4FD0E0}} .finished{{background:#1B3A22;color:var(--ok)}}
.failed,.stalled{{background:#3A1B1B;color:var(--warn)}} .starting{{background:#2A2A16;color:#E0CE74}}
svg{{display:block;width:100%;height:auto;overflow:visible}}
.k{{display:flex;gap:16px;flex-wrap:wrap;font-family:var(--mono);font-size:11px;
  color:var(--muted);margin-top:10px}}
.k i{{display:inline-block;width:10px;height:2px;vertical-align:middle;margin-right:5px}}
.note{{font-size:11px;color:var(--muted);margin-top:10px;font-family:var(--mono);
  border-left:2px solid var(--edge);padding-left:10px}}
h2{{font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.08em;
  text-transform:uppercase;margin:0 0 4px}}
.drift td{{font-family:var(--mono);font-size:12px;padding:2px 14px 2px 0}}
.drift td:last-child{{text-align:right}}
</style>
<div class="wrap">
  <h1 id="name">-</h1>
  <div class="sub" id="ident">-</div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2 style="margin:0">Progress</h2><span class="pill" id="state">-</span>
    </div>
    <div class="bar"><i id="fill" style="width:0%"></i></div>
    <div class="row">
      <div><b>iteration</b><span id="iter">-</span></div>
      <div><b>elapsed</b><span id="elapsed">-</span></div>
      <div><b>remaining</b><span id="eta">-</span></div>
      <div><b>per iteration</b><span id="per">-</span></div>
      <div><b>innovation off</b><span id="innov">-</span></div>
    </div>
  </div>

  <div class="card">
    <h2>Mode share by iteration</h2>
    <svg id="modes" viewBox="0 0 900 260" preserveAspectRatio="none"></svg>
    <div class="k" id="mkey"></div>
    <div class="note">modestats: the mode agents CHOSE, not trips that
      COMPLETED. A diagnostic of convergence, never a result - a reportable
      number comes only from extract_metrics.py then fit.py.</div>
  </div>

  <div class="card">
    <h2>Score by iteration</h2>
    <svg id="scores" viewBox="0 0 900 200" preserveAspectRatio="none"></svg>
    <div class="k" id="skey"></div>
  </div>

  <div class="card" id="driftcard" style="display:none">
    <h2>Drift after innovation stops</h2>
    <table class="drift"><tbody id="drift"></tbody></table>
    <div class="note">New plans stop being created at the marked iteration. Any
      movement after it is the relaxation question issue 5 turns on: a model
      still drifting once its search is off has not relaxed.</div>
  </div>
</div>
<script>
const MODE_COLOUR = {{car:'--car', ride:'--ride', pt:'--pt', walk:'--walk', bike:'--bike'}};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS = 'http://www.w3.org/2000/svg';

function hms(s) {{
  if (s === null || s === undefined) return '-';
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  if (h) return h + 'h ' + String(m).padStart(2, '0') + 'm';
  if (m) return m + 'm ' + String(s % 60).padStart(2, '0') + 's';
  return s + 's';
}}

function el(tag, attrs) {{
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}}

function plot(svg, series, iters, colours, W, H, marker) {{
  svg.textContent = '';
  const keys = Object.keys(series).filter(k => k !== 'iteration');
  if (!keys.length || !iters || iters.length < 2) return;
  const pad = {{l: 46, r: 10, t: 10, b: 20}};
  let lo = Infinity, hi = -Infinity;
  for (const k of keys) for (const v of series[k])
    if (v !== null) {{ if (v < lo) lo = v; if (v > hi) hi = v; }}
  if (!isFinite(lo)) return;
  if (hi === lo) {{ hi += 1; lo -= 1; }}
  const padY = (hi - lo) * 0.08; lo -= padY; hi += padY;
  const x0 = iters[0], x1 = iters[iters.length - 1];
  const X = v => pad.l + (v - x0) / Math.max(1, x1 - x0) * (W - pad.l - pad.r);
  const Y = v => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);

  for (let g = 0; g <= 3; g++) {{
    const v = lo + (hi - lo) * g / 3, y = Y(v);
    svg.appendChild(el('line', {{x1: pad.l, x2: W - pad.r, y1: y, y2: y,
      stroke: css('--edge'), 'stroke-width': 1}}));
    const t = el('text', {{x: pad.l - 8, y: y + 3.5, 'text-anchor': 'end',
      fill: css('--muted'), 'font-size': 10, 'font-family': css('--mono')}});
    t.textContent = Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
    svg.appendChild(t);
  }}
  if (marker !== null && marker !== undefined && marker >= x0 && marker <= x1) {{
    svg.appendChild(el('line', {{x1: X(marker), x2: X(marker), y1: pad.t, y2: H - pad.b,
      stroke: css('--muted'), 'stroke-width': 1, 'stroke-dasharray': '3 3'}}));
  }}
  for (const k of keys) {{
    let d = '', pen = false;
    series[k].forEach((v, i) => {{
      if (v === null) {{ pen = false; return; }}
      d += (pen ? 'L' : 'M') + X(iters[i]).toFixed(1) + ' ' + Y(v).toFixed(1) + ' ';
      pen = true;
    }});
    svg.appendChild(el('path', {{d: d, fill: 'none', 'stroke-width': 1.6,
      stroke: css(colours[k] || '--ink'), 'stroke-linejoin': 'round'}}));
  }}
  [x0, x1].forEach((v, i) => {{
    const t = el('text', {{x: X(v), y: H - 5, 'text-anchor': i ? 'end' : 'start',
      fill: css('--muted'), 'font-size': 10, 'font-family': css('--mono')}});
    t.textContent = v; svg.appendChild(t);
  }});
}}

function key(node, keys, colours, last) {{
  node.textContent = '';
  keys.forEach(k => {{
    const s = document.createElement('span');
    const v = last[k];
    s.innerHTML = '<i style="background:' + css(colours[k] || '--ink') + '"></i>' + k +
      (v === undefined || v === null ? '' : ' ' + (Math.abs(v) < 1 ? v.toFixed(4) : v.toFixed(1)));
    node.appendChild(s);
  }});
}}

async function tick() {{
  let d;
  try {{ d = await (await fetch('status.json', {{cache: 'no-store'}})).json(); }}
  catch (e) {{ return; }}
  document.getElementById('name').textContent = d.name;
  const bits = [];
  if (d.scenario) bits.push(d.scenario + ' x ' + d.day);
  if (d.fraction !== null && d.fraction !== undefined) bits.push((d.fraction * 100).toFixed(0) + '% sample');
  if (d.seed) bits.push('seed ' + d.seed);
  if (d.threads) bits.push(d.threads + ' threads');
  document.getElementById('ident').textContent = bits.join('  -  ') || 'reading run record ...';

  const st = document.getElementById('state');
  st.textContent = d.state; st.className = 'pill ' + d.state;
  const pct = (d.target && d.iteration !== null) ? Math.min(100, d.iteration / d.target * 100) : 0;
  document.getElementById('fill').style.width = pct.toFixed(1) + '%';
  document.getElementById('iter').textContent =
    (d.iteration === null ? '-' : d.iteration) + ' / ' + (d.target === null ? '?' : d.target) +
    '   ' + pct.toFixed(0) + '%';
  document.getElementById('elapsed').textContent = hms(d.elapsed_s);
  document.getElementById('eta').textContent = d.state === 'running' ? hms(d.eta_s) : '-';
  document.getElementById('per').textContent =
    d.median_iteration_s === null ? '-' : d.median_iteration_s.toFixed(1) + 's';
  document.getElementById('innov').textContent =
    d.innovation_off_at === null ? '-' : d.innovation_off_at;

  const mi = d.modes.iteration || [];
  const ms = Object.assign({{}}, d.modes); delete ms.iteration;
  plot(document.getElementById('modes'), ms, mi, MODE_COLOUR, 900, 260, d.innovation_off_at);
  const lastOf = s => {{ const o = {{}}; for (const k in s) o[k] = s[k][s[k].length - 1]; return o; }};
  key(document.getElementById('mkey'), Object.keys(ms), MODE_COLOUR, lastOf(ms));

  const si = d.scores.iteration || [];
  const ss = Object.assign({{}}, d.scores); delete ss.iteration;
  const SC = {{avg_executed: '--pt', avg_best: '--walk', avg_worst: '--warn'}};
  plot(document.getElementById('scores'), ss, si, SC, 900, 200, d.innovation_off_at);
  key(document.getElementById('skey'), Object.keys(ss), SC, lastOf(ss));

  const dr = d.post_innovation_drift || {{}};
  const card = document.getElementById('driftcard'), body = document.getElementById('drift');
  const ks = Object.keys(dr);
  card.style.display = ks.length ? '' : 'none';
  body.textContent = '';
  ks.sort().forEach(k => {{
    const tr = document.createElement('tr');
    const a = document.createElement('td'); a.textContent = k;
    const b = document.createElement('td');
    b.textContent = (dr[k] > 0 ? '+' : '') + dr[k].toFixed(4);
    b.style.color = Math.abs(dr[k]) > 0.005 ? css('--warn') : css('--ok');
    tr.appendChild(a); tr.appendChild(b); body.appendChild(tr);
  }});
  document.title = (d.iteration === null ? '' : d.iteration + '/' + d.target + ' ') + d.name;
}}
tick(); setInterval(tick, {poll}000);
</script>
"""


class _Handler(http.server.BaseHTTPRequestHandler):
    run_dir = None
    poll = 3

    def _send(self, body, ctype):
        raw = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(raw)
        except OSError:
            pass

    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ('/', '/index.html'):
            name = os.path.basename(os.path.abspath(self.run_dir))
            self._send(PAGE.format(name=name, poll=self.poll), 'text/html; charset=utf-8')
        elif path == '/status.json':
            self._send(json.dumps(scan(self.run_dir)), 'application/json')
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass          # the run's own stdout is the record; this is a viewer


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(run_dir, port, poll=3):
    """Start the viewer in a daemon thread. Returns its url, or None."""
    handler = type('H', (_Handler,), {'run_dir': run_dir, 'poll': poll})
    try:
        httpd = _Server(('127.0.0.1', port), handler)
    except OSError as e:
        if e.errno not in (errno.EADDRINUSE, errno.EACCES):
            raise
        try:
            httpd = _Server(('127.0.0.1', 0), handler)
        except OSError:
            return None
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d/' % httpd.server_address[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True, help='a directory under results/')
    ap.add_argument('--port', type=int, default=None,
                    help='override RUN.monitor.port')
    a = ap.parse_args()
    run_dir = a.run if os.path.isdir(a.run) else os.path.join(RESULTS, a.run)
    if not os.path.isdir(run_dir):
        raise SystemExit('no such run: %s' % run_dir)
    cfg = _registry.load()
    port = a.port if a.port is not None else cfg.get('RUN.monitor.port')
    url = serve(run_dir, port, cfg.get('RUN.monitor.poll_s'))
    if not url:
        raise SystemExit('could not bind a port for the run monitor')
    print('run monitor: %s' % url, flush=True)
    print('watching %s - Ctrl-C to stop' % run_dir, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
