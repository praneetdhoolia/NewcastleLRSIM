#!/usr/bin/env python
"""Assemble a basemap and an event replay into one self-contained page.

Both payloads are inlined rather than fetched: the page is meant to be opened
from anywhere, including as a published artefact, where a strict content policy
blocks every external host - which is also why nothing here is drawn by a
third-party map library. See build_basemap.py for that reasoning.

The view works in METRES, not in screen units. A road is stroked at its real
carriageway width, so zooming in widens it the way a road widens on a real map
instead of staying a fixed-weight wire. Past a threshold the SUMO per-lane
geometry takes over and individual lanes are drawn at their own widths. That is
the difference between a network diagram and a map.

The page is generated, never hand-edited, and is NOT committed: it carries
several megabytes of payload and this repo does not commit bulk data. The
scripts are the committed artefacts.

    python src/analyse/build_basemap.py --out basemap.json --no-simplify
    python src/analyse/replay_events.py results/<run>/output \
        --basemap basemap.json --out replay.json
    python src/analyse/build_replay_page.py replay.json --basemap basemap.json \
        --out replay.html
"""
import os
import json
import argparse

PAGE = r"""<title>{title}</title>
<style>
:root{{
  --panel:#0E1719; --edge:#1E2E2D; --ink:#DCE6E4; --muted:#7A918F;
  --water:#08161F; --land:#101617; --green:#111E15; --sand:#1D1B13;
  --casing:#05090A; --tarmac:#39484A; --marking:#7C9490;
  --rd5:#283335; --rd4:#31403F; --rd3:#3C4E4C; --rd2:#4B605C; --rd1:#66857A;
  --rail:#5B4668; --tram:#E074AC; --coast:#1B2E34;
  --car:#F0A93C; --transit:#4FD0E0; --warn:#E06A5E;
  --mono:ui-monospace,"Cascadia Mono","SF Mono",Menlo,Consolas,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--water);color:var(--ink);font-family:var(--sans);
  height:100vh;display:flex;flex-direction:column;overflow:hidden}}
header{{display:flex;flex-wrap:wrap;gap:.4rem 1.3rem;align-items:baseline;
  padding:.5rem .9rem;background:var(--panel);border-bottom:1px solid var(--edge)}}
h1{{font:600 .88rem/1.2 var(--mono);margin:0;letter-spacing:.02em}}
.prov{{font:.69rem/1.4 var(--mono);color:var(--muted);display:flex;gap:.85rem;flex-wrap:wrap}}
.prov b{{color:var(--ink);font-weight:600}}
.flag{{font:600 .63rem/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;
  color:var(--warn);border:1px solid var(--warn);border-radius:2px;padding:.24rem .4rem}}
#wrap{{position:relative;flex:1;min-height:0;cursor:grab;overflow:hidden}}
#wrap.drag{{cursor:grabbing}}
canvas{{position:absolute;inset:0;width:100%;height:100%;display:block}}
.overlay{{position:absolute;background:rgba(14,23,25,.88);border:1px solid var(--edge);
  border-radius:3px;font:.67rem/1.5 var(--mono);color:var(--muted);padding:.45rem .55rem;
  pointer-events:none}}
#key{{left:.7rem;bottom:.7rem}}
#key i{{display:inline-block;width:1.1rem;height:0;border-top-width:2px;
  border-top-style:solid;vertical-align:middle;margin-right:.4rem}}
#key span{{display:block}}
#scalebox{{right:.7rem;bottom:.7rem;text-align:center;color:var(--ink)}}
#bar{{height:3px;background:var(--ink);margin-top:.3rem;border-radius:1px}}
#lanetag{{right:.7rem;top:.7rem;color:var(--tram);border-color:var(--tram)}}
footer{{display:flex;align-items:center;gap:.85rem;padding:.45rem .9rem;
  background:var(--panel);border-top:1px solid var(--edge);flex-wrap:wrap}}
button{{font:600 .74rem/1 var(--mono);color:var(--ink);background:transparent;
  border:1px solid var(--edge);border-radius:3px;padding:.4rem .62rem;cursor:pointer}}
button:hover{{border-color:var(--muted)}}
button:focus-visible{{outline:2px solid var(--car);outline-offset:2px}}
button[aria-pressed="true"]{{border-color:var(--car);color:var(--car)}}
#clock{{font:600 1.08rem/1 var(--mono);font-variant-numeric:tabular-nums;min-width:4.8rem}}
#scrub{{flex:1;min-width:10rem;accent-color:var(--car)}}
.count{{font:.72rem/1.3 var(--mono);font-variant-numeric:tabular-nums;color:var(--muted);
  display:flex;align-items:center;gap:.35rem}}
.count b{{color:var(--ink);font-weight:600;min-width:3.4rem;display:inline-block;text-align:right}}
.dot{{width:.5rem;height:.5rem;border-radius:50%;display:inline-block}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>
<header>
  <h1>{title}</h1>
  <div class="prov">
    <span>run <b>{run}</b></span><span>scenario <b>{scenario}</b></span>
    <span>day <b>{day}</b></span><span>sample <b>{frac}</b></span>
    <span>iter <b>{iters}</b></span><span>drawn <b>{drawn}</b>/{seen} vehicles</span>
  </div>
  <span class="flag">Diagnostic &mdash; not a result</span>
</header>
<div id="wrap">
  <canvas id="c"></canvas>
  <div class="overlay" id="key">
    <span><i style="border-color:var(--rd1)"></i>motorway &amp; trunk</span>
    <span><i style="border-color:var(--rd3)"></i>primary &amp; secondary</span>
    <span><i style="border-color:var(--rd5)"></i>local streets</span>
    <span><i style="border-color:var(--rail)"></i>heavy rail</span>
    <span><i style="border-color:var(--tram)"></i>light rail</span>
    <span><i style="border-color:var(--water);border-top-width:6px"></i>water</span>
  </div>
  <div class="overlay" id="lanetag" hidden>lane geometry &middot; SUMO corridor</div>
  <div class="overlay" id="scalebox"><span id="scaletxt">&mdash;</span><div id="bar"></div></div>
</div>
<footer>
  <button id="play">Pause</button>
  <span id="clock">00:00</span>
  <input id="scrub" type="range" min="0" max="0" value="0" step="1" aria-label="Time of day">
  <button id="speed">1&times;</button>
  <button id="trails" aria-pressed="true">Trails</button>
  <button id="zin">Zoom +</button><button id="zout">&minus;</button>
  <button id="reset">Reset</button>
  <span class="count"><span class="dot" style="background:var(--car)"></span>on road <b id="nc">0</b></span>
  <span class="count"><span class="dot" style="background:var(--transit)"></span>transit <b id="nt">0</b></span>
</footer>
<script id="base" type="application/json">{basemap}</script>
<script id="payload" type="application/json">{payload}</script>
<script>
const B = JSON.parse(document.getElementById('base').textContent);
const D = JSON.parse(document.getElementById('payload').textContent);
const STEP = D.meta.step_s, NF = D.meta.frames;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const bg = document.createElement('canvas'), tr = document.createElement('canvas');
let W = 0, H = 0, dpr = 1;

function bytes(s){{
  const bin = atob(s), n = bin.length, u = new Uint8Array(n);
  for (let i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
  return u;
}}
// basemap: anchored int32-cm runs with int16-cm deltas, decoded once to metres
const LAYERS = {{}}, PATHS = {{}};
let LANEW = new Map();
for (const k in B.layers) {{
  const u = bytes(B.layers[k]), dv = new DataView(u.buffer);
  const runs = []; let i = 0;
  while (i + 12 <= u.length) {{
    const x0 = dv.getInt32(i, true), y0 = dv.getInt32(i + 4, true);
    const n = dv.getUint16(i + 8, true), meta = dv.getUint8(i + 10);
    i += 12;
    if (n < 2 || i + (n - 1) * 4 > u.length) break;
    const xs = new Float32Array(n), ys = new Float32Array(n);
    let px = x0, py = y0; xs[0] = px / 100; ys[0] = py / 100;
    for (let j = 1; j < n; j++) {{
      px += dv.getInt16(i, true); py += dv.getInt16(i + 2, true); i += 4;
      xs[j] = px / 100; ys[j] = py / 100;
    }}
    runs.push({{xs: xs, ys: ys, meta: meta}});
  }}
  LAYERS[k] = runs;
  // One Path2D per layer, built ONCE in world metres. Every draw then strokes
  // that same object under a canvas transform, so panning and zooming cost a
  // handful of stroke calls instead of half a million lineTo calls in JS.
  const p = new Path2D();
  const byW = new Map();
  for (const r of runs) {{
    let t = p;
    if (k === 'lanes') {{
      if (!byW.has(r.meta)) byW.set(r.meta, new Path2D());
      t = byW.get(r.meta);
    }}
    t.moveTo(r.xs[0], r.ys[0]);
    for (let j = 1; j < r.xs.length; j++) t.lineTo(r.xs[j], r.ys[j]);
    if (k === 'coast' || k === 'water' || k === 'green' || k === 'sand') t.closePath();
  }}
  PATHS[k] = p;
  if (k === 'lanes') LANEW = byW;
}}
function frame(s){{
  const u = bytes(s), dv = new DataView(u.buffer), n = u.length >> 3;
  const out = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {{
    out[i * 2] = dv.getInt32(i * 8, true) / 100;
    out[i * 2 + 1] = dv.getInt32(i * 8 + 4, true) / 100;
  }}
  return out;
}}
const FR = D.road.map(frame), FT = D.transit.map(frame);

// metres of carriageway per class: what the road actually is, not a line weight
const ORDER = [
  ['residential', '--rd5',  7.0, 0.55, 0],
  ['tertiary',    '--rd4',  8.5, 0.80, 0],
  ['secondary',   '--rd3', 10.5, 1.05, 0],
  ['primary',     '--rd2', 13.0, 1.35, 0],
  ['trunk',       '--rd1', 16.0, 1.70, 1],
  ['motorway',    '--rd1', 22.0, 2.20, 1],
  ['rail',        '--rail', 4.0, 1.00, 0],
  ['tram',        '--tram', 6.0, 2.20, 1],
];
const AREAS = [['coast', '--land'], ['green', '--green'],
               ['sand', '--sand'], ['water', '--water']];

// view state, in metres
const EX = B.bbox[2] - B.bbox[0], EY = B.bbox[3] - B.bbox[1];
let cx = EX / 2, cy = EY / 2, mpp = 1, mpp0 = 1;
const MPP_MIN = 0.01;                      // ~10 m across a 1000 px viewport

let COL = {{}};
function refreshPalette(){{
  const cs = getComputedStyle(document.documentElement);
  for (const v of ['--water','--land','--green','--sand','--casing','--tarmac',
                   '--marking','--rd5','--rd4','--rd3','--rd2','--rd1','--rail',
                   '--tram','--coast','--car','--transit'])
    COL[v] = cs.getPropertyValue(v).trim();
}}
const css = v => COL[v];
function fit(){{
  const r = cv.parentElement.getBoundingClientRect();
  dpr = Math.min(devicePixelRatio || 1, 2);
  W = Math.max(1, Math.round(r.width * dpr)); H = Math.max(1, Math.round(r.height * dpr));
  for (const k of [cv, bg, tr]) {{ k.width = W; k.height = H; }}
  mpp0 = Math.max(EX / (W / dpr), EY / (H / dpr));
}}
const S = () => dpr / mpp;                 // device pixels per metre
const PX = x => (x - cx) * S() + W / 2;
const PY = y => H / 2 - (y - cy) * S();

function path(g, runs){{
  let any = false;
  g.beginPath();
  for (const r of runs) {{
    any = true;
    for (let j = 0; j < r.xs.length; j++) {{
      const x = PX(r.xs[j]), y = PY(r.ys[j]);
      if (j) g.lineTo(x, y); else g.moveTo(x, y);
    }}
  }}
  return any;
}}
function fillArea(g, key, col){{
  const runs = LAYERS[key]; if (!runs) return;
  g.fillStyle = css(col); g.beginPath();
  for (const r of runs) {{
    for (let j = 0; j < r.xs.length; j++) {{
      const x = PX(r.xs[j]), y = PY(r.ys[j]);
      if (j) g.lineTo(x, y); else g.moveTo(x, y);
    }}
    g.closePath();
  }}
  g.fill('evenodd');
}}
const laneZoom = () => mpp < 0.55 && LAYERS['lanes'] && LAYERS['lanes'].length;

function paintBase(){{
  const g = bg.getContext('2d');
  const sx = S();
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = css('--water'); g.fillRect(0, 0, W, H);
  // world metres -> device pixels, for everything below
  g.setTransform(sx, 0, 0, -sx, W / 2 - cx * sx, H / 2 + cy * sx);
  g.lineJoin = 'round'; g.lineCap = 'round'; g.setLineDash([]);
  const wpx = 1 / sx;                       // one device pixel, in metres

  for (const [k, col] of AREAS) {{
    if (!PATHS[k]) continue;
    g.fillStyle = css(col); g.fill(PATHS[k], 'evenodd');
  }}
  if (PATHS['coast']) {{
    g.strokeStyle = css('--coast'); g.lineWidth = 0.8 * dpr * wpx;
    g.stroke(PATHS['coast']);
  }}

  const lanes = laneZoom();
  for (const [key, col, metres, minPx, glow] of ORDER) {{
    if (!PATHS[key]) continue;
    if (key === 'residential' && mpp > 90) continue;
    const lw = Math.max(minPx * dpr * wpx, metres);
    if (key !== 'rail' && key !== 'tram') {{
      g.strokeStyle = css('--casing'); g.shadowBlur = 0;
      g.lineWidth = lw + 2.2 * dpr * wpx; g.stroke(PATHS[key]);
    }}
    g.strokeStyle = (lanes && key !== 'rail' && key !== 'tram')
      ? css('--tarmac') : css(col);
    if (glow && !lanes) {{ g.shadowColor = css(col); g.shadowBlur = 5 * dpr; }}
    else g.shadowBlur = 0;
    g.lineWidth = lw; g.stroke(PATHS[key]);
  }}
  g.shadowBlur = 0;

  if (lanes) {{
    // lanes bucketed by width, so this is a dozen strokes rather than 17,188
    g.strokeStyle = css('--tarmac');
    for (const [meta, pth] of LANEW) {{
      g.lineWidth = meta === 255 ? 3.0 : meta / 10;
      g.stroke(pth);
    }}
    if (mpp < 0.18 && PATHS['lanes']) {{
      g.strokeStyle = css('--marking'); g.lineWidth = Math.max(0.5 * wpx, 0.12);
      g.setLineDash([3, 4]); g.stroke(PATHS['lanes']); g.setLineDash([]);
    }}
  }}
  g.setTransform(1, 0, 0, 1, 0, 0);
  document.getElementById('lanetag').hidden = !lanes;
  scalebar();
}}

function scalebar(){{
  const want = mpp * 110;
  const pow = Math.pow(10, Math.floor(Math.log10(want)));
  const nice = [1, 2, 5, 10].map(k => k * pow).find(v => v >= want) || pow;
  document.getElementById('bar').style.width = (nice / mpp) + 'px';
  document.getElementById('scaletxt').textContent =
    nice >= 1000 ? (nice / 1000) + ' km' : nice + ' m';
}}

let f = 0, playing = true, speed = 1, useTrails = true, acc = 0, last = 0, dirty = true;

function draw(){{
  if (dirty) {{ paintBase(); tr.getContext('2d').clearRect(0, 0, W, H); dirty = false; }}
  const g = tr.getContext('2d');
  if (useTrails) {{
    g.globalCompositeOperation = 'destination-out';
    g.fillStyle = 'rgba(0,0,0,0.20)'; g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'source-over';
  }} else g.clearRect(0, 0, W, H);
  // a car is about 4.4 m long: a dot when far out, a vehicle when close in
  const rc = Math.max(1.1 * dpr, 4.4 * S());
  const rt = Math.max(2.2 * dpr, 18.0 * S());
  const road = FR[f] || new Float32Array(0), tran = FT[f] || new Float32Array(0);
  // world-space viewport, so offscreen vehicles cost one compare each
  const sx = S(), hx = (W / 2 + 30) / sx, hy = (H / 2 + 30) / sx;
  const x0 = cx - hx, x1 = cx + hx, y0 = cy - hy, y1 = cy + hy;
  g.fillStyle = css('--car');
  for (let i = 0; i + 1 < road.length; i += 2) {{
    const wx = road[i], wy = road[i + 1];
    if (wx < x0 || wx > x1 || wy < y0 || wy > y1) continue;
    g.fillRect(PX(wx) - rc / 2, PY(wy) - rc / 2, rc, rc);
  }}
  g.fillStyle = css('--transit');
  for (let i = 0; i + 1 < tran.length; i += 2) {{
    const wx = tran[i], wy = tran[i + 1];
    if (wx < x0 || wx > x1 || wy < y0 || wy > y1) continue;
    g.beginPath(); g.arc(PX(wx), PY(wy), rt / 2, 0, 6.284); g.fill();
  }}
  ctx.drawImage(bg, 0, 0); ctx.drawImage(tr, 0, 0);
  const t = f * STEP;
  document.getElementById('clock').textContent =
    String(Math.floor(t / 3600)).padStart(2, '0') + ':' +
    String(Math.floor(t / 60) % 60).padStart(2, '0');
  document.getElementById('nc').textContent = (road.length >> 1).toLocaleString();
  document.getElementById('nt').textContent = (tran.length >> 1).toLocaleString();
  document.getElementById('scrub').value = f;
}}
function tick(ts){{
  if (!last) last = ts;
  const dt = ts - last; last = ts;
  if (playing) {{ acc += dt * speed; while (acc > 70) {{ acc -= 70; f = (f + 1) % NF; }} }}
  draw(); requestAnimationFrame(tick);
}}

function zoomAt(sx, sy, k){{
  const m2 = Math.min(mpp0, Math.max(MPP_MIN, mpp * k));
  // hold the world point under the cursor still
  const wx = cx + (sx - W / 2) * mpp / dpr, wy = cy - (sy - H / 2) * mpp / dpr;
  cx = wx - (sx - W / 2) * m2 / dpr; cy = wy + (sy - H / 2) * m2 / dpr;
  mpp = m2; dirty = true;
}}
const wrap = document.getElementById('wrap');
wrap.addEventListener('wheel', e => {{
  e.preventDefault();
  const r = wrap.getBoundingClientRect();
  zoomAt((e.clientX - r.left) * dpr, (e.clientY - r.top) * dpr,
         Math.exp(e.deltaY * 0.0016));
}}, {{passive: false}});
let down = null;
wrap.addEventListener('pointerdown', e => {{
  down = {{x: e.clientX, y: e.clientY, cx: cx, cy: cy}};
  wrap.classList.add('drag'); wrap.setPointerCapture(e.pointerId);
}});
wrap.addEventListener('pointermove', e => {{
  if (!down) return;
  cx = down.cx - (e.clientX - down.x) * mpp;
  cy = down.cy + (e.clientY - down.y) * mpp; dirty = true;
}});
wrap.addEventListener('pointerup', () => {{ down = null; wrap.classList.remove('drag'); }});

document.getElementById('scrub').max = Math.max(0, NF - 1);
document.getElementById('play').onclick = e => {{
  playing = !playing; e.target.textContent = playing ? 'Pause' : 'Play';
}};
document.getElementById('scrub').oninput = e => {{ f = +e.target.value; dirty = true; }};
document.getElementById('speed').onclick = e => {{
  speed = speed >= 8 ? 1 : speed * 2; e.target.innerHTML = speed + '&times;';
}};
document.getElementById('trails').onclick = e => {{
  useTrails = !useTrails; e.target.setAttribute('aria-pressed', useTrails); dirty = true;
}};
document.getElementById('zin').onclick = () => zoomAt(W / 2, H / 2, 0.5);
document.getElementById('zout').onclick = () => zoomAt(W / 2, H / 2, 2);
document.getElementById('reset').onclick = () => {{
  mpp = mpp0; cx = EX / 2; cy = EY / 2; dirty = true;
}};
addEventListener('resize', () => {{ fit(); mpp = Math.min(mpp, mpp0); dirty = true; }});
refreshPalette(); fit(); mpp = mpp0; requestAnimationFrame(tick);
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('payload')
    ap.add_argument('--basemap', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default=None)
    a = ap.parse_args()

    d = json.load(open(a.payload, encoding='utf-8'))
    b = json.load(open(a.basemap, encoding='utf-8'))
    m = d['meta']
    # both payloads must be anchored on the same origin, or the vehicles sit
    # somewhere other than the roads
    if m.get('origin') and b.get('origin'):
        assert abs(m['origin'][0] - b['origin'][0]) < 1e-6 and \
               abs(m['origin'][1] - b['origin'][1]) < 1e-6, \
               'replay and basemap were built against different origins'
    # the renderer works in metres from the origin, so shift the bbox onto it
    b = dict(b, bbox=[0.0, 0.0, b['bbox'][2] - b['bbox'][0],
                      b['bbox'][3] - b['bbox'][1]])
    frac = m.get('sample_fraction')
    html = PAGE.format(
        title=a.title or ('Newcastle microsimulation — %s' % m.get('run', 'run')),
        run=m.get('run', '?'), scenario=m.get('scenario') or '?',
        day=m.get('day') or '?',
        frac=('%g%%' % (frac * 100)) if isinstance(frac, (int, float)) else '?',
        iters=m.get('iterations') if m.get('iterations') is not None else '?',
        drawn='{:,}'.format(m.get('vehicles_drawn', 0)),
        seen='{:,}'.format(m.get('vehicles_seen', 0)),
        basemap=json.dumps(b, separators=(',', ':')),
        payload=json.dumps(d, separators=(',', ':')))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as w:
        w.write(html)
    print('wrote %s  (%.1f MiB)' % (a.out, os.path.getsize(a.out) / 2**20))


if __name__ == '__main__':
    main()
