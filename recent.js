'use strict';
// Compare page: projections of the saved states of every run, one run, two runs or a set of runs side by side.
// Time is the master state: every panel shows its own saved state nearest to the chosen time and prints that time.
(() => {
  const KEY = '20261125';
  const $ = id => document.getElementById(id);
  const canvas = $('scene'), ctx = canvas.getContext('2d');
  const CODE_ORDER = ['Athena++', 'AthenaPK', 'Athena 4.2', 'Enzo', 'Enzo-E', 'RAMSES', 'FLASH 4.8', 'Flash-X', 'Arepo', 'GIZMO MFM', 'GIZMO MFV', 'GADGET-4'];
  const VIEW_NAME = { edge: 'Edge on', face: 'Face on', both: 'Edge on and face on' };
  const VIEW_FILE = { edge: 'edge', face: 'face', both: 'edge-and-face' };
  const SHEET = { edge: [256, 128], face: [128, 128] }; // the standard map sizes; pictures of other boxes are fitted inside
  const TICKS = [0.008, 0.05, 0.2, 1, 5];
  const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  const OLD_LINK_STEP = 0.5;   // links written before 2026-11-22 carry ?frame=N with states 0.5 t_cc apart
  const COMPACT_BELOW = 860; // picture width in CSS px under which names and colour bar move into the page text
  // On screen the picture is drawn at its shown size, with the text at a fixed size in CSS px: the 1920 x 1080 layout is
  // laid out in units of 1/1.5 CSS px, so its 20 px footer shows at 13 px and its 24 px axis labels at 16 px whatever the window.
  // Save picture and Record video keep the 1920 x 1080 frame.
  const SCREEN_UNITS = 1.5;
  const MIN_SCREEN_W = 1280;   // in a short window the layout keeps at least this width in picture units, so the maps keep their room
  const STAMP_PX = 16;        // the time drawn over the maps on narrow screens, in CSS px
  const MAX_BACKING = 3840;    // widest canvas backing store, in device pixels
  const MAGMA = [[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 253, 191]];

  let catalog = null, runs = [], has3D = null;
  const byId = new Map();
  // view: the runs mode view (edge or face); gview: the side by side view (edge, face or both); set: which runs stand side by side;
  // level: the level chosen for the sets that have runs at several levels
  const S = { mode: 'runs', view: 'edge', gview: 'edge', set: 'twelve', t: 0, level: 5, current: null, comparison: null, playing: false, recording: false, dragging: false,
    compact: false, smooth: true, labels: true, speedKey: '', raf: 0, last: 0, urlTimer: 0, tiles: [], stacked: false, timeHTML: '', observer: null };

  // ------------------------------------------------------------------- run groups
// shared run groups 20261125 begin: keep identical in studio.js, recent.js and viewer.html
const RUN_GROUPS = [
  { key: 'twelve', title: 'Twelve methods',
    about: 'The same cloud and wind run with eight grid codes (Athena++, AthenaPK, Athena 4.2, Enzo, Enzo-E, RAMSES, FLASH 4.8, Flash-X) with an inflowing wind, the moving mesh code Arepo in a box periodic along the wind, and the particle methods GIZMO MFM, GIZMO MFV and GADGET-4 in a box periodic on all faces.' },
  { key: 'boundary', title: 'Boundary control',
    about: 'Athena++ with only the box faces changed. The 20 R boxes repeat the boxes of the moving mesh and particle runs: periodic along the wind, as for Arepo, and periodic on all faces, as for GIZMO and GADGET-4. The 100 R boxes are the same two boxes made 100 cloud radii long instead of 20.' },
  { key: 'solver', title: 'Solver settings',
    about: 'One change to the numerical method of one code, each next to the standard run of that code at the same level.' },
  { key: 'smooth', title: 'Smooth velocity profile',
    about: 'Runs started with the earlier smooth velocity profile at the cloud edge instead of the sharp edge at 1.3 cloud radii, each next to its sharp edge run.' },
  { key: 'contrast', title: 'Density contrast 10 and 1000',
    about: 'Clouds 10 and 1000 times denser than the wind, otherwise the setup of the twelve methods.' },
  { key: 'apk', title: 'AthenaPK cooling and solver tests',
    about: 'AthenaPK with tabulated radiative cooling switched on and off, and with different Riemann solvers and reconstructions.' },
  { key: 'level6', title: 'Level 6',
    about: 'Level 6 is 512 × 256 × 256 cells, 25.6 cells per cloud radius.' },
];
const runKey = r => String(r.run || r.projection_id || r.id || '').replace(/^new_/, '');
const runCode = r => String(r.code || String(r.label || '').split(' · ')[0]).replace(/\s*χ\s*[\d.]+\s*$/, '');
const runLevel = r => Number.isInteger(r.level) ? r.level : Number.isInteger(r.lvl) ? r.lvl : 5;
function runGroup(r) {
  if (RUN_GROUPS.some(g => g.key === r.group)) return r.group;
  const key = runKey(r), text = key + ' ' + String(r.label || '');
  if (runLevel(r) === 6) return 'level6';
  if (/historical|smooth velocity|tanh/i.test(text)) return 'smooth';
  if (/periodic|(^|[-_])(p3|px)(long)?([-_]|$)/i.test(text)) return 'boundary';
  if (/^apk/i.test(key) && /cooling|HLLE|HLLC/i.test(text)) return 'apk';
  if (/ppm|hllc/i.test(text)) return 'solver';
  if (/-track-l\d+$/i.test(key) || /box moving with the cloud/i.test(text)) return 'other';   // moving box runs stay together
  if (Number(r.chi) === 10 || Number(r.chi) === 1000) return 'contrast';
  if (Number(r.chi) === 100 && !runVariant(r)) return 'twelve';
  return 'other';                                   // listed last under "Other complete runs"
}
// 100 R long boxes: the "box" field, or "long" as a word or id part ("along the wind" does not count), or "100 R"
const runBox = r => (Number(r.box) === 100 || /(^|[-_ ])(p3|px)?long\b|100 ?R\b/i.test(runKey(r) + ' ' + String(r.label || ''))) ? 100 : 20;
// what this run changes, from the "variant" field or from the label words after code, χ and level
function runVariant(r) {
  if (r.variant) return String(r.variant);
  return String(r.label || '').split(' · ').slice(1).map(s => s.trim())
    .filter(s => s && !/^(χ|chi)\s*[\d.]+$/i.test(s) && !/^(level|n)\s*\d+$/i.test(s)).join(', ');
}
function runName(r) {           // name inside a group table: the code, then what the run changes
  let v = runVariant(r);
  if (runGroup(r) === 'smooth') v = v.replace(/,?\s*smooth velocity profile/i, '').replace(/^,\s*/, '');
  return v ? runCode(r) + ', ' + v : runCode(r);
}
const runMeta = r => `χ ${r.chi}, level ${runLevel(r)}`;
const runFaces = r => String(r.boundary || '') + (runBox(r) === 100 ? ', 100 R long box' : '');
// the standard run this one is compared with, or null
function runTwin(r, all) {
  const g = runGroup(r);
  if (!['boundary', 'solver', 'smooth', 'level6'].includes(g)) return null;
  const level = g === 'level6' ? 5 : runLevel(r);
  const same = x => x !== r && runCode(x) === runCode(r) && Number(x.chi) === Number(r.chi) && runLevel(x) === level;
  if (g === 'level6') return all.find(x => same(x) && runGroup(x) !== 'level6' && !runVariant(x)) || null;
  // the twelve methods run at that level; above level 5 the standard level 6 run
  return all.find(x => same(x) && runGroup(x) === 'twelve') ||
    (g === 'boundary' ? null : all.find(x => same(x) && runGroup(x) === 'level6' && !runVariant(x))) || null;
}
const filmHref = r => 'index.html?film=new_' + encodeURIComponent(runKey(r));
const viewerHref = r => 'viewer.html?run=new_' + encodeURIComponent(runKey(r));
const compareHref = (r, twin) => 'recent.html?run=' + encodeURIComponent(runKey(r)) + (twin ? '&compare=' + encodeURIComponent(runKey(twin)) : '');
// shared run groups 20261125 end

  // ---------- text helpers ----------
  const undash = s => String(s ?? '').replace(/\s*[\u2014\u2013]\s*/g, ', ').replace(/\s+-{1,2}\s+/g, ', ').replace(/--/g, ', ');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = t => (Math.abs(t) < 0.005 ? 0 : t).toFixed(2);
  const timeHTML = t => `t = ${fmt(t)} t<sub>cc</sub>`;
  const timePlain = t => `t = ${fmt(t)} t_cc`;
  const slug = s => String(s).replace(/χ\s*/g, 'chi').replace(/\+/g, 'p').normalize('NFKD').replace(/[^\w.]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase();
  const cap = s => String(s || '').replace(/^./, c => c.toUpperCase());

  // ---------- what a run is ----------
  // Runs staged before the catalog carried group, box and variant fields: these are filled in from the id, so that the
  // run groups place them as intended. Fields the catalog gives are never changed.
  const ID_PARTS = [
    [/-(smooth|tanh)-l\d+$/, { group: 'smooth', variant: 'smooth velocity profile' }],
    [/-pxlong-l\d+$/, { group: 'boundary', variant: 'periodic along the wind, 100 R box', boundary: 'periodic along the wind', box: 100 }],
    [/-p3long-l\d+$/, { group: 'boundary', variant: 'periodic on all faces, 100 R box', boundary: 'periodic on all faces', box: 100 }],
    [/-px-l\d+$/, { group: 'boundary', variant: 'periodic along the wind', boundary: 'periodic along the wind' }],
    [/-p3-l\d+$/, { group: 'boundary', variant: 'periodic on all faces', boundary: 'periodic on all faces' }],
    [/-enzoppm-l\d+$/, { group: 'solver', variant: 'Enzo PPM settings' }],
    [/-ppm-l\d+$/, { group: 'solver', variant: 'PPM reconstruction' }],
    [/-hllc-l\d+$/, { group: 'solver', variant: 'HLLC solver' }],
  ];
  function completeRecord(r) {
    if (!Number.isInteger(r.level) && r.n > 0) { const l = Math.round(Math.log2(r.n / 32)) + 3; if (l >= 1 && l <= 8) r.level = l; }
    if (/^apk/i.test(r.id)) return; // the AthenaPK cooling and solver tests carry their settings in the label
    const hit = ID_PARTS.find(([re]) => re.test(r.id));
    if (!hit) return;
    const f = hit[1];
    if (!r.group) r.group = f.group;
    if (!r.boundary && f.boundary) r.boundary = f.boundary;
    if (r.box == null && f.box) r.box = f.box;
    if (!r.variant && !runVariant(r)) r.variant = f.variant;
  }
  const label = r => [runCode(r), `χ ${r.chi}`, `level ${runLevel(r)}`, ...runVariant(r).split(', ')].map(s => undash(s).trim()).filter(Boolean).join(' · ');
  const dims = (l, box = 20) => { const x = 2 ** (l + 3) * box / 20, y = 2 ** (l + 2); return `${x} × ${y} × ${y}`; };
  const codeRank = r => { const i = CODE_ORDER.indexOf(runCode(r)); return i < 0 ? 99 : i; };
  // paper order of the codes, then level from high to low, then χ, then name
  const byPaper = (a, b) => codeRank(a) - codeRank(b) || (codeRank(a) === 99 ? runCode(a).localeCompare(runCode(b)) : 0)
    || runLevel(b) - runLevel(a) || Number(a.chi) - Number(b.chi) || runName(a).localeCompare(runName(b));
  const groupInfo = key => RUN_GROUPS.find(g => g.key === key) || { key, title: 'Other complete runs', about: '' };
  const coolingOn = r => !!r.cooling && r.cooling !== 'none';
  const with3D = r => !has3D || has3D.has(r.id);
  function statusHTML(r) {
    const s = String(r.status || '');
    if (/partial historical coverage/i.test(s)) return 'Ends at ' + timeHTML(tEnd(r));
    if (/accepted bounded result|completed? run/i.test(s)) return 'Complete run';
    if (/historical display/i.test(s)) return 'Earlier run';
    if (/legacy film/i.test(s)) return 'Earlier film';
    if (/historical image set/i.test(s)) return 'Earlier image set';
    return esc(undash(s)).replace(/t_cc/g, 't<sub>cc</sub>');   // "Stops at 3.55 t_cc, where the solver failed"
  }
  const NOTE_DROP = /\b(accepted|bounded|screen|retained|convergence|ranking|controller failure)\b/i;
  function cleanNote(note) {
    return String(note || '').split(/(?<=\.)\s+|;\s*/).map(s => s.trim().replace(/\.$/, '')).filter(s => s && !NOTE_DROP.test(s))
      .map(s => undash(s.replace(/\s*\bin bound input\.in\b/i, '').replace(/\bHistorical\b/g, 'Earlier').replace(/\s+/g, ' ').trim()))
      .filter(Boolean).map(s => s.charAt(0).toUpperCase() + s.slice(1) + '.').join(' ');
  }

  // ---------- time ----------
  const times = r => r._t || (r._t = r.frames.map(f => Number(f.time)));
  const tStart = r => times(r)[0];
  const tEnd = r => times(r)[times(r).length - 1];
  function lowerIndex(a, t) { let lo = 0, hi = a.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (a[m] <= t) lo = m; else hi = m; } return lo; }
  function nearest(r, t) {
    const a = times(r), n = a.length;
    if (n === 1 || t <= a[0]) return 0;
    if (t >= a[n - 1]) return n - 1;
    const lo = lowerIndex(a, t);
    return t - a[lo] <= a[lo + 1] - t ? lo : lo + 1;
  }
  // the state a panel shows now: a saved state, or during smooth playback a blend of two neighbours
  function shown(r) {
    const a = times(r), n = a.length;
    if (S.smooth && (S.playing || S.recording) && n > 1 && S.t > a[0] && S.t < a[n - 1]) {
      const i = lowerIndex(a, S.t), f = (S.t - a[i]) / (a[i + 1] - a[i]);
      if (f > 0.001 && f < 0.999) return { i, j: i + 1, f, t: S.t };
    }
    const i = nearest(r, S.t);
    return { i, j: i, f: 0, t: a[i] };
  }
  const onScreen = () => S.mode === 'twelve' ? gridRuns() : [S.current, S.comparison].filter(Boolean);
  function refRun() {
    const list = onScreen();
    return list.reduce((best, r) => (r.frames.length > best.frames.length ? r : best), list[0] || S.current);
  }
  const minT = () => Math.min(...onScreen().map(tStart));
  const maxT = () => Math.max(...onScreen().map(tEnd));
  function rate() {
    const ref = refRun(), n = ref.frames.length;
    return n < 2 ? 0 : Number($('speed').value || 1) * (tEnd(ref) - tStart(ref)) / (n - 1);
  }

  // ---------- files of a run (contract: "base" holds every file; otherwise the older relative paths) ----------
  const sheetURL = (r, v) => r.base ? r.base + v + '.png' : `assets/recent/${r.id}-${v}.png`;
  function filmURL(r, v) {
    if (r.base) return r.base + `film-${v}.mp4`;
    const key = `assets/films/${r.id}-${v}.mp4`, smooth = window.SMOOTH_60 && window.SMOOTH_60[key];
    return smooth && smooth.src ? smooth.src : key;
  }

  const sheets = new Map();
  function sheet(r, v) {
    const url = sheetURL(r, v);
    let e = sheets.get(url);
    if (!e) {
      e = { img: new Image(), ready: false, failed: false, run: r };
      e.promise = new Promise((resolve, reject) => {
        e.img.crossOrigin = 'anonymous'; // pictures drawn into the canvas must stay exportable when they come from another site
        e.img.decoding = 'async';
        e.img.onload = () => { e.ready = true; resolve(e.img); requestDraw(); };
        e.img.onerror = () => { e.failed = true; const err = new Error(`The pictures of ${label(r)} did not load.`); showError(err.message); reject(err); requestDraw(); };
      });
      e.promise.catch(() => {});
      e.img.src = url;
      sheets.set(url, e);
    }
    return e;
  }
  function retryFailed() { for (const [url, e] of sheets) if (e.failed) sheets.delete(url); $('error').hidden = true; requestDraw(); }
  function showError(msg) {
    const el = $('error'), b = document.createElement('button');
    b.type = 'button'; b.textContent = 'Retry'; b.onclick = retryFailed;
    el.replaceChildren(document.createTextNode(msg + ' '), b); el.hidden = false;
  }

  // ---------- canvas drawing ----------
  // halo: width of a dark outline drawn under the letters, for names written onto a map as in the paper
  const outline = (g, halo) => { g.lineJoin = 'round'; g.lineWidth = halo; g.strokeStyle = 'rgba(0,0,0,.85)'; };
  function text(g, s, x, y, size, color, align = 'left', weight = '', halo = 0) {
    g.font = `${weight} ${size}px ${FONT}`; g.fillStyle = color; g.textAlign = align; g.textBaseline = 'alphabetic';
    if (halo) { outline(g, halo); g.strokeText(s, x, y); }
    g.fillText(s, x, y);
  }
  // text with subscripts: segs = [[text], [text, true], ...]
  function rich(g, segs, x, y, size, color, align = 'left', weight = '', halo = 0) {
    const big = `${weight} ${size}px ${FONT}`, small = `${weight} ${Math.round(size * 0.68)}px ${FONT}`;
    let w = 0;
    for (const [s, sub] of segs) { g.font = sub ? small : big; w += g.measureText(s).width; }
    const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
    g.fillStyle = color; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    for (const pass of halo ? ['stroke', 'fill'] : ['fill']) {
      if (pass === 'stroke') outline(g, halo);
      let cx = x0;
      for (const [s, sub] of segs) {
        g.font = sub ? small : big;
        if (pass === 'stroke') g.strokeText(s, cx, sub ? y + size * 0.24 : y); else g.fillText(s, cx, sub ? y + size * 0.24 : y);
        cx += g.measureText(s).width;
      }
    }
    return w;
  }
  const timeSegs = t => [[`t = ${fmt(t)} t`], ['cc', true]];
  function fitSize(g, s, maxW, size, min, weight = '') {
    for (let f = size; f >= min; f -= 1) { g.font = `${weight} ${f}px ${FONT}`; if (g.measureText(s).width <= maxW) return f; }
    return min;
  }
  // width over height of a run's map: from its box for edge on, square face on
  function mapAspect(r, v) {
    if (v !== 'edge') return 1;
    const e = Array.isArray(r.extent) && r.extent.length === 4 ? r.extent.map(Number) : [-3, 17, -5, 5], a = (e[1] - e[0]) / (e[3] - e[2]);
    return a > 0 && isFinite(a) ? a : 2;
  }
  const rowHeight = r => (Array.isArray(r.image_shape) && r.image_shape[0] > 0 ? r.image_shape[0] : 128); // pixel rows of one saved state in a sheet
  function frame(g, r, v, st, x, y, w, h) {
    g.fillStyle = '#05070d'; g.fillRect(x, y, w, h);
    const e = sheet(r, v);
    if (!e.ready) { text(g, e.failed ? 'Pictures did not load' : 'Loading', x + w / 2, y + h / 2, Math.max(14, Math.round(h * 0.07)), '#7e8da5', 'center'); return false; }
    const sw = e.img.naturalWidth, sh = rowHeight(r), k = Math.min(w / sw, h / sh), dw = sw * k, dh = sh * k, dx = x + (w - dw) / 2, dy = y + (h - dh) / 2;
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    g.drawImage(e.img, 0, st.i * sh, sw, sh, dx, dy, dw, dh);
    if (st.f > 0 && st.j !== st.i) { g.globalAlpha = st.f; g.drawImage(e.img, 0, st.j * sh, sw, sh, dx, dy, dw, dh); g.globalAlpha = 1; }
    return true;
  }
  // the place of a run that a set has no run for
  function emptyCell(g, x, y, w, h, msg) {
    g.fillStyle = '#05070d'; g.fillRect(x, y, w, h);
    g.strokeStyle = '#2c3035'; g.lineWidth = 2; g.strokeRect(x + 1, y + 1, w - 2, h - 2);
    if (msg) { const fs = fitSize(g, msg, w * 0.86, Math.max(14, Math.round(h * 0.11)), 10); text(g, msg, x + w / 2, y + h / 2 + fs * 0.35, fs, '#8a93a3', 'center'); }
  }
  function stamp(g, t, x, y, fs) { // time readout with a dark backing, for pictures without a text band
    g.font = `${fs}px ${FONT}`;
    const w = g.measureText(`t = ${fmt(t)} t`).width + g.measureText('cc').width * 0.72;
    g.fillStyle = 'rgba(5,7,13,.72)'; g.fillRect(x - fs * 0.3, y - fs * 1.05, w + fs * 0.6, fs * 1.5);
    rich(g, timeSegs(t), x, y, fs, '#f1f4fb');
  }
  function tickValues(a, b) { const step = b - a > 40 ? 20 : 5, out = []; for (let v = a; v <= b + 1e-9; v += step) out.push(Math.round(v * 100) / 100); return out; }
  function axes(g, r, v, ix, iy, iw, ih, fs) {
    const ext = Array.isArray(r.extent) && r.extent.length === 4 ? r.extent.map(Number) : [-3, 17, -5, 5];
    const [x0, x1] = v === 'edge' ? [ext[0], ext[1]] : [ext[2], ext[3]], [y0, y1] = [ext[2], ext[3]];
    g.strokeStyle = '#6c7586'; g.lineWidth = 1; g.strokeRect(ix + 0.5, iy + 0.5, iw - 1, ih - 1);
    for (const val of tickValues(x0, x1)) text(g, String(val), ix + (val - x0) / (x1 - x0) * iw, iy + ih + fs * 1.3, fs, '#acb7c9', 'center');
    for (const val of tickValues(y0, y1)) text(g, String(val), ix - fs * 0.6, iy + ih - (val - y0) / (y1 - y0) * ih + fs * 0.35, fs, '#acb7c9', 'right');
    text(g, v === 'edge' ? 'Distance along the wind / R' : 'Transverse distance / R', ix + iw / 2, iy + ih + fs * 2.75, fs, '#acb7c9', 'center');
    g.save(); g.translate(ix - fs * 2.3, iy + ih / 2); g.rotate(-Math.PI / 2); text(g, 'Transverse distance / R', 0, 0, fs, '#acb7c9', 'center'); g.restore();
  }
  const colormap = () => (catalog && Array.isArray(catalog.colormap) && catalog.colormap.length > 1 ? catalog.colormap.map(c => c.map(x => Math.round(x * 255))) : MAGMA);
  const barPos = v => Math.log(v / TICKS[0]) / Math.log(TICKS[TICKS.length - 1] / TICKS[0]);
  function colorbar(g, cx, y, w, h, fs) {
    const cm = colormap(), x = cx - w / 2;
    cm.forEach((c, i) => { g.fillStyle = `rgb(${c.join(',')})`; g.fillRect(x + i * w / cm.length, y, w / cm.length + 1, h); });
    for (const v of TICKS) text(g, String(v), x + barPos(v) * w, y + h + fs * 1.25, fs, '#a5b1c5', 'center');
    rich(g, [['Column density  Σ / (ρ'], ['c,0', true], [' R)  ·  logarithmic scale']], cx, y - fs * 0.7, fs * 1.08, '#c6cfdd', 'center');
  }
  function footer(g, W, H) {
    text(g, 'Cloud Studio · Kaan Boge', 40, H - 22, 20, '#7e8da5');
    text(g, 'kaanboge.github.io/cloud-studio', W - 40, H - 22, 20, '#7e8da5', 'right');
  }
  function panel(g, r, x, y, w, h, o) {
    const v = S.view, asp = mapAspect(r, v), st = shown(r);
    const top = o.title + o.sub + 44, padL = o.labels ? o.axis * 4.6 : 16, padR = 24, padB = o.labels ? o.axis * 3.6 : 8;
    const aw = w - padL - padR, ah = h - top - padB, ih = Math.min(ah, aw / asp), iw = ih * asp;
    const ix = x + padL + (aw - iw) / 2, iy = y + top + (ah - ih) / 2;
    const titleMax = Math.max(iw, w - padL - padR), fs = fitSize(g, label(r), titleMax, o.title, o.min || Math.round(o.title * 0.6), '600');
    let name = label(r);
    g.font = `600 ${fs}px ${FONT}`;
    while (name.length > 8 && g.measureText(name).width > titleMax) name = name.slice(0, -2).trimEnd() + '…'; // never into the next panel
    text(g, name, ix, iy - o.sub - 26, fs, '#f1f4fb', 'left', '600');
    rich(g, [[VIEW_NAME[v] + '  ·  '], ...timeSegs(st.t)], ix, iy - 14, o.sub, '#c9d2e0');
    frame(g, r, v, st, ix, iy, iw, ih);
    if (o.labels) axes(g, r, v, ix, iy, iw, ih, o.axis);
  }
  // full picture: the 1920 x 1080 frame that is saved and recorded; on wide screens the same layout at the shown size
  // (min: the smallest run name in picture units, so that a name on screen stays at 13 CSS px or more)
  function renderRuns(g, W, H, labels, min = 0) {
    g.fillStyle = '#070911'; g.fillRect(0, 0, W, H);
    const list = [S.current, S.comparison].filter(Boolean), bottom = labels ? 150 : 56;
    if (list.length === 2) {
      const o = { title: 30, sub: 24, axis: 21, labels, min };
      panel(g, list[0], 12, 16, W / 2 - 18, H - bottom - 16, o);
      panel(g, list[1], W / 2 + 6, 16, W / 2 - 18, H - bottom - 16, o);
    } else panel(g, list[0], 40, 16, W - 80, H - bottom - 16, { title: 36, sub: 28, axis: 24, labels, min });
    if (labels) colorbar(g, W / 2, H - 104, 720, 20, 22);
    footer(g, W, H);
  }
  // all runs of a set in one picture: the number of columns that gives the largest pictures, or a fixed number
  function bestGrid(n, W, H, aspect, labelH, gap) {
    let best = { cols: 1, rows: n, w: 0 };
    for (let cols = 1; cols <= n; cols++) {
      const rows = Math.ceil(n / cols), w = Math.min((W - gap * (cols - 1)) / cols, ((H - gap * (rows - 1)) / rows - labelH) * aspect);
      if (w > best.w + 0.5) best = { cols, rows, w };
    }
    return best;
  }
  function gridShape(n, W, H, aspect, labelH, gap, cols) {
    if (!cols) return bestGrid(n, W, H, aspect, labelH, gap);
    const rows = Math.max(1, Math.ceil(n / cols));
    return { cols, rows, w: Math.max(1, Math.min((W - gap * (cols - 1)) / cols, ((H - gap * (rows - 1)) / rows - labelH) * aspect)) };
  }
  function gridTitle() {
    const list = gridRuns(), one = f => { const s = [...new Set(list.map(f))]; return s.length === 1 ? s[0] : null; };
    const name = SETS[S.set].name, c = S.set === 'twelve' ? null : one(runCode), code = c && !name.includes(c) ? c : null, chi = one(r => r.chi), mach = one(r => r.mach), L = levelFor(S.set), lvl = L != null ? L : one(runLevel);
    return [name, code, chi != null ? `χ ${chi}` : '', mach ? `Mach ${mach}` : '', lvl != null ? `level ${lvl}` : ''].filter(Boolean).join(', ');
  }
  // the paper layout: each run as an edge on map with its face on map beside it at the same height, one column per group;
  // h is the map height that fits the area, pw the width of one pair
  function pairLayout(groups, AW, AH, P) {
    const G = groups.length, R = Math.max(1, ...groups.map(x => x.runs.length)), head = groups.some(x => x.head) ? P.head : 0;
    const byH = (AH - head - (R - 1) * P.row) / R, byW = (AW - (G - 1) * P.group - G * P.inner) / (3 * G);
    const h = Math.max(1, Math.floor(Math.min(byH, byW)));
    return { G, R, head, h, pw: 3 * h + P.inner };
  }
  const PAIR_PICTURE = { inner: 6, row: 10, group: 64, head: 44 };
  function renderPairs(g, W, top, AW, AH) {
    const groups = gridGroups(), L = pairLayout(groups, AW, AH, PAIR_PICTURE), P = PAIR_PICTURE, h = L.h;
    const totalW = L.G * L.pw + (L.G - 1) * P.group, totalH = L.head + L.R * h + (L.R - 1) * P.row;
    const x0 = (W - totalW) / 2, y0 = top + (AH - totalH) / 2, fs = Math.max(16, Math.min(28, Math.round(h * 0.13))), pad = Math.round(fs * 0.6);
    groups.forEach((grp, n) => {
      const x = x0 + n * (L.pw + P.group);
      if (grp.head) text(g, grp.head, x, y0 + 30, 30, '#f1f4fb', 'left', '600');
      grp.runs.forEach((r, k) => {
        const y = y0 + L.head + k * (h + P.row);
        if (!r) { emptyCell(g, x, y, 2 * h, h, emptyText()); emptyCell(g, x + 2 * h + P.inner, y, h, h, ''); return; }
        const st = shown(r);
        frame(g, r, 'edge', st, x, y, 2 * h, h);
        frame(g, r, 'face', st, x + 2 * h + P.inner, y, h, h);
        const name = tileName(r), nf = fitSize(g, name, 2 * h - 2 * pad, fs, 12, '600');
        text(g, name, x + pad, y + pad + nf * 0.8, nf, '#ffffff', 'left', '600', Math.max(3, nf * 0.22));
        rich(g, timeSegs(st.t), x + pad, y + h - pad, fs, '#f1f4fb', 'left', '', Math.max(3, fs * 0.22));
      });
    });
  }
  function renderGrid(g, W, H, labels) {
    g.fillStyle = '#070911'; g.fillRect(0, 0, W, H);
    const v = S.gview, bottom = labels ? 150 : 56, ref = refRun();
    const vw = rich(g, [[VIEW_NAME[v] + '  ·  '], ...timeSegs(shown(ref).t)], W - 40, 58, 32, '#c9d2e0', 'right'), title = gridTitle();
    text(g, title, 40, 58, fitSize(g, title, W - 120 - vw, 36, 22, '600'), '#f1f4fb', 'left', '600');
    const top = 90, AW = W - 80, AH = H - top - bottom, lab = 34, gap = 28;
    if (v === 'both') {
      renderPairs(g, W, top, AW, AH);
      text(g, 'Edge on with the wind from left to right, face on beside it looking along the wind', W / 2, H - 22, 20, '#7e8da5', 'center');
    } else {
      const cells = gridCells(), [sw, sh] = SHEET[v], L = gridShape(cells.length, AW, AH, sw / sh, lab, gap, fixedCols()), iw = L.w, ih = iw * sh / sw;
      const totalW = L.cols * iw + (L.cols - 1) * gap, totalH = L.rows * (ih + lab) + (L.rows - 1) * gap;
      const x0 = (W - totalW) / 2, y0 = top + (AH - totalH) / 2, fs = Math.max(16, Math.min(24, Math.round(iw / 15)));
      cells.forEach((r, k) => {
        const x = x0 + (k % L.cols) * (iw + gap), y = y0 + Math.floor(k / L.cols) * (ih + lab + gap);
        if (!r) { emptyCell(g, x, y + lab, iw, ih, emptyText()); return; }
        const st = shown(r), tw = rich(g, timeSegs(st.t), x + iw, y + lab - 10, fs, '#c9d2e0', 'right');
        const name = tileName(r), nf = fitSize(g, name, iw - tw - 12, fs, 12, '600');
        text(g, name, x, y + lab - 10, nf, '#f1f4fb', 'left', '600');
        frame(g, r, v, st, x, y + lab, iw, ih);
      });
    }
    if (labels) colorbar(g, W / 2, H - 104, 720, 20, 22);
    footer(g, W, H);
  }
  function setCanvas(W, H) { if (canvas.width !== W) canvas.width = W; if (canvas.height !== H) canvas.height = H; }
  // the size in CSS px at which the canvas shows a picture of this width over height (its CSS width, limited by max-height)
  function screenBox(aspect) {
    const w = canvas.getBoundingClientRect().width, mh = parseFloat(getComputedStyle(canvas).maxHeight);
    const cw = mh > 0 ? Math.min(w, mh * aspect) : w;
    return { w: cw, h: cw / aspect };
  }
  // backing store at the shown size times the device pixel ratio, drawn in picture units of W x H
  function fitCanvas(W, H, box) {
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_BACKING / box.w);
    setCanvas(Math.max(1, Math.round(box.w * dpr)), Math.max(1, Math.round(box.h * dpr)));
    ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  }
  function picture1920() { setCanvas(1920, 1080); ctx.setTransform(1, 0, 0, 1, 0, 0); }
  // narrow screens: the picture fills the canvas, the time stays drawn in, names and colour bar go to the caption below
  function renderCompact() {
    const list = [S.current, S.comparison].filter(Boolean), v = S.view, [sw, sh] = SHEET[v];
    const k = v === 'edge' ? 5 : 7.5, cw = sw * k, ch = sh * k, gap = 24;
    const vertical = list.length === 2 && v === 'edge', cols = list.length === 2 && !vertical ? 2 : 1, rows = vertical ? 2 : 1;
    const W = cols * cw + (cols - 1) * gap, H = rows * ch + (rows - 1) * gap, box = screenBox(W / H);
    if (!(box.w > 0)) return false;
    const fs = STAMP_PX * W / box.w; // 16 CSS px whatever the width of the screen
    fitCanvas(W, H, box);
    ctx.fillStyle = '#070911'; ctx.fillRect(0, 0, W, H);
    list.forEach((r, n) => {
      const x = cols === 2 ? n * (cw + gap) : 0, y = rows === 2 ? n * (ch + gap) : 0, st = shown(r);
      frame(ctx, r, v, st, x, y, cw, ch);
      stamp(ctx, st.t, x + fs * 0.6, y + fs * 1.4, fs);
    });
    return true;
  }
  function drawScene() {
    // side by side shows its tiles on screen; the canvas draws it only while a video is recorded
    if (S.mode === 'twelve') { picture1920(); renderGrid(ctx, 1920, 1080, S.labels); return; }
    if (!S.recording) {
      if (S.compact && renderCompact()) return;
      const box = screenBox(16 / 9);
      if (!S.compact && box.w > 0) {
        const u = Math.max(SCREEN_UNITS, MIN_SCREEN_W / box.w), W = box.w * u, H = box.h * u;
        fitCanvas(W, H, box); renderRuns(ctx, W, H, S.labels, Math.min(24, Math.ceil(13 * u))); return;
      }
    }
    picture1920(); renderRuns(ctx, 1920, 1080, S.labels);
  }

  // ---------- runs side by side (small canvases, sheets load when a tile comes into view) ----------
  // A set is one or more columns of runs, as in the paper, made from the run groups. Rows line up across the columns,
  // and a run a row has no partner for is drawn as an empty picture. A set with runs at several levels shows one level at a time.
  const PAPER_LEFT = 6; // as in the paper: Athena++ to RAMSES on the left, FLASH 4.8 to GADGET-4 on the right
  const EMPTY = 'No run at this level';
  const FACE_ORDER = ['inflow and outflow', 'periodic along the wind', 'periodic on all faces'];
  const faceRank = r => { const i = FACE_ORDER.indexOf(String(r.boundary || '').toLowerCase()); return i < 0 ? 9 : i; };
  const inGroup = key => runs.filter(r => runGroup(r) === key);
  // the standard run a run is compared with: from the run groups, or from the id (athpp-100-ppm-l4 to athpp-100-l4)
  function twinOf(r) {
    const t = runTwin(r, runs);
    if (t) return t;
    const id = String(r.id).replace(/-(ppm|hllc|enzoppm|smooth|tanh|pxlong|p3long|px|p3)(?=-l\d+$)/, '');
    return (id !== r.id && byId.get(id)) || null;
  }
  // one column per code: the standard run on top, then the same code in the other boxes
  function stackCols(list) {
    const codes = [...new Set(list.slice().sort(byPaper).map(runCode))];
    return codes.map(c => {
      const own = list.filter(r => runCode(r) === c).sort((a, b) => faceRank(a) - faceRank(b) || label(a).localeCompare(label(b)));
      return { head: '', runs: [own.map(twinOf).find(Boolean) || null, ...own] };
    });
  }
  // two columns: each run of the group beside the standard run it is compared with
  function pairCols(list, heads) {
    const rows = list.slice().sort(byPaper);
    return [{ head: heads[0], runs: rows.map(twinOf) }, { head: heads[1], runs: rows }];
  }
  function contrastCols(list) {
    const chis = [...new Set(list.map(r => Number(r.chi)))].sort((a, b) => a - b), names = [...new Set(list.slice().sort(byPaper).map(runName))];
    return chis.map(c => ({ head: `χ ${c}`, runs: names.map(n => list.find(r => Number(r.chi) === c && runName(r) === n) || null) }));
  }
  const solverOf = r => runVariant(r).replace(/(^|,\s*)cooling (on|off)(?=,|$)/i, '').replace(/^,\s*|,\s*$/g, '').trim();
  function coolingCols(list) {
    const rows = list.slice().sort(byPaper);
    const off = r => runs.find(x => x !== r && !coolingOn(x) && runCode(x) === runCode(r) && Number(x.chi) === Number(r.chi) && runLevel(x) === runLevel(r)
      && solverOf(x) === solverOf(r) && /cooling off/i.test(runVariant(x))) || null;
    return [{ head: 'Cooling off', runs: rows.map(off) }, { head: 'Cooling on', runs: rows }];
  }
  const boundaryTile = r => (r.boundary ? cap(undash(r.boundary)) : runName(r));
  const longBoxTile = r => boundaryTile(r) + (runBox(r) === 100 ? ', 100 R box' : ', 20 R box');
  // name: the Set menu; data: the runs that make the set (their partners come from twinOf); aligned: rows line up across the columns
  const SETS = {
    twelve: { name: 'Twelve methods', file: 'twelve-methods', about: 'twelve', data: () => inGroup('twelve'), tile: r => runCode(r),
      cols: list => {
        const seen = new Set(), l = list.slice().sort(byPaper).filter(r => !seen.has(runCode(r)) && seen.add(runCode(r)));
        return [{ head: '', runs: l.filter(r => codeRank(r) < PAPER_LEFT) }, { head: '', runs: l.filter(r => codeRank(r) >= PAPER_LEFT) }];
      } },
    boundary20: { name: 'Boundary control, 20 R boxes', file: 'boundary-control-20R', about: 'boundary', tile: boundaryTile, cols: stackCols,
      data: () => inGroup('boundary').filter(r => runBox(r) === 20) },
    boundary100: { name: 'Boundary control, 100 R boxes', file: 'boundary-control-100R', about: 'boundary', tile: longBoxTile, cols: stackCols,
      data: () => inGroup('boundary').filter(r => runBox(r) === 100) },
    solver: { name: 'Solver settings', file: 'solver-settings', about: 'solver', aligned: true, tile: r => runName(r),
      data: () => inGroup('solver'), cols: list => pairCols(list, ['Standard setting', 'Changed setting']) },
    smooth: { name: 'Smooth velocity profile', file: 'smooth-velocity-profile', about: 'smooth', aligned: true,
      tile: r => runCode(r) + (runGroup(r) === 'smooth' ? ', smooth' : ', sharp'),
      data: () => inGroup('smooth'), cols: list => pairCols(list, ['Sharp velocity edge', 'Smooth velocity profile']) },
    contrast: { name: 'Density contrast 10 and 1000', file: 'contrast-chi10-chi1000', about: 'contrast', aligned: true, tile: r => `${runName(r)}, χ ${r.chi}`,
      data: () => inGroup('contrast'), cols: contrastCols },
    cooling: { name: 'AthenaPK cooling on and off', file: 'cooling-on-off', aligned: true, empty: 'No run with cooling off',
      about: 'AthenaPK at χ 100 with tabulated radiative cooling switched off and switched on, one row for each Riemann solver and reconstruction.',
      tile: r => `${solverOf(r) || runCode(r)}, cooling ${coolingOn(r) ? 'on' : 'off'}`, data: () => runs.filter(coolingOn), cols: coolingCols },
    level6: { name: 'Level 5 and level 6', file: 'level5-level6', about: 'level6', aligned: true, oneLevel: true, empty: 'No run at level 5',
      extra: 'Each level 6 run stands next to the same run at level 5.', tile: r => `${runName(r)}, χ ${r.chi}, level ${runLevel(r)}`,
      data: () => inGroup('level6'), cols: list => pairCols(list, ['Level 5', 'Level 6']) },
  };
  const SET_ALIAS = { boundary: 'boundary20' }; // links written before 2026-11-25
  const setLevels = key => (SETS[key].oneLevel ? [] : [...new Set(SETS[key].data().map(runLevel))].sort((a, b) => b - a));
  function levelFor(key) { const lv = setLevels(key); return !lv.length ? null : lv.includes(S.level) ? S.level : lv.includes(5) ? 5 : lv[0]; }
  const setBox = key => (SETS[key].data().some(r => runBox(r) === 100) ? 100 : 20);
  function groupsOf(key) {
    const set = SETS[key];
    if (!set) return [];
    const L = levelFor(key);
    return set.cols(set.data().filter(r => L == null || runLevel(r) === L)).filter(c => c.runs.some(Boolean));
  }
  const memo = new Map();
  function gridGroups() { const k = S.set + '|' + S.level; if (!memo.has(k)) memo.set(k, groupsOf(S.set)); return memo.get(k); }
  const hasRuns = key => SETS[key].data().length > 0;
  const anySet = () => Object.keys(SETS).some(hasRuns);
  const aligned = () => !!SETS[S.set].aligned && gridGroups().length > 1;
  const fixedCols = () => (aligned() ? gridGroups().length : 0);
  // the pictures in reading order: the columns one after another, or row by row where the rows line up
  function gridCells() {
    const groups = gridGroups();
    if (!aligned()) return groups.flatMap(x => x.runs);
    const R = Math.max(...groups.map(x => x.runs.length)), out = [];
    for (let k = 0; k < R; k++) for (const x of groups) out.push(x.runs[k] || null);
    return out;
  }
  const gridRuns = () => gridCells().filter(Boolean);
  const tileName = r => undash((SETS[S.set].tile || runName)(r));
  const emptyText = () => SETS[S.set].empty || EMPTY;
  const gridViews = () => (S.gview === 'both' ? ['edge', 'face'] : [S.gview]);
  const PAIR_SCREEN = { inner: 4, row: 8, group: 24, head: 30 }; // the gaps of .tiles.both, .group, .maps and .group-head in recent.css
  function makeTile(r) {
    const v = S.gview, pair = v === 'both', views = gridViews(), span = cls => { const e = document.createElement('span'); e.className = cls; return e; };
    const fig = document.createElement(r ? 'button' : 'div'), name = span('code'), time = span('t');
    const canvases = views.map(w => { const c = document.createElement('canvas'), [sw, sh] = SHEET[w]; c.width = sw * 2; c.height = sh * 2; c.setAttribute('aria-hidden', 'true'); return c; });
    fig.className = (pair ? 'tile pair' : 'tile') + (r ? '' : ' empty');
    if (pair) { // name and time written onto the edge on map, as in the paper
      const maps = span('maps'), box = span('edgebox');
      box.append(canvases[0], name, time); maps.append(box, canvases[1]); fig.append(maps);
    } else {
      const cp = span('tile-cap');
      cp.append(name, time); fig.append(canvases[0], cp);
    }
    if (!r) {
      fig.setAttribute('role', 'img'); fig.setAttribute('aria-label', emptyText());
      canvases.forEach((c, n) => emptyCell(c.getContext('2d'), 0, 0, c.width, c.height, n ? '' : emptyText()));
      return { run: null, fig, views, canvases, ctxs: [], time, visible: false, key: '', th: '' };
    }
    fig.type = 'button'; name.textContent = tileName(r);
    const th = timeHTML(shown(r).t); time.innerHTML = th; // there from the start, so that the caption is measured whole
    fig.addEventListener('click', () => { if (!S.recording) { $('run').value = r.id; $('compare').value = ''; setMode('runs'); select(); } });
    fig.title = `Open ${label(r)}`; fig.setAttribute('aria-label', `Open ${label(r)}, ${VIEW_NAME[v].toLowerCase()}`);
    return { run: r, fig, views, canvases, ctxs: canvases.map(c => c.getContext('2d')), time, visible: false, key: '', th };
  }
  // narrow screens, where the columns of a set cannot stand side by side: the pairs of a set whose rows line up
  // go into one column row by row, so that every run sits right under the run it is compared with
  function stackedPairs() {
    if (S.gview !== 'both' || !aligned() || matchMedia('(min-width: 900px)').matches || document.fullscreenElement) return false;
    const G = gridGroups().length, W = $('tiles').clientWidth;
    return W > 0 && (W - (G - 1) * PAIR_SCREEN.group) / G < 300;
  }
  const screenGroups = () => (S.stacked ? [{ head: '', runs: gridCells() }] : gridGroups());
  function buildGrid() {
    if (S.observer) S.observer.disconnect();
    const v = S.gview, holder = $('tiles');
    S.tiles = [];
    S.stacked = stackedPairs();
    if (v === 'both') {
      holder.replaceChildren(...screenGroups().map(grp => {
        const col = document.createElement('div');
        col.className = 'group';
        if (grp.head) { const h = document.createElement('p'); h.className = 'group-head'; h.textContent = grp.head; col.append(h); }
        for (const r of grp.runs) { const t = makeTile(r); S.tiles.push(t); col.append(t.fig); }
        return col;
      }));
    } else {
      S.tiles = gridCells().map(makeTile);
      holder.replaceChildren(...S.tiles.map(t => t.fig));
    }
    holder.classList.toggle('face', v === 'face'); holder.classList.toggle('both', v === 'both'); $('grid').classList.toggle('both', v === 'both');
    const live = S.tiles.filter(t => t.run);
    S.observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
      for (const en of entries) { const t = live.find(x => x.fig === en.target); if (t) { t.visible = en.isIntersecting; if (t.visible) { t.views.forEach(w => sheet(t.run, w)); t.key = ''; } } }
      requestDraw();
    }, { rootMargin: '300px 0px' }) : null;
    if (S.observer) live.forEach(t => S.observer.observe(t.fig)); else live.forEach(t => { t.visible = true; });
    $('gridHead').textContent = gridTitle();
    layoutGrid();
  }
  function layoutGrid() {
    if (S.mode !== 'twelve' || !S.tiles.length) return;
    const holder = $('tiles'), wide = matchMedia('(min-width: 900px)').matches, aspect = S.gview === 'edge' ? 2 : 1;
    if (S.gview === 'both') {
      if (stackedPairs() !== S.stacked) { buildGrid(); return; }
      const groups = screenGroups(), P = PAIR_SCREEN, W = holder.clientWidth;
      let pw;
      if (wide || document.fullscreenElement) pw = pairLayout(groups, W, holder.clientHeight, P).pw;
      else { // narrow screens: the groups side by side while a pair keeps at least 300 px, otherwise one column
        let k = groups.length;
        while (k > 1 && (W - (k - 1) * P.group) / k < 300) k--;
        pw = Math.max(60, Math.floor((W - (k - 1) * P.group) / k));
      }
      holder.style.setProperty('--pair-w', pw + 'px'); holder.style.removeProperty('--cols'); holder.style.removeProperty('--tile-w'); holder.style.removeProperty('--col-w');
      return;
    }
    holder.style.removeProperty('--pair-w');
    const fixed = fixedCols();
    if (wide || document.fullscreenElement) {
      // pictures sized for one line of name and time (24 px). A column may be wider than its picture, up to the widest
      // caption, so that names stay on one line; where even that does not fit, the pictures are sized again for the wrapped names.
      const caps = [...holder.querySelectorAll('.tile-cap')], W = holder.clientWidth;
      holder.classList.add('measure');
      const need = Math.ceil(Math.max(0, ...caps.map(c => c.getBoundingClientRect().width)));
      holder.classList.remove('measure');
      const fit = lab => {
        const L = gridShape(S.tiles.length, W, holder.clientHeight, aspect, lab, 12, fixed), tw = Math.floor(L.w);
        const col = Math.max(tw, Math.min(need, Math.floor((W - 12 * (L.cols - 1)) / L.cols)));
        holder.style.setProperty('--cols', L.cols); holder.style.setProperty('--tile-w', tw + 'px'); holder.style.setProperty('--col-w', col + 'px');
      };
      const capH = () => Math.max(24, ...caps.map(c => Math.ceil(c.getBoundingClientRect().height)));
      let lab = 24;
      fit(lab);
      for (let k = 0; k < 2 && capH() > lab; k++) { lab = capH(); fit(lab); }
    } else {
      holder.style.setProperty('--cols', fixed || (S.gview === 'edge' ? 2 : 3)); holder.style.removeProperty('--tile-w'); holder.style.removeProperty('--col-w');
    }
  }
  function drawGrid() {
    for (const tile of S.tiles) {
      const r = tile.run;
      if (!r) continue;
      const es = tile.views.map(w => sheets.get(sheetURL(r, w)));
      if (!tile.visible && !es.every(e => e && e.ready)) continue;
      const st = shown(r), key = `${st.i}|${st.j}|${st.f.toFixed(3)}|${es.map(e => (e ? e.ready + '' + e.failed : 'new')).join('|')}`;
      if (key !== tile.key) { tile.key = key; tile.views.forEach((w, n) => frame(tile.ctxs[n], r, w, st, 0, 0, tile.canvases[n].width, tile.canvases[n].height)); }
      const th = timeHTML(st.t);
      if (th !== tile.th) { tile.th = th; tile.time.innerHTML = th; }
    }
  }

  // ---------- page text that follows the picture ----------
  function buildBar(el) {
    const cm = colormap(), stops = [];
    for (let i = 0; i < cm.length; i += Math.max(1, Math.floor(cm.length / 24))) stops.push(`rgb(${cm[i].join(',')}) ${(i / (cm.length - 1) * 100).toFixed(1)}%`);
    stops.push(`rgb(${cm[cm.length - 1].join(',')}) 100%`);
    el.innerHTML = `<span class="cbar-title">Column density Σ / (ρ<sub>c,0</sub> R), logarithmic</span><span class="cbar-strip" style="background:linear-gradient(90deg,${stops.join(',')})"></span><span class="cbar-ticks">${TICKS.map(v => `<span style="left:${(barPos(v) * 100).toFixed(2)}%">${v}</span>`).join('')}</span>`;
  }
  function updateReadouts() {
    const ref = refRun(); if (!ref) return;
    const t = shown(ref).t, html = timeHTML(t);
    if (html !== S.timeHTML) { S.timeHTML = html; $('timeLabel').innerHTML = html; $('time').setAttribute('aria-valuetext', timePlain(t)); }
    if (!S.dragging) $('time').value = String(S.t);
    if (S.mode === 'twelve') return;
    if (S.compact) {
      const rows = [S.current, S.comparison].filter(Boolean).map(r => `<p><b>${esc(label(r))}</b><span>${VIEW_NAME[S.view]}, ${timeHTML(shown(r).t)}</span></p>`).join('');
      if ($('captionRows').innerHTML !== rows) $('captionRows').innerHTML = rows;
    }
  }
  function detailBlock(r, heading) {
    const n = r.frames.length, L = runLevel(r), g = runGroup(r), facts = [statusHTML(r)];
    if (g === 'twelve') facts.push('One of the twelve methods');
    else if (g !== 'other' && g !== 'level6') facts.push(esc(groupInfo(g).title));
    if (r.boundary) facts.push(esc(cap(undash(r.boundary))) + (runBox(r) === 100 ? ' in a 100 R long box' : ''));
    if (coolingOn(r)) facts.push('Cooling on');
    const note = cleanNote(r.note);
    return `${heading ? `<h3>${esc(label(r))}</h3>` : ''}<p class="meta">Mach ${esc(r.mach)}, level ${L}, ${dims(L, runBox(r))} cells, ${n} saved states to ${timeHTML(tEnd(r))}</p>`
      + `<p>${facts.filter(Boolean).map(s => s + '.').join(' ')}</p>${note ? `<p>${esc(note).replace(/t_cc/g, 't<sub>cc</sub>')}</p>` : ''}`;
  }
  function updateDetails() {
    if (S.mode === 'twelve') {
      const set = SETS[S.set], list = [...new Set(gridRuns())], L = levelFor(S.set), info = groupInfo(set.about);
      const about = [info.about || set.about, set.extra].filter(Boolean).join(' ');
      const order = S.set === 'twelve' ? ' Athena++ to RAMSES stand on the left, FLASH 4.8 to GADGET-4 on the right.' : '';
      const empty = gridCells().some(c => !c) ? ' An empty picture stands for a run that is not available.' : '';
      const cells = L == null ? '' : setBox(S.set) === 100 ? `Level ${L}, ${dims(L)} cells in the 20 R box and ${dims(L, 100)} in the 100 R boxes, ` : `Level ${L}, ${dims(L)} cells, `;
      $('title').textContent = gridTitle();
      $('detailBody').innerHTML = `<p>${esc(about)}${order} Every picture shows its own saved state nearest to the chosen time.${empty}</p>`
        + `<p class="meta">${cells}${list.length} ${list.length === 1 ? 'run' : 'runs'}.</p><p>Select a picture to open that run.</p>`;
      return;
    }
    $('title').textContent = S.comparison ? 'Two runs at the same time' : label(S.current);
    $('detailBody').innerHTML = S.comparison ? detailBlock(S.current, true) + detailBlock(S.comparison, true) : detailBlock(S.current, false);
  }
  function updateLinks() {
    const r = S.current, v = S.view;
    $('mp4').hidden = !!S.comparison || S.mode === 'twelve';
    $('mp4').href = filmURL(r, v);
    $('mp4').download = `cloud-studio_${slug(label(r))}_${v}.mp4`;
    $('mp4').title = `Film of ${label(r)}, ${VIEW_NAME[v].toLowerCase()}, 60 fps`;
    $('rotate3d').href = viewerHref(r);
    $('rotate3d').hidden = S.mode === 'twelve' || !with3D(r);
  }
  function syncURL() {
    clearTimeout(S.urlTimer);
    S.urlTimer = setTimeout(() => {
      const u = new URL(location), p = u.searchParams;
      p.delete('frame');
      p.set('run', S.current.id);
      if (S.comparison && S.mode === 'runs') p.set('compare', S.comparison.id); else p.delete('compare');
      p.set('view', S.mode === 'twelve' ? S.gview : S.view);
      p.set('t', fmt(shown(refRun()).t));
      if (S.mode === 'twelve') {
        const L = levelFor(S.set);
        p.set('mode', 'twelve'); p.set('set', S.set);
        if (L != null) p.set('level', String(L)); else p.delete('level');
      } else { p.delete('mode'); p.delete('set'); p.delete('level'); }
      if (u.href !== location.href) history.replaceState(null, '', u);
    }, 200);
  }

  // ---------- drawing loop and playback ----------
  let queued = false;
  function requestDraw() { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; draw(); }); } }
  function draw() {
    if (!S.current) return;
    if (S.mode === 'twelve' && !S.recording) drawGrid(); else drawScene();
    updateReadouts();
  }
  function buildSpeeds() {
    const many = refRun().frames.length > 30, key = many ? 'many' : 'few';
    if (key === S.speedKey) return;
    S.speedKey = key;
    const opts = many ? [5, 10, 20] : [1, 2, 4], def = many ? 10 : 2;
    $('speed').replaceChildren(...opts.map(v => { const o = new Option(`${v} frames/s`, String(v)); o.selected = v === def; return o; }));
  }
  function setRange() {
    const lo = minT(), hi = maxT();
    $('time').min = String(lo); $('time').max = String(hi);
    S.t = Math.min(Math.max(S.t, lo), hi);
  }
  function setPlayButton() { $('play').textContent = S.playing ? 'Pause' : 'Play'; }
  function ready() { // pictures needed right now are loaded
    if (S.mode === 'twelve') return S.tiles.every(t => !t.run || !t.visible || t.views.every(w => { const e = sheets.get(sheetURL(t.run, w)) || {}; return e.ready || e.failed; }));
    return onScreen().every(r => { const e = sheet(r, S.view); return e.ready || e.failed; });
  }
  function tick(now) {
    if (!S.playing) return;
    const dt = S.last ? Math.min(0.1, (now - S.last) / 1000) : 0;
    S.last = now;
    if (ready()) {
      const lo = minT(), hi = maxT();
      S.t += dt * rate();
      if (S.t > hi) S.t = lo + (S.t - hi) % Math.max(hi - lo, 1e-6);
    }
    draw();
    S.raf = requestAnimationFrame(tick);
  }
  function play() {
    if (S.playing || S.recording) return;
    if (S.t >= maxT() - 1e-6) S.t = minT();
    S.playing = true; S.last = 0; setPlayButton();
    S.raf = requestAnimationFrame(tick);
  }
  function pause() {
    if (!S.playing) return;
    S.playing = false; cancelAnimationFrame(S.raf);
    const ref = refRun(); S.t = times(ref)[nearest(ref, S.t)];
    setPlayButton(); requestDraw(); syncURL();
  }
  const toggle = () => (S.playing ? pause() : play());
  function step(d) {
    if (S.recording) return;
    pause();
    const ref = refRun(), a = times(ref), i = Math.min(a.length - 1, Math.max(0, nearest(ref, S.t) + d));
    S.t = a[i]; requestDraw(); syncURL();
  }
  function jump(end) { if (S.recording) return; pause(); S.t = end ? maxT() : minT(); requestDraw(); syncURL(); }

  // ---------- choosing what is shown ----------
  function refresh() { buildSpeeds(); setRange(); updateDetails(); updateLinks(); requestDraw(); syncURL(); }
  function markCurrent() {
    for (const tr of document.querySelectorAll('#tables tr[data-id]')) {
      if (S.current && tr.dataset.id === S.current.id) tr.setAttribute('aria-current', 'true'); else tr.removeAttribute('aria-current');
    }
  }
  function select() {
    S.current = byId.get($('run').value) || S.current;
    S.comparison = byId.get($('compare').value) || null;
    markCurrent();
    refresh();
  }
  function buildLevels() {
    const lv = setLevels(S.set), box = setBox(S.set);
    $('level').replaceChildren(...lv.map(l => new Option(`Level ${l}, ${dims(l, box)} cells`, String(l))));
    const L = levelFor(S.set);
    if (L != null) $('level').value = String(L);
  }
  // the View menu offers both maps side by side only in the side by side mode; Level shows for sets with runs at several levels
  function setChoices() {
    const sel = $('view'), grid = S.mode === 'twelve', both = sel.querySelector('option[value="both"]');
    if (grid && !both) sel.add(new Option('Edge on and face on, as in the paper', 'both'));
    if (!grid && both) both.remove();
    sel.value = grid ? S.gview : S.view;
    buildLevels();
    $('levelWrap').hidden = !grid || setLevels(S.set).length < 2;
  }
  function buildSets() {
    const keys = Object.keys(SETS).filter(hasRuns);
    $('set').replaceChildren(...keys.map(k => new Option(SETS[k].name, k)));
    if (keys.length && !keys.includes(S.set)) S.set = keys[0];
    $('set').value = S.set;
    return keys;
  }
  function setMode(mode) {
    if (mode === 'twelve' && !anySet()) mode = 'runs';
    pause();
    S.mode = mode;
    const twelve = mode === 'twelve';
    $('modeRuns').setAttribute('aria-pressed', String(!twelve)); $('modeTwelve').setAttribute('aria-pressed', String(twelve));
    document.querySelectorAll('.run-only').forEach(e => { e.hidden = twelve; });
    document.querySelectorAll('.twelve-only').forEach(e => { e.hidden = !twelve; });
    setChoices();
    $('studio').classList.toggle('twelve', twelve);
    canvas.hidden = twelve; $('grid').hidden = !twelve; $('caption').hidden = twelve || !S.compact;
    if (twelve) buildGrid(); else if (S.observer) { S.observer.disconnect(); S.observer = null; }
    refresh();
  }
  function measure() { // keep the picture and the Play button inside one window height on wide screens
    const wide = matchMedia('(min-width: 900px)').matches, root = document.documentElement;
    if (!wide) { root.style.removeProperty('--chrome'); return; }
    const top = $('studio').getBoundingClientRect().top + scrollY, tr = document.querySelector('.transport').offsetHeight;
    const below = $('caption').hidden ? 0 : $('caption').offsetHeight;
    root.style.setProperty('--chrome', Math.round(top + tr + below + 22) + 'px');
  }
  function onResize() {
    const w = $('screen').clientWidth, compact = w > 0 && w < COMPACT_BELOW && !document.fullscreenElement;
    if (compact !== S.compact) { S.compact = compact; $('caption').hidden = !compact || S.mode === 'twelve'; S.timeHTML = ''; measure(); }
    layoutGrid(); requestDraw();
  }

  // ---------- saving ----------
  function download(blob, name) {
    const u = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = u; a.download = name; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 60000);
  }
  const message = s => { $('message').textContent = s; };
  function baseName() {
    const t = fmt(shown(refRun()).t);
    if (S.mode === 'twelve') { const L = levelFor(S.set); return `cloud-studio_${SETS[S.set].file}${L != null ? '_level' + L : ''}_${VIEW_FILE[S.gview]}_t${t}`; }
    return `cloud-studio_${slug(label(S.current))}${S.comparison ? '_vs_' + slug(label(S.comparison)) : ''}_${S.view}_t${t}`;
  }
  const loadAll = () => Promise.all(onScreen().flatMap(r => (S.mode === 'twelve' ? gridViews() : [S.view]).map(w => sheet(r, w).promise)));
  async function savePicture() {
    if (S.recording) return;
    pause();
    try {
      message('Preparing the picture');
      await loadAll();
      const c = document.createElement('canvas'); c.width = 1920; c.height = 1080;
      const g = c.getContext('2d');
      if (S.mode === 'twelve') renderGrid(g, 1920, 1080, S.labels); else renderRuns(g, 1920, 1080, S.labels);
      const blob = await new Promise((resolve, reject) => { try { c.toBlob(b => (b ? resolve(b) : reject(new Error('empty picture'))), 'image/png'); } catch (e) { reject(e); } });
      download(blob, baseName() + '.png');
      message('Picture saved, 1920 × 1080.');
    } catch (e) { message('The picture could not be saved: ' + e.message); }
  }
  async function record() {
    if (S.recording) return;
    pause();
    const type = ['video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'].find(t => window.MediaRecorder && MediaRecorder.isTypeSupported(t));
    if (!canvas.captureStream || !type) { message('This browser cannot record the picture. A screen recorder works instead.'); return; }
    try { message('Loading the pictures'); await loadAll(); } catch (e) { message(e.message); return; }
    S.recording = true;
    const controls = [...document.querySelectorAll('#studio select, #studio button, #studio input')];
    controls.forEach(e => { e.disabled = true; });
    const twelve = S.mode === 'twelve';
    if (twelve) { $('grid').hidden = true; canvas.hidden = false; }
    const lo = minT(), hi = maxT(), speed = rate() || 1;
    let rec = null;
    // one pass from the first to the last saved state; the first frame is held until the encoder delivers data,
    // so that a short run never comes out empty while the browser's video encoder is still starting
    const once = async mime => {
      const chunks = [], stream = canvas.captureStream(60);
      try {
        S.t = lo; draw();
        rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 12000000 });
        rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
        const done = new Promise((resolve, reject) => { rec.onstop = resolve; rec.onerror = e => reject(e.error || new Error('recording failed')); });
        rec.start(100);
        message(`Recording ${VIEW_NAME[twelve ? S.gview : S.view].toLowerCase()} from ${timePlain(lo)} to ${timePlain(hi)}`);
        await new Promise(resolve => {
          let start = 0;
          const t0 = performance.now();
          const f = now => {
            if (!start && (chunks.reduce((a, c) => a + c.size, 0) > 200 || now - t0 > 3000)) start = now;
            S.t = start ? Math.min(hi, lo + (now - start) / 1000 * speed) : lo; draw();
            if (!start || S.t < hi) requestAnimationFrame(f); else setTimeout(resolve, 600);
          };
          requestAnimationFrame(f);
        });
        rec.stop(); await done;
        return new Blob(chunks, { type: mime });
      } finally { stream.getTracks().forEach(t => t.stop()); }
    };
    try {
      let blob = await once(type);
      if (!blob.size && type.startsWith('video/mp4')) {
        const webm = ['video/webm;codecs=vp9', 'video/webm'].find(t => MediaRecorder.isTypeSupported(t));
        if (webm) blob = await once(webm);
      }
      if (!blob.size) throw new Error('the browser delivered an empty video');
      download(blob, baseName().replace(/_t[\d.]+$/, '') + (blob.type.startsWith('video/mp4') ? '.mp4' : '.webm'));
      message('Video saved, one full cycle.');
    } catch (e) { if (rec && rec.state !== 'inactive') rec.stop(); message('The video could not be recorded: ' + e.message); }
    finally {
      controls.forEach(e => { e.disabled = false; });
      S.recording = false;
      if (twelve) { canvas.hidden = true; $('grid').hidden = false; S.tiles.forEach(t => { t.key = ''; }); }
      S.t = times(refRun())[nearest(refRun(), S.t)];
      requestDraw(); syncURL();
    }
  }

  // ---------- all runs: menus and tables, by group ----------
  // order: the twelve methods level by level, boundary control (20 R boxes, then 100 R boxes), the other groups, other runs
  function tableGroups(list) {
    const of = key => list.filter(r => runGroup(r) === key).sort(byPaper), out = [], twelve = of('twelve'), boundary = of('boundary');
    for (const l of [...new Set(twelve.map(runLevel))].sort((a, b) => b - a)) out.push({ key: 'twelve', title: `Twelve methods, level ${l}`, runs: twelve.filter(r => runLevel(r) === l) });
    out.push({ key: 'boundary', title: 'Boundary control, 20 R boxes', runs: boundary.filter(r => runBox(r) === 20) });
    out.push({ key: 'boundary', title: 'Boundary control, 100 R boxes', runs: boundary.filter(r => runBox(r) === 100) });
    for (const g of RUN_GROUPS) if (g.key !== 'twelve' && g.key !== 'boundary') out.push({ key: g.key, title: g.title, runs: of(g.key) });
    out.push({ key: 'other', title: 'Other complete runs', runs: of('other') });
    return out.filter(g => g.runs.length);
  }
  function fillRunSelect(sel) {
    for (const g of tableGroups(runs)) {
      const og = document.createElement('optgroup');
      og.label = g.title;
      for (const r of g.runs) og.append(new Option(label(r), r.id));
      sel.append(og);
    }
  }
  function buildFilter() {
    const f = $('filter'), add = (v, t) => f.add(new Option(t, v));
    for (const g of RUN_GROUPS) if (runs.some(r => runGroup(r) === g.key)) add('group:' + g.key, g.title);
    if (runs.some(r => runGroup(r) === 'other')) add('group:other', 'Other complete runs');
    for (const c of [...new Set(runs.map(r => Number(r.chi)))].sort((a, b) => a - b)) add('chi:' + c, `χ ${c}`);
    const levels = [...new Set(runs.map(runLevel))].sort((a, b) => a - b);
    if (levels.length > 1) for (const l of levels) add('level:' + l, `Level ${l}`);
    if (runs.some(coolingOn)) add('cooling', 'Cooling on');
  }
  function keep(r, f) {
    if (f === 'all') return true;
    if (f === 'cooling') return coolingOn(r);
    const [k, v] = f.split(':');
    return k === 'group' ? runGroup(r) === v : k === 'chi' ? String(Number(r.chi)) === v : k === 'level' ? String(runLevel(r)) === v : true;
  }
  function rowHTML(r) {
    const n = r.frames.length, end = tEnd(r), name = esc(label(r));
    const flag = end < 4.995 ? `Ends at ${timeHTML(end)}` : /complete/i.test(String(r.status || 'complete')) ? '' : statusHTML(r);
    return `<tr data-id="${esc(r.id)}"><th scope="row">${esc(undash(runName(r)))}<span class="meta">${esc(runMeta(r))}${flag ? `. ${flag}.` : ''}</span></th>`
      + `<td class="faces">${esc(undash(runFaces(r)))}</td><td class="states">${n} to ${timeHTML(end)}</td>`
      + `<td class="open"><button type="button" data-show="${esc(r.id)}" aria-label="Show ${name}">Show</button>`
      + `<a href="${esc(filmHref(r))}" aria-label="Film of ${name}">Film</a>${with3D(r) ? `<a href="${esc(viewerHref(r))}" aria-label="3D view of ${name}">3D</a>` : ''}</td></tr>`;
  }
  function buildTables() {
    const f = $('filter').value, parts = [], told = new Set();
    for (const g of tableGroups(runs)) {
      const list = g.runs.filter(r => keep(r, f));
      if (!list.length) continue;
      parts.push(`<h3>${esc(g.title)}</h3>`);
      const about = told.has(g.key) ? '' : groupInfo(g.key).about;
      told.add(g.key);
      if (about) parts.push(`<p class="about">${esc(about)}</p>`);
      parts.push(`<div class="table-scroll"><table class="runs"><caption class="visually-hidden">${esc(g.title)}</caption>`
        + '<thead><tr><th scope="col">Run</th><th scope="col">Box faces</th><th scope="col">Saved states</th><th scope="col">Open</th></tr></thead>'
        + `<tbody>${list.map(rowHTML).join('')}</tbody></table></div>`);
    }
    $('tables').innerHTML = parts.length ? parts.join('') : '<p class="meta">No run matches this choice.</p>';
    markCurrent();
  }
  function show(id) {
    if (S.recording || !byId.has(id)) return;
    $('run').value = id;
    if ($('compare').value === id) $('compare').value = '';
    if (S.mode !== 'runs') setMode('runs');
    select();
    $('studio').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }

  // ---------- start ----------
  async function init() {
    fetch('data/smooth60.json?v=' + KEY).then(r => (r.ok ? r.json() : {})).then(m => { window.SMOOTH_60 = m; if (S.current) updateLinks(); }).catch(() => {});
    // which runs have 3D data: the keys of assets/recent3d/catalog.js (until it loads, every run is taken to have them)
    fetch('assets/recent3d/catalog.js?v=' + KEY).then(r => (r.ok ? r.text() : '')).then(t => {
      const ids = new Set([...String(t).matchAll(/"new_([^"]+)"\s*:\s*\{/g)].map(m => m[1]));
      if (!ids.size) return;
      has3D = ids;
      if (runs.length) { buildTables(); if (S.current) updateLinks(); }
    }).catch(() => {});
    try {
      const res = await fetch('assets/recent/catalog.json?v=' + KEY);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      catalog = await res.json();
      runs = (catalog.runs || []).filter(r => r && r.id && Array.isArray(r.frames) && r.frames.length && (!r.views || r.views.includes('edge')));
      if (!runs.length) throw new Error('no runs');
      runs.forEach(r => { completeRecord(r); byId.set(r.id, r); });
    } catch (e) {
      showError('The run list did not load. Please reload the page.');
      $('error').querySelector('button').onclick = () => location.reload();
      $('count').textContent = 'complete runs';
      $('tables').innerHTML = '<p class="meta">The run list did not load.</p>';
      return;
    }
    const q = new URL(location).searchParams;
    fillRunSelect($('run')); fillRunSelect($('compare'));
    buildFilter(); buildBar($('captionBar')); buildBar($('gridBar'));
    const done = runs.every(r => /complete/i.test(String(r.status || 'complete')) && tEnd(r) >= 4.995);
    $('count').textContent = `${runs.length} ${done ? 'complete runs' : 'runs'}`;
    $('modes').hidden = !anySet();
    const first = byId.get('enzo-1000') || tableGroups(runs)[0].runs[0];
    S.current = byId.get(q.get('run')) || first;
    S.comparison = byId.get(q.get('compare')) || null;
    $('run').value = S.current.id; $('compare').value = S.comparison ? S.comparison.id : '';
    if (['edge', 'face'].includes(q.get('view'))) S.view = q.get('view');
    S.gview = q.get('view') === 'both' ? 'both' : S.view;
    $('view').value = S.view;
    const lvl = Number(q.get('level')); if (Number.isInteger(lvl) && lvl > 0) S.level = lvl;
    const sq = SET_ALIAS[q.get('set')] || q.get('set'); if (sq && Object.prototype.hasOwnProperty.call(SETS, sq)) S.set = sq;
    buildSets();
    S.smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches; $('smoothTime').checked = S.smooth;
    const tq = q.get('t'), fq = q.get('frame');
    S.t = tq !== null && tq !== '' && isFinite(+tq) ? +tq : fq !== null && fq !== '' && isFinite(+fq) ? +fq * OLD_LINK_STEP : tEnd(S.current);
    const twelveFirst = ['twelve', 'grid'].includes(q.get('mode'));
    buildTables();

    $('run').onchange = select; $('compare').onchange = select;
    $('view').onchange = () => {
      const v = $('view').value;
      if (S.mode === 'twelve') { S.gview = v; if (v !== 'both') S.view = v; buildGrid(); } else { S.view = v; S.gview = v; }
      S.timeHTML = ''; refresh();
    };
    $('level').onchange = () => { S.level = Number($('level').value); buildGrid(); refresh(); };
    $('set').onchange = () => { S.set = $('set').value; setChoices(); buildGrid(); refresh(); };
    $('modeRuns').onclick = () => setMode('runs'); $('modeTwelve').onclick = () => setMode('twelve');
    $('smoothTime').onchange = () => { S.smooth = $('smoothTime').checked; requestDraw(); };
    $('labels').onchange = () => { S.labels = $('labels').checked; requestDraw(); };
    $('filter').onchange = buildTables;
    $('tables').addEventListener('click', e => { const b = e.target.closest('button[data-show]'); if (b) show(b.dataset.show); });
    $('play').onclick = toggle;
    $('prevFrame').onclick = () => step(-1); $('nextFrame').onclick = () => step(1);
    const slider = $('time');
    slider.addEventListener('pointerdown', () => { S.dragging = true; });
    const release = () => { if (!S.dragging) return; S.dragging = false; syncURL(); };
    slider.addEventListener('pointerup', release); slider.addEventListener('pointercancel', release); slider.addEventListener('change', release);
    slider.oninput = () => { if (S.playing) { S.playing = false; cancelAnimationFrame(S.raf); setPlayButton(); } S.t = Number(slider.value); requestDraw(); syncURL(); };
    $('picture').onclick = savePicture; $('record').onclick = record;
    $('full').onclick = () => {
      const p = document.fullscreenElement ? document.exitFullscreen() : $('screen').requestFullscreen ? $('screen').requestFullscreen() : Promise.reject(new Error('Full screen is not available here.'));
      p.catch(e => message(e.message));
    };
    $('shareView').onclick = async () => {
      clearTimeout(S.urlTimer);
      const u = new URL(location); u.searchParams.set('t', fmt(shown(refRun()).t)); history.replaceState(null, '', u);
      try { await navigator.clipboard.writeText(location.href); message('Link copied.'); } catch { message(location.href); }
    };
    document.addEventListener('keydown', e => {
      if (S.recording || e.altKey || e.ctrlKey || e.metaKey) return;
      const el = e.target, tag = el.tagName, slider = el === $('time');
      if (e.key === ' ' || e.code === 'Space') {
        if (!slider && /INPUT|SELECT|TEXTAREA|BUTTON|SUMMARY|^A$/.test(tag)) return;
        e.preventDefault(); toggle(); return;
      }
      if (/SELECT|TEXTAREA/.test(tag) || (tag === 'INPUT' && !slider && el.type !== 'checkbox')) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
      else if (e.key === 'Home') { e.preventDefault(); jump(false); }
      else if (e.key === 'End') { e.preventDefault(); jump(true); }
    });
    document.addEventListener('visibilitychange', () => { if (document.hidden && !S.recording) pause(); });
    document.addEventListener('fullscreenchange', () => { onResize(); });
    if ('ResizeObserver' in window) new ResizeObserver(onResize).observe($('screen'));
    addEventListener('resize', () => { measure(); onResize(); });
    measure(); onResize();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { measure(); onResize(); });
    setMode(twelveFirst ? 'twelve' : 'runs');
  }
  init();
})();
