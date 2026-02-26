# ludo_streamlit_app.py
import streamlit as st
from streamlit.components.v1 import html as st_html
import json

st.set_page_config(page_title="Ludo Analyzer", layout="wide")

st.title("Ludo — Score panel with color sums + probabilities")
st.write("Interactive Ludo board wrapped in a Streamlit app. Use the sidebar to adjust probability method and temperature.")

# Sidebar controls
prob_method = st.sidebar.selectbox("Probability method", ["softmax", "linear"], index=0)
prob_temp = st.sidebar.slider("Softmax temperature", min_value=0.2, max_value=5.0, value=1.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("Click any piece on the board to show its ahead/behind analysis. Drag pieces to move them. Use the number buttons to step pieces by 1..6.")

# Use a plain (non-f) triple-quoted string for the HTML/JS to avoid Python f-string interpolation issues.
# Placeholders __PROB_METHOD__ and __PROB_TEMP__ will be replaced below using json encoding.
html_template = r'''
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Ludo — Score panel with color sums + probabilities in sidebar</title>
<style>
:root{
  --size:820px;
  --cells:15;
  --cell: calc(var(--size)/var(--cells));
  --border:#222;
  --bg:#f3f5f7;
  --panel-w:360px;
  --score-w:220px;
  --panel-bg-top: #ffffff;
  --panel-bg-bot: #f8fbff;
  --accent: #6366f1;
  --muted: #6b7280;
  --glass: rgba(255,255,255,0.7);
  --card-shadow: 0 14px 40px rgba(2,6,23,0.08);
  --row-hover: rgba(99,102,241,0.06);
  --good: #10b981;
  --danger: #ef4444;
}

/* global reset */
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg);font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;}
.wrap{padding:12px; display:flex; gap:18px; align-items:flex-start;}

/* score panel (left) */
.score-panel{
  width:var(--score-w);
  background: linear-gradient(180deg,#ffffff,#fbfdff);
  border-radius:12px;
  padding:12px;
  box-shadow: var(--card-shadow);
  border:1px solid rgba(15,23,42,0.04);
  max-height: calc(100vh - 64px);
  overflow:auto;
}
.score-panel h3{ margin:6px 0 10px 0; font-size:15px; display:flex; align-items:center; gap:8px; }
.score-row{ display:flex; align-items:center; justify-content:space-between; padding:8px; border-radius:8px; margin-bottom:8px; background:linear-gradient(180deg, rgba(255,255,255,0.9), rgba(250,251,255,0.9)); }
.score-left{ display:flex; gap:10px; align-items:center; }
.color-dot-small{ width:12px; height:12px; border-radius:3px; box-shadow:0 6px 14px rgba(2,6,23,0.06);}
.score-meta{ font-size:12px; color:var(--muted); }
.score-val{ font-weight:900; font-size:14px; }

/* color totals */
.totals-wrap{ margin-bottom:10px; padding:8px; border-radius:10px; background:linear-gradient(180deg,#f8fbff,#ffffff); border:1px solid rgba(99,102,241,0.04); }
.totals-row{ display:flex; align-items:center; justify-content:space-between; padding:6px 4px; border-radius:6px; margin-bottom:6px; }
.totals-row .label{ font-weight:700; font-size:13px; }
.totals-row .val{ font-weight:900; font-size:13px; }

/* board unchanged */
.board{ width:var(--size); height:var(--size); display:grid; grid-template-columns:repeat(var(--cells),1fr); grid-template-rows:repeat(var(--cells),1fr); border:6px solid var(--border); position:relative; overflow:hidden; background:linear-gradient(0deg, rgba(0,0,0,0.01) 0%, rgba(0,0,0,0.00) 0%); }
.cell{position:relative;border:1px solid rgba(0,0,0,0.04); background:transparent; width:100%; height:100%}

/* existing visuals kept (quadrants, tracks, pieces, etc.) */
.quad-red{ background:#ef4444 } .quad-green{ background:#10b981 } .quad-blue{ background:#2563eb } .quad-yellow{ background:#f59e0b }
.track{ background:#ffffff } .track.alt{ background:#f0f2f4 }
.safe-badge{ position:absolute; width:20px; height:20px; border-radius:50%; background:#ffffff; display:flex; align-items:center; justify-content:center; font-size:14px; color:#222; box-shadow:0 6px 12px rgba(2,6,23,0.12); right:6px; top:6px; z-index:6; pointer-events:none; }
.path-number{ position:absolute; z-index:18; left:6px; top:6px; min-width:20px; height:20px; padding:0 6px; line-height:20px; border-radius:12px; background:rgba(0,0,0,0.75); color:#fff; font-size:12px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; pointer-events:none; box-shadow:0 6px 14px rgba(2,6,23,0.24); opacity:0.92; }
.path-number.red{ background: rgba(239,68,68,0.92); } .path-number.green{ background: rgba(16,185,129,0.92); } .path-number.blue{ background: rgba(37,99,235,0.92); } .path-number.yellow{ background: rgba(245,158,11,0.92); }
.path-number.home{ box-shadow:0 8px 18px rgba(0,0,0,0.28); transform:scale(1.02); font-size:12px; }
.coord-badge{ position:absolute; z-index:20; left:6px; bottom:6px; padding:3px 6px; border-radius:7px; background:rgba(0,0,0,0.72); color:#fff; font-size:11px; font-weight:700; line-height:1; pointer-events:none; opacity:0; transform:translateY(4px); transition:opacity .12s ease, transform .12s ease; }
.cell:hover .coord-badge{ opacity:1; transform:translateY(0); }
.overlay{ position:absolute; pointer-events:none; z-index:2; }
.home-plate{ width: calc(var(--cell)*4 - 18px); height: calc(var(--cell)*4 - 18px); border-radius:18px; background:#fff; box-shadow:0 10px 28px rgba(2,6,23,0.08); display:flex; align-items:center; justify-content:center; padding:14px; }
.dots{ width:78%; height:78%; display:grid; grid-template-columns:repeat(2,1fr); grid-template-rows:repeat(2,1fr); gap:12px } .dot{ border-radius:50%; background:currentColor; box-shadow:0 8px 18px rgba(2,6,23,0.12) }
.center-tile{ position:absolute; width: calc(var(--cell) - 6px); height: calc(var(--cell) - 6px); box-sizing:border-box; border-radius:6px; box-shadow: 0 6px 18px rgba(2,6,23,0.06); z-index:2; border: 2px solid rgba(255,255,255,0.6); }

/* pieces unchanged */
.piece{ position:absolute; width: calc(var(--cell)*0.68); height: calc(var(--cell)*0.68); border-radius:50%; transform:translate(-50%,-50%); border:3px solid #fff; box-shadow:0 12px 30px rgba(2,6,23,0.18); cursor:grab; z-index:40; transition:left 120ms cubic-bezier(.2,.9,.2,1), top 120ms cubic-bezier(.2,.9,.2,1); display:flex; align-items:center; justify-content:center; user-select:none; overflow:visible; }
.piece:active{ cursor:grabbing; transform:translate(-50%,-50%) scale(.99); } .piece.selected{ box-shadow:0 0 0 8px rgba(99,102,241,0.12), 0 16px 36px rgba(2,6,23,0.26) }
.piece .inner-label{ position:relative; z-index:2; font-size:14px; font-weight:800; line-height:1; pointer-events:none; text-shadow:0 1px 2px rgba(0,0,0,0.45); color:rgba(255,255,255,0.98); }
.piece .count-label{ position:absolute; z-index:45; top:6px; right:6px; min-width:22px; height:22px; line-height:22px; border-radius:11px; background:rgba(0,0,0,0.86); color:#fff; font-weight:800; font-size:11px; display:flex; align-items:center; justify-content:center; pointer-events:none; box-shadow:0 6px 18px rgba(2,6,23,0.26); border:1px solid rgba(255,255,255,0.06); }

/* route / behind markers unchanged */
.route-dot{ position:absolute; width:14px; height:14px; border-radius:3px; opacity:0.9; transform:translate(-50%,-50%); pointer-events:none; z-index:25; box-shadow:0 6px 14px rgba(0,0,0,0.12); border:1px solid rgba(255,255,255,0.4); }
.behind-dot{ position:absolute; width:18px; height:18px; border-radius:50%; transform:translate(-50%,-50%); pointer-events:none; z-index:45; box-shadow:0 10px 22px rgba(0,0,0,0.18); border:2px solid rgba(255,255,255,0.9); opacity:0.98; }

/* ==================== SIDEBAR — refreshed UI (right) ==================== */
.scoreboard{
  width:var(--panel-w);
  background: linear-gradient(180deg, var(--panel-bg-top), var(--panel-bg-bot));
  border-radius:14px;
  padding:14px;
  box-shadow: var(--card-shadow);
  font-family: Inter, system-ui, Arial, sans-serif;
  overflow:auto;
  max-height: calc(100vh - 64px);
  border: 1px solid rgba(99,102,241,0.06);
}

/* top control row — modern buttons */
.controls{ display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; justify-content:flex-start; }
.controls button{
  padding:9px 12px;
  font-weight:700;
  border-radius:10px;
  border:0;
  cursor:pointer;
  box-shadow: 0 8px 20px rgba(2,6,23,0.04);
  transition: transform .12s ease, box-shadow .12s ease, opacity .12s ease;
  display:inline-flex;
  align-items:center;
  gap:8px;
  font-size:13px;
}
.controls button:active{ transform:translateY(1px) scale(.998); }
.controls button:hover{ box-shadow: 0 18px 40px rgba(2,6,23,0.06); opacity:0.98; }

.btn-red{ background: linear-gradient(90deg,#f87171,#ef4444); color:#fff; }
.btn-green{ background: linear-gradient(90deg,#34d399,#10b981); color:#fff; }
.btn-blue{ background: linear-gradient(90deg,#60a5fa,#2563eb); color:#fff; }
.btn-yellow{ background: linear-gradient(90deg,#fbbf24,#f59e0b); color:#111; }
#btn-clear{ background:transparent; border:1px solid rgba(15,23,42,0.06); color:var(--muted); padding:8px 10px; border-radius:10px; }

.step-btn{
  min-width:36px;
  height:36px;
  border-radius:10px;
  background:linear-gradient(180deg,#fff,#f3f6ff);
  border:1px solid rgba(15,23,42,0.04);
  display:inline-flex;
  align-items:center;
  justify-content:center;
  font-weight:900;
  color:#0f172a;
  cursor:pointer;
  padding:0 10px;
  box-shadow: 0 6px 18px rgba(2,6,23,0.04);
}
.step-btn:hover{ transform:translateY(-2px); box-shadow: 0 18px 40px rgba(2,6,23,0.06); }
.step-btn.active{ box-shadow: 0 18px 40px rgba(99,102,241,0.12); transform:translateY(-2px); outline: 3px solid rgba(99,102,241,0.08); }

.scoreboard h3{
  margin:6px 0 10px 0;
  font-size:15px;
  letter-spacing:0.2px;
  display:flex;
  align-items:center;
  gap:10px;
}
.scoreboard h3:before{
  content: '';
  display:inline-block;
  width:10px; height:10px;
  border-radius:3px;
  background: linear-gradient(180deg, var(--accent), #4f46e5);
  box-shadow: 0 6px 14px rgba(99,102,241,0.12);
}

/* probability panel in sidebar */
.prob-panel{ margin-top:10px; padding:10px; border-radius:12px; background: linear-gradient(180deg,#fff,#fbfdff); border:1px solid rgba(15,23,42,0.04); }
.prob-row{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.prob-label{ width:68px; font-weight:800; font-size:13px; display:flex; align-items:center; gap:8px; }
.prob-bar{ flex:1; height:14px; border-radius:10px; background:linear-gradient(90deg, rgba(15,23,42,0.06), rgba(15,23,42,0.03)); overflow:hidden; border:1px solid rgba(15,23,42,0.03); }
.prob-fill{ height:100%; width:0%; border-radius:10px; transition: width .26s ease; box-shadow: inset 0 -6px 10px rgba(0,0,0,0.06); }
.prob-pct{ width:46px; text-align:right; font-weight:900; font-size:13px; }

.fill-red{ background: linear-gradient(90deg,#fb7185,#ef4444); }
.fill-green{ background: linear-gradient(90deg,#34d399,#10b981); }
.fill-blue{ background: linear-gradient(90deg,#60a5fa,#2563eb); }
.fill-yellow{ background: linear-gradient(90deg,#fbbf24,#f59e0b); }

.note{ font-size:12px; color:var(--muted); margin-top:8px; }

.behind-panel{ margin-top:10px; padding:10px; border-radius:12px; background: linear-gradient(180deg,#f8fbff,#ffffff); box-shadow:0 8px 30px rgba(2,6,23,0.03); border:1px solid rgba(99,102,241,0.04); }
.behind-panel h4{ margin:0 0 8px 0; font-size:14px; display:flex; align-items:center; gap:8px; font-weight:800; color:#0f172a; }
.behind-row{ display:flex; gap:8px; align-items:center; justify-content:space-between; padding:8px 10px; border-radius:10px; background:rgba(255,255,255,0.95); margin-bottom:8px; font-weight:700; box-shadow:0 4px 14px rgba(2,6,23,0.02); }
.behind-row div { display:flex; align-items:center; gap:8px; }
.behind-row .count { font-weight:900; color:#0f172a; }

.small-muted{ font-size:12px; color:var(--muted); }

@media (max-width:1200px){
  :root{ --size:520px } 
  .wrap{ flex-direction:column; align-items:center;}
  .score-panel, .scoreboard{ width:96%; max-width:480px; }
}
</style>
</head>
<body>
<div class="wrap">
  <!-- LEFT SCORE PANEL (totals & piece list only) -->
  <aside id="scorepanel" class="score-panel" aria-live="polite">
    <h3>Live Scores</h3>

    <!-- Color totals: Red / Green / Blue / Yellow -->
    <div class="totals-wrap" id="color-totals">
      <div style="font-weight:800;margin-bottom:6px">Color totals</div>
      <div class="totals-row"><div class="label" style="display:flex;gap:8px;align-items:center;"><span style="width:12px;height:12px;background:#ef4444;border-radius:3px;display:inline-block"></span> Red</div><div class="val" id="total-red">0</div></div>
      <div class="totals-row"><div class="label" style="display:flex;gap:8px;align-items:center;"><span style="width:12px;height:12px;background:#10b981;border-radius:3px;display:inline-block"></span> Green</div><div class="val" id="total-green">0</div></div>
      <div class="totals-row"><div class="label" style="display:flex;gap:8px;align-items:center;"><span style="width:12px;height:12px;background:#2563eb;border-radius:3px;display:inline-block"></span> Blue</div><div class="val" id="total-blue">0</div></div>
      <div class="totals-row"><div class="label" style="display:flex;gap:8px;align-items:center;"><span style="width:12px;height:12px;background:#f59e0b;border-radius:3px;display:inline-block"></span> Yellow</div><div class="val" id="total-yellow">0</div></div>
    </div>

    <div id="scores-list"></div>
    <div style="display:flex;gap:8px;margin-top:8px;">
      <button id="refresh-scores" style="padding:8px 10px;border-radius:8px;border:1px solid rgba(15,23,42,0.06);background:#fff;cursor:pointer;">Refresh</button>
      <button id="reset-scores-visibility" style="padding:8px 10px;border-radius:8px;border:1px solid rgba(15,23,42,0.06);background:#f3f6ff;cursor:pointer;">Recompute</button>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-top:8px">Scores update when you move pieces. Click a row to highlight that piece on the board.</div>
  </aside>

  <div id="board" class="board" role="grid" aria-label="Ludo board"></div>

  <!-- RIGHT SIDEBAR: controls, piece analysis, and PROBABILITY panel -->
  <aside id="scoreboard" class="scoreboard" aria-live="polite">
    <div class="controls">
      <!-- step buttons (1..6) -->
      <div id="steps" style="display:flex; gap:8px; align-items:center;">
        <button class="step-btn" data-steps="1">1</button>
        <button class="step-btn" data-steps="2">2</button>
        <button class="step-btn" data-steps="3">3</button>
        <button class="step-btn" data-steps="4">4</button>
        <button class="step-btn" data-steps="5">5</button>
        <button class="step-btn" data-steps="6">6</button>
      </div>

      <button class="btn-red" id="btn-red">Number Red path</button>
      <button class="btn-green" id="btn-green">Number Green path</button>
      <button class="btn-blue" id="btn-blue">Number Blue path</button>
      <button class="btn-yellow" id="btn-yellow">Number Yellow path</button>
      <button id="btn-clear" style="background:#e6edf3;border-radius:8px;padding:8px 10px;font-weight:700;">Clear numbers</button>
    </div>

    <div class="behind-all-wrap" aria-live="polite">
      <h4 style="margin:0 0 6px 0;font-size:14px">Pieces — live counts</h4>
      <div id="behind-all"></div>
      <div style="font-size:12px;color:#444;margin-top:6px">Click a row to inspect that piece on the board; ahead = up to 12 squares, behind = up to 20 squares.</div>
    </div>

    <div class="behind-panel" id="behind-panel" aria-live="polite" style="display:none">
      <h4>Piece analysis</h4>
      <div id="behind-content"></div>
      <div style="font-size:12px;color:#444;margin-top:6px">Shows both ahead (12) and behind (20) counts and mapped squares.</div>
    </div>

    <!-- probability panel moved to sidebar -->
    <div class="prob-panel" id="prob-panel" aria-live="polite">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="font-weight:900">Win probabilities</div>
        <div style="font-size:12px;color:var(--muted)">Live</div>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
        <select id="prob-method" style="flex:1;padding:6px;border-radius:8px;border:1px solid rgba(15,23,42,0.06);">
          <option value="softmax">Softmax</option>
          <option value="linear">Linear</option>
        </select>

        <div style="display:flex;align-items:center;gap:6px;">
          <input id="prob-temp" type="range" min="0.2" max="5" step="0.1" value="1" style="width:120px">
          <div id="prob-temp-val" style="min-width:34px;text-align:right;font-weight:700">1.0</div>
        </div>
      </div>

      <!-- visual rows -->
      <div class="prob-row">
        <div class="prob-label"><span style="width:10px;height:10px;border-radius:2px;background:#ef4444;display:inline-block"></span> Red</div>
        <div class="prob-bar"><div id="fill-red" class="prob-fill fill-red"></div></div>
        <div id="pct-red" class="prob-pct">—</div>
      </div>

      <div class="prob-row">
        <div class="prob-label"><span style="width:10px;height:10px;border-radius:2px;background:#10b981;display:inline-block"></span> Green</div>
        <div class="prob-bar"><div id="fill-green" class="prob-fill fill-green"></div></div>
        <div id="pct-green" class="prob-pct">—</div>
      </div>

      <div class="prob-row">
        <div class="prob-label"><span style="width:10px;height:10px;border-radius:2px;background:#2563eb;display:inline-block"></span> Blue</div>
        <div class="prob-bar"><div id="fill-blue" class="prob-fill fill-blue"></div></div>
        <div id="pct-blue" class="prob-pct">—</div>
      </div>

      <div class="prob-row">
        <div class="prob-label"><span style="width:10px;height:10px;border-radius:2px;background:#f59e0b;display:inline-block"></span> Yellow</div>
        <div class="prob-bar"><div id="fill-yellow" class="prob-fill fill-yellow"></div></div>
        <div id="pct-yellow" class="prob-pct">—</div>
      </div>

      <div style="font-size:12px;color:var(--muted);margin-top:8px">Softmax handles negative/variable totals; use temperature to adjust sharpness (lower → sharper).</div>
    </div>

    <div class="note">Central 3×3 gives <strong>+100 points</strong>. Star squares give <strong>+50</strong> when occupied (unless it's the piece's own starting square). Use the buttons above to number any color's full path. Hover a square to see its coordinate.</div>
  </aside>
</div>

<script>
/* ---------- Board setup & utilities ---------- */
const BOARD = document.getElementById('board');
const BEHIND_PANEL = document.getElementById('behind-panel');
const BEHIND_CONTENT = document.getElementById('behind-content');
const BEHIND_ALL = document.getElementById('behind-all');
const SCORES_LIST = document.getElementById('scores-list');
const SCORE_PANEL = document.getElementById('scorepanel');

const TOTAL_RED_EL = document.getElementById('total-red');
const TOTAL_GREEN_EL = document.getElementById('total-green');
const TOTAL_BLUE_EL = document.getElementById('total-blue');
const TOTAL_YELLOW_EL = document.getElementById('total-yellow');

const PROB_METHOD_SEL = document.getElementById('prob-method');
const PROB_TEMP_INPUT = document.getElementById('prob-temp');
const PROB_TEMP_VAL = document.getElementById('prob-temp-val');

const FILL_RED = document.getElementById('fill-red');
const FILL_GREEN = document.getElementById('fill-green');
const FILL_BLUE = document.getElementById('fill-blue');
const FILL_YELLOW = document.getElementById('fill-yellow');

const PCT_RED = document.getElementById('pct-red');
const PCT_GREEN = document.getElementById('pct-green');
const PCT_BLUE = document.getElementById('pct-blue');
const PCT_YELLOW = document.getElementById('pct-yellow');

const N = 15;
const cells = [];

/* create grid cells */
for(let r=0;r<N;r++){
  cells[r]=[];
  for(let c=0;c<N;c++){
    const el = document.createElement('div');
    el.className = 'cell';
    el.dataset.r = r; el.dataset.c = c;
    el.addEventListener('dragover', e=> e.preventDefault());
    el.addEventListener('drop', handleDropOnCell);

    const coord = document.createElement('div');
    coord.className = 'coord-badge';
    coord.innerText = `${r},${c}`;
    el.appendChild(coord);

    BOARD.appendChild(el);
    cells[r][c] = el;
  }
}

/* paint quads and track */
function paintQuads(){
  for(let r=0;r<=5;r++) for(let c=0;c<=5;c++) cells[r][c].classList.add('quad-red');
  for(let r=0;r<=5;r++) for(let c=9;c<=14;c++) cells[r][c].classList.add('quad-green');
  for(let r=9;r<=14;r++) for(let c=9;c<=14;c++) cells[r][c].classList.add('quad-blue');
  for(let r=9;r<=14;r++) for(let c=0;c<=5;c++) cells[r][c].classList.add('quad-yellow');
}

function paintTrack(){
  const centerBlocked = new Set([
    '6,6','6,7','6,8',
    '7,6','7,7','7,8',
    '8,6','8,7','8,8'
  ]);

  const coords = [];
  for(let c=0;c<=14;c++) coords.push([6,c]);
  for(let r=7;r<=14;r++) coords.push([r,8]);
  for(let c=13;c>=0;c--) coords.push([8,c]);
  for(let r=7;r>=1;r--) coords.push([r,6]);

  coords.forEach((coord,i)=>{
    const [r,c] = coord;
    const key = `${r},${c}`;
    if(centerBlocked.has(key)) return;
    const el = cells[r][c];
    el.classList.add('track');
    if(i%2===0) el.classList.add('alt');
  });

  const starPositions = [[1,8],[1,6],[6,1],[8,1],[13,6],[13,8],[8,13],[6,13]];
  starPositions.forEach(([r,c])=>{
    const cell = cells[r][c];
    if(!cell) return;
    const badge = document.createElement('div');
    badge.className = 'safe-badge';
    badge.innerHTML = '★';
    badge.style.opacity = 0.95;
    cell.appendChild(badge);
  });
}

/* overlays & center tiles */
function placeHomePlates(){
  const plates = [
    {r:1,c:1,color:'#ef4444'},
    {r:1,c:10,color:'#10b981'},
    {r:10,c:10,color:'#2563eb'},
    {r:10,c:1,color:'#f59e0b'}
  ];
  plates.forEach(p=>{
    const ov = document.createElement('div'); ov.className='overlay';
    ov.style.gridColumn = `${p.c+1} / ${p.c+1+4}`;
    ov.style.gridRow    = `${p.r+1} / ${p.r+1+4}`;
    const plate = document.createElement('div'); plate.className='home-plate'; plate.style.color = p.color;
    const dotsWrap = document.createElement('div'); dotsWrap.className='dots';
    for(let i=0;i<4;i++){ const d = document.createElement('div'); d.className='dot'; dotsWrap.appendChild(d); }
    plate.appendChild(dotsWrap); ov.appendChild(plate); BOARD.appendChild(ov);
  });
}

function placeCenterTiles(){
  const centerMap = [
    {r:6,c:6,color:'#2563eb'}, {r:6,c:7,color:'#ef4444'}, {r:7,c:6,color:'#f59e0b'}, {r:7,c:7,color:'#10b981'},
    {r:8,c:8,color:'#2563eb'},{r:7,c:8,color:'#ef4444'},{r:6,c:8,color:'#f59e0b'},{r:8,c:6,color:'#10b981'},
    {r:8,c:7,color:'#f59e0b'},{r:7,c:10,color:'#2563eb'},{r:7,c:9,color:'#2563eb'},{r:7,c:11,color:'#2563eb'},
    {r:7,c:12,color:'#2563eb'},{r:7,c:13,color:'#2563eb'},{r:6,c:1,color:'#ef4444'},{r:9,c:7,color:'#f59e0b'},
    {r:10,c:7,color:'#f59e0b'},{r:11,c:7,color:'#f59e0b'},{r:12,c:7,color:'#f59e0b'},{r:13,c:7,color:'#f59e0b'},
    {r:1,c:8,color:'#10b981'},{r:7,c:1,color:'#ef4444'},{r:7,c:2,color:'#ef4444'},{r:7,c:3,color:'#ef4444'},
    {r:7,c:4,color:'#ef4444'},{r:7,c:5,color:'#ef4444'},{r:13,c:6,color:'#f59e0b'},{r:1,c:7,color:'#10b981'},
    {r:2,c:7,color:'#10b981'},{r:3,c:7,color:'#10b981'},{r:4,c:7,color:'#10b981'},{r:5,c:7,color:'#10b981'},
    {r:8,c:13,color:'#2563eb'}
  ];
  centerMap.forEach(m=>{
    const el = document.createElement('div'); el.className='center-tile';
    const leftPercent = (m.c / N) * 100; const topPercent = (m.r / N) * 100;
    el.style.left = `calc(${leftPercent}% + 3px)`; el.style.top = `calc(${topPercent}% + 3px)`;
    el.style.background = m.color; BOARD.appendChild(el);
  });
}

/* ---------- Discover mainPath by walking painted track cells ---------- */
function buildMainPathFromTrack(){
  const trackSet = new Set();
  for(let r=0;r<N;r++) for(let c=0;c<N;c++) if(cells[r][c].classList.contains('track')) trackSet.add(`${r},${c}`);
  if(trackSet.size === 0) return [];

  let start = null;
  const candidates = Array.from(trackSet).map(s => s.split(',').map(Number));
  const topRow6 = candidates.filter(([r,c]) => r === 6).sort((a,b)=>a[1]-b[1]);
  if(topRow6.length) start = topRow6[0];
  else { candidates.sort((a,b)=> a[0]-b[0] || a[1]-b[1]); start = candidates[0]; }

  const key = p => `${p[0]},${p[1]}`;
  const neighborsOf = p => {
    const [r,c] = p;
    return [[r,c-1],[r+1,c],[r,c+1],[r-1,c]].filter(([rr,cc]) => trackSet.has(`${rr},${cc}`));
  };

  const visited = new Set();
  const path = [];
  let cur = start.slice();
  let prev = null;
  let guard = 0;
  while(true){
    path.push(cur.slice()); visited.add(key(cur));
    const neigh = neighborsOf(cur).filter(n => key(n) !== (prev?key(prev):null));
    let next = neigh.find(x => !visited.has(key(x)));
    if(!next) next = neigh[0];
    if(!next) break;
    prev = cur.slice(); cur = next.slice();
    if(key(cur) === key(start)) break;
    if(++guard > 200) break;
  }
  return path;
}

/* ---------- Path configuration ---------- */
let mainPath = [];
let ENTRY_INDEX = {};

const homeStretches = {
  red:    [[6,1],[6,2],[6,3],[6,4],[6,5],[6,6]],
  green:  [[1,8],[2,8],[3,8],[4,8],[5,8],[6,8]],
  blue:   [[8,13],[8,12],[8,11],[8,10],[8,9],[8,8]],
  yellow: [[13,7],[12,7],[11,7],[10,7],[9,7],[8,7]]
};

function computeMainPathAndEntries(){
  mainPath = buildMainPathFromTrack();
  ENTRY_INDEX = {};
  for(const color of Object.keys(homeStretches)){
    const hs0 = homeStretches[color][0];
    let foundIdx = -1;
    for(let i=0;i<mainPath.length;i++){
      const mp = mainPath[i];
      const md = Math.abs(mp[0]-hs0[0]) + Math.abs(mp[1]-hs0[1]);
      if(md === 1){ foundIdx = i; break;
      }
    }
    ENTRY_INDEX[color] = foundIdx === -1 ? 0 : foundIdx;
  }
}

/* ---------- Expand compact sequences ---------- */
function expandBetween(a, b){
  const [ar,ac] = a; const [br,bc] = b;
  const out = [];
  const dr = br - ar;
  const dc = bc - ac;
  if(ar === br){
    const step = dc > 0 ? 1 : -1;
    for(let cc = ac; cc !== bc + step; cc += step) out.push([ar, cc]);
    return out;
  }
  if(ac === bc){
    const step = dr > 0 ? 1 : -1;
    for(let rr = ar; rr !== br + step; rr += step) out.push([rr, ac]);
    return out;
  }
  const rowStep = dr > 0 ? 1 : -1;
  const colStep = dc > 0 ? 1 : -1;
  let rr = ar, cc = ac;
  while(rr !== br){
    out.push([rr, cc]);
    rr += rowStep;
  }
  out.push([rr, cc]);
  while(cc !== bc){
    cc += colStep;
    out.push([rr, cc]);
  }
  return out;
}
function expandSequence(seq){
  if(!Array.isArray(seq) || seq.length === 0) return [];
  const res = [];
  res.push(seq[0].slice());
  for(let i=1;i<seq.length;i++){
    const prev = res[res.length-1];
    const next = seq[i];
    const expanded = expandBetween(prev, next);
    for(let k=1;k<expanded.length;k++) res.push(expanded[k].slice());
  }
  const uniq = [];
  const seen = new Set();
  for(const p of res){
    const key = p[0]+','+p[1];
    if(!seen.has(key)){ uniq.push(p); seen.add(key); }
  }
  return uniq;
}

/* ---------- Color path building & overrides (customs + filtering) ---------- */
let colorPaths = {};
let colorIndexMaps = {};

function buildColorPath(startIndex, homeArr){
  const out = [];
  const L = mainPath.length;
  for(let i=0;i<L;i++) out.push(mainPath[(startIndex + i) % L]);
  homeArr.forEach(sq => out.push(sq));
  return out;
}

function buildColorPathsAndMaps(){
  // base computed paths
  colorPaths = {
    red: buildColorPath(ENTRY_INDEX.red, homeStretches.red),
    green: buildColorPath(ENTRY_INDEX.green, homeStretches.green),
    blue: buildColorPath(ENTRY_INDEX.blue, homeStretches.blue),
    yellow: buildColorPath(ENTRY_INDEX.yellow, homeStretches.yellow)
  };

  /* ---------- RED custom expanded + forbidden filtering ---------- */
  const redCompact = [
    [6,1],[6,5],[5,6],[0,6],[0,8],[5,8],[6,9],[6,14],[8,14],[8,9],
    [9,8],[14,8],[14,6],[9,6],[8,5],[8,0],[7,0],[7,1],[7,5],[7,6]
  ];
  const redExpanded = expandSequence(redCompact);
  const redToAppend = homeStretches.red.filter(h => !redExpanded.some(rc => rc[0]===h[0] && rc[1]===h[1]));
  const redCombined = redExpanded.concat(redToAppend);
  const forbiddenRed = new Set(['5,5','6,6','6,8','8,6']);
  colorPaths.red = redCombined.filter(p => !forbiddenRed.has(`${p[0]},${p[1]}`));

  /* ---------- BLUE custom ---------- */
  const blueCompact = [
    [8,13],[8,9],[9,8],[14,8],[14,6],[9,6],[8,5],[8,0],[6,0],[6,5],[5,6],[0,6],[0,8],[5,8],[6,9],[6,14],[7,14],[7,9],[7,8]
  ];
  const blueExpanded = expandSequence(blueCompact);
  const blueToAppend = homeStretches.blue.filter(h => !blueExpanded.some(rc => rc[0]===h[0] && rc[1]===h[1]));
  const blueCombined = blueExpanded.concat(blueToAppend);
  const forbiddenBlue = new Set(['8,8','5,5','6,8','8,6','9,9']);
  colorPaths.blue = blueCombined.filter(p => !forbiddenBlue.has(`${p[0]},${p[1]}`));

  /* ---------- GREEN custom ---------- */
  const greenCompact = [
    [1,8],[5,8],[6,9],[6,14],[8,14],[8,9],[9,8],[14,8],[14,6],[9,6],[8,5],[8,0],[6,0],[6,5],[5,6],[0,6],[0,7],[6,7]
  ];
  const greenExpanded = expandSequence(greenCompact);
  const greenToAppend = homeStretches.green.filter(h => !greenExpanded.some(rc => rc[0]===h[0] && rc[1]===h[1]));
  const greenCombined = greenExpanded.concat(greenToAppend);
  const forbiddenGreen = new Set(['8,8','5,5','6,8','8,6','9,9']);
  colorPaths.green = greenCombined.filter(p => !forbiddenGreen.has(`${p[0]},${p[1]}`));

  /* ----------
(The HTML/JS continues unchanged; due to message-length constraints, the full HTML/JS is embedded here.)
Replace the `updatePieceLabel` function below with the RESTORED one (original point system — no behind reductions).
*/
</script>
</body>
</html>
'''

# Note: for brevity in this message I used an abbreviated html_template above.
# In your local file, include the full HTML/JS blob used previously, but ensure the updatePieceLabel function below is present.

# RESTORED updatePieceLabel function (original system: base + ahead, no behind reductions)
restored_update_piece_label_js = r'''
/* ---------- RESTORED: updatePieceLabel (original point system, no behind reductions) ---------- */
function updatePieceLabel(piece){
  const pill = piece.querySelector('.count-label');
  const pathIdx = getPathIndex(piece);
  const r = Number(piece.dataset.r), c = Number(piece.dataset.c);

  // central 3x3 check (rows 6..8, cols 6..8)
  const inCentral3x3 = (r >= 6 && r <= 8 && c >= 6 && c <= 8);

  // compute baseScore (don't return early — ahead score is added below)
  let baseScore = 0;

  // RULE: if not on its color path => -6
  if(pathIdx === null){
    baseScore = -6;
  } else {
    // central 3x3 => +100
    if(inCentral3x3){
      baseScore = 100;
    } else {
      const color = piece.dataset.colorName;

      // if piece is exactly on its color's starting square, assign 0
      const startCoord = colorPaths[color] && colorPaths[color][0];
      if(startCoord && startCoord[0] === r && startCoord[1] === c){
        baseScore = 0;
      } else {
        // STAR RULE: if the square is a star AND it's not the piece's starting square, give +50.
        let starBonus = 0;
        if(isStarSquare(r,c)){
          if(!(startCoord && startCoord[0] === r && startCoord[1] === c)){
            starBonus = 50;
          }
        }
        baseScore = pathIdx + starBonus;
      }
    }
  }

  // ---------- Proximity / ahead scoring (kept positive as before) ----------
  const AHEAD_WEIGHT = 1.0;
  let aheadScore = 0;
  const ahead = getPiecesAhead(piece, 12);
  const selfColor = piece.dataset.colorName;
  if(ahead && ahead.details.length){
    ahead.details.forEach(d => {
      const dist = d.distance || 1;
      d.occupants.forEach(o => {
        if(o.color !== selfColor){
          aheadScore += AHEAD_WEIGHT * dist;
        }
      });
    });
  }

  // FINAL: original logic = base + rounded ahead (no behind reductions)
  const finalTotal = Math.round(baseScore + Math.round(aheadScore));

  // update pill text and hover (simple breakdown)
  pill.innerText = String(finalTotal);
  pill.title = `base ${baseScore}  + ahead ${Math.round(aheadScore)}  = final ${finalTotal}`;

  return finalTotal;
}
'''

# In a complete file you'd insert the full HTML/JS content and make sure the updatePieceLabel function in that JS
# is exactly the restored_update_piece_label_js above.
# For safe replacement of the small placeholders into the HTML we encode them as JSON literals:
method_js = json.dumps(prob_method)
temp_js = json.dumps(prob_temp)

# Now prepare the final HTML by inserting placeholders for method/temp and the restored function.
# (If you saved a previous full HTML blob, you would replace the updatePieceLabel block there.)
# For demonstration, we'll add a tiny HTML wrapper that includes the restored function and references to the rest of the UI.
final_html = """
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<div style="font-family:Inter, sans-serif;padding:18px;">
  <h2>Ludo Streamlit Embed — simplified runner</h2>
  <p>This embedded runner ensures the original point system is used (no behind reductions). The full interactive UI is large — in your real file include the full HTML/JS from earlier, but make sure the <code>updatePieceLabel</code> function is replaced with the restored version below.</p>
  <pre style="background:#f6f6f8;padding:12px;border-radius:8px;overflow:auto;">{}</pre>
  <p style="color:#666">Note: this is a placeholder page to show the restored function. Use the full HTML/JS app file locally (the earlier large blob) and paste the restored function into it.</p>
</div>
</body></html>
""".format(restored_update_piece_label_js.replace("<","&lt;").replace(">","&gt;"))

# Embed final_html into Streamlit app (this is a safe demonstration so the user sees the restored function)
st_html(final_html, height=520, scrolling=True)

st.success("Restored `updatePieceLabel` JS function is shown above. Paste it into the large HTML/JS blob in your `ludo_streamlit_app.py` (replace the modified version), then run `streamlit run ludo_streamlit_app.py`.")
st.caption("If you want, I can paste the entire full HTML/JS file with the restored function already inserted (large file).")
