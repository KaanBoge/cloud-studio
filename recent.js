'use strict';
// Compare page: projections of the saved states of every run, one run, two runs or the twelve methods at once.
// Time is the master state: every panel shows its own saved state nearest to the chosen time and prints that time.
(() => {
  const KEY = '20261122';
  const $ = id => document.getElementById(id);
  const canvas = $('scene'), ctx = canvas.getContext('2d');
  const CODE_ORDER = ['Athena++', 'AthenaPK', 'Athena 4.2', 'Enzo', 'Enzo-E', 'RAMSES', 'FLASH 4.8', 'Flash-X', 'Arepo', 'GIZMO MFM', 'GIZMO MFV', 'GADGET-4'];
  const VIEW_NAME = { edge: 'Edge-on', face: 'Face-on' };
  const SHEET = { edge: [256, 128], face: [128, 128] };
  const TICKS = [0.008, 0.05, 0.2, 1, 5];
  const FONT = '"Segoe UI", system-ui, -apple-system, Arial, sans-serif';
  const OLD_LINK_STEP = 0.5;   // links written before 2026-11-22 carry ?frame=N with states 0.5 t_cc apart
  const COMPACT_BELOW = 860; // picture width in CSS px under which names and colour bar move into the page text
  const MAGMA = [[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 253, 191]];

  let catalog = null, runs = [];
  const byId = new Map();
  const S = { mode: 'runs', view: 'edge', t: 0, level: 5, current: null, comparison: null, playing: false, recording: false, dragging: false,
    compact: false, smooth: true, labels: true, speedKey: '', raf: 0, last: 0, urlTimer: 0, tiles: [], timeHTML: '', observer: null };

  // ---------- text helpers ----------
  const undash = s => String(s ?? '').replace(/\s*[—–]\s*/g, ', ').replace(/\s+-{1,2}\s+/g, ', ').replace(/--/g, ', ');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = t => (Math.abs(t) < 0.005 ? 0 : t).toFixed(2);
  const timeHTML = t => `t = ${fmt(t)} t<sub>cc</sub>`;
  const timePlain = t => `t = ${fmt(t)} t_cc`;
  const slug = s => String(s).replace(/χ\s*/g, 'chi').replace(/\+/g, 'p').normalize('NFKD').replace(/[^\w.]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase();

  // ---------- what a run is ----------
  function levelOf(r) {
    if (Number.isInteger(r.level)) return r.level;
    if (r.n > 0) { const l = Math.round(Math.log2(r.n / 32)) + 3; if (l >= 1 && l <= 8) return l; }
    return 5;
  }
  const dims = l => { const x = 2 ** (l + 3), y = 2 ** (l + 2); return `${x} × ${y} × ${y}`; };
  function codeOf(r) {
    if (r.code) return undash(r.code);
    const first = String(r.label || r.id).split(' · ')[0];
    return undash(first.replace(/\s*χ\s*[\d.]+\s*$/, '').trim() || r.id);
  }
  // words after the code in an older label; internal names are dropped, resolution is given as a level
  const QUALIFIER = { sharp: null, historical: 'smooth velocity profile', 'periodic box': null };
  function qualifiers(r) {
    const out = [];
    for (const part of String(r.label || '').split(' · ').slice(1).map(s => s.trim()).filter(Boolean)) {
      const k = part.toLowerCase();
      if (/^n\s*\d+$/.test(k) || /^level\s*\d+$/.test(k) || /^χ\s*\d+$/.test(k)) continue;
      if (k in QUALIFIER) { if (QUALIFIER[k]) out.push(QUALIFIER[k]); continue; }
      if (r.boundary && /periodic|inflow|outflow/.test(k)) continue;
      out.push(undash(part));
    }
    if (r.group === 'boundary' && r.boundary) out.push(undash(r.boundary));
    return out;
  }
  const label = r => [codeOf(r), `χ ${r.chi}`, `level ${levelOf(r)}`, ...qualifiers(r)].join(' · ');
  const tileLabel = r => [codeOf(r), ...qualifiers(r)].join(' · ');
  const codeRank = r => { const i = CODE_ORDER.indexOf(codeOf(r)); return i < 0 ? 99 : i; };
  const codeSort = (a, b) => codeRank(a) - codeRank(b) || label(a).localeCompare(label(b));
  function statusHTML(r) {
    const s = String(r.status || '');
    if (/partial historical coverage/i.test(s)) return 'Ends at ' + timeHTML(tEnd(r));
    if (/accepted bounded result|completed? run/i.test(s)) return 'Complete run';
    if (/historical display/i.test(s)) return 'Earlier run';
    if (/legacy film/i.test(s)) return 'Earlier film';
    if (/historical image set/i.test(s)) return 'Earlier image set';
    return esc(undash(s));
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
  const posterURL = (r, v) => r.base ? r.base + `poster-${v}.jpg` : `assets/posters/${r.id}-${v}.jpg`;
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
    b.textContent = 'Retry'; b.onclick = retryFailed;
    el.replaceChildren(document.createTextNode(msg + ' '), b); el.hidden = false;
  }

  // ---------- canvas drawing ----------
  function text(g, s, x, y, size, color, align = 'left', weight = '') {
    g.font = `${weight} ${size}px ${FONT}`; g.fillStyle = color; g.textAlign = align; g.textBaseline = 'alphabetic'; g.fillText(s, x, y);
  }
  // text with subscripts: segs = [[text], [text, true], ...]
  function rich(g, segs, x, y, size, color, align = 'left', weight = '') {
    const big = `${weight} ${size}px ${FONT}`, small = `${weight} ${Math.round(size * 0.68)}px ${FONT}`;
    let w = 0;
    for (const [s, sub] of segs) { g.font = sub ? small : big; w += g.measureText(s).width; }
    let cx = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
    g.fillStyle = color; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    for (const [s, sub] of segs) { g.font = sub ? small : big; g.fillText(s, cx, sub ? y + size * 0.24 : y); cx += g.measureText(s).width; }
    return w;
  }
  const timeSegs = t => [[`t = ${fmt(t)} t`], ['cc', true]];
  function fitSize(g, s, maxW, size, min, weight = '') {
    for (let f = size; f >= min; f -= 1) { g.font = `${weight} ${f}px ${FONT}`; if (g.measureText(s).width <= maxW) return f; }
    return min;
  }
  function frame(g, r, v, st, x, y, w, h) {
    g.fillStyle = '#05070d'; g.fillRect(x, y, w, h);
    const e = sheet(r, v);
    if (!e.ready) { text(g, e.failed ? 'Pictures did not load' : 'Loading', x + w / 2, y + h / 2, Math.max(14, Math.round(h * 0.07)), '#7e8da5', 'center'); return false; }
    const [sw, sh] = SHEET[v];
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    g.drawImage(e.img, 0, st.i * sh, sw, sh, x, y, w, h);
    if (st.f > 0 && st.j !== st.i) { g.globalAlpha = st.f; g.drawImage(e.img, 0, st.j * sh, sw, sh, x, y, w, h); g.globalAlpha = 1; }
    return true;
  }
  function stamp(g, t, x, y, fs) { // time readout with a dark backing, for pictures without a text band
    g.font = `${fs}px ${FONT}`;
    const w = g.measureText(`t = ${fmt(t)} t`).width + g.measureText('cc').width * 0.72;
    g.fillStyle = 'rgba(5,7,13,.72)'; g.fillRect(x - fs * 0.3, y - fs * 1.05, w + fs * 0.6, fs * 1.5);
    rich(g, timeSegs(t), x, y, fs, '#f1f4fb');
  }
  function tickValues(a, b) { const out = []; for (let v = a; v <= b + 1e-9; v += 5) out.push(Math.round(v * 100) / 100); return out; }
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
    const v = S.view, [sw, sh] = SHEET[v], st = shown(r);
    const top = o.title + o.sub + 44, padL = o.labels ? o.axis * 4.6 : 16, padR = 24, padB = o.labels ? o.axis * 3.6 : 8;
    const aw = w - padL - padR, ah = h - top - padB, sc = Math.min(aw / sw, ah / sh), iw = sw * sc, ih = sh * sc;
    const ix = x + padL + (aw - iw) / 2, iy = y + top + (ah - ih) / 2;
    const name = label(r), titleMax = Math.max(iw, w - padL - padR), fs = fitSize(g, name, titleMax, o.title, Math.round(o.title * 0.6), '600');
    text(g, name, ix, iy - o.sub - 26, fs, '#f1f4fb', 'left', '600');
    rich(g, [[VIEW_NAME[v] + '  ·  '], ...timeSegs(st.t)], ix, iy - 14, o.sub, '#c9d2e0');
    frame(g, r, v, st, ix, iy, iw, ih);
    if (o.labels) axes(g, r, v, ix, iy, iw, ih, o.axis);
  }
  // full picture: the 1920 x 1080 frame that is saved and recorded, and shown on wide screens
  function renderRuns(g, W, H, labels) {
    g.fillStyle = '#070911'; g.fillRect(0, 0, W, H);
    const list = [S.current, S.comparison].filter(Boolean), bottom = labels ? 150 : 56;
    if (list.length === 2) {
      const o = { title: 30, sub: 24, axis: 21, labels };
      panel(g, list[0], 12, 16, W / 2 - 18, H - bottom - 16, o);
      panel(g, list[1], W / 2 + 6, 16, W / 2 - 18, H - bottom - 16, o);
    } else panel(g, list[0], 40, 16, W - 80, H - bottom - 16, { title: 36, sub: 28, axis: 24, labels });
    if (labels) colorbar(g, W / 2, H - 104, 720, 20, 22);
    footer(g, W, H);
  }
  // all methods of a level in one picture
  function bestGrid(n, W, H, aspect, labelH, gap) {
    let best = { cols: 1, rows: n, w: 0 };
    for (let cols = 1; cols <= n; cols++) {
      const rows = Math.ceil(n / cols), w = Math.min((W - gap * (cols - 1)) / cols, ((H - gap * (rows - 1)) / rows - labelH) * aspect);
      if (w > best.w + 0.5) best = { cols, rows, w };
    }
    return best;
  }
  function gridTitle() {
    const list = gridRuns(), chis = [...new Set(list.map(r => r.chi))], machs = [...new Set(list.map(r => r.mach))];
    return ['Twelve methods', chis.length === 1 ? `χ ${chis[0]}` : '', machs.length === 1 && machs[0] ? `Mach ${machs[0]}` : '', `level ${S.level}`].filter(Boolean).join(' · ');
  }
  function renderGrid(g, W, H, labels) {
    g.fillStyle = '#070911'; g.fillRect(0, 0, W, H);
    const list = gridRuns(), v = S.view, [sw, sh] = SHEET[v], bottom = labels ? 150 : 56, ref = refRun();
    text(g, gridTitle(), 40, 58, 36, '#f1f4fb', 'left', '600');
    rich(g, [[VIEW_NAME[v] + '  ·  '], ...timeSegs(shown(ref).t)], W - 40, 58, 32, '#c9d2e0', 'right');
    const top = 90, AW = W - 80, AH = H - top - bottom, lab = 34, gap = 28;
    const L = bestGrid(list.length, AW, AH, sw / sh, lab, gap), iw = L.w, ih = iw * sh / sw;
    const totalW = L.cols * iw + (L.cols - 1) * gap, totalH = L.rows * (ih + lab) + (L.rows - 1) * gap;
    const x0 = (W - totalW) / 2, y0 = top + (AH - totalH) / 2, fs = Math.max(16, Math.min(24, Math.round(iw / 15)));
    list.forEach((r, k) => {
      const x = x0 + (k % L.cols) * (iw + gap), y = y0 + Math.floor(k / L.cols) * (ih + lab + gap), st = shown(r);
      const tw = rich(g, timeSegs(st.t), x + iw, y + lab - 10, fs, '#c9d2e0', 'right');
      const name = tileLabel(r), nf = fitSize(g, name, iw - tw - 12, fs, 12, '600');
      text(g, name, x, y + lab - 10, nf, '#f1f4fb', 'left', '600');
      frame(g, r, v, st, x, y + lab, iw, ih);
    });
    if (labels) colorbar(g, W / 2, H - 104, 720, 20, 22);
    footer(g, W, H);
  }
  function setCanvas(W, H) { if (canvas.width !== W) canvas.width = W; if (canvas.height !== H) canvas.height = H; }
  // narrow screens: the picture fills the canvas, the time stays drawn in, names and colour bar go to the caption below
  function renderCompact() {
    const list = [S.current, S.comparison].filter(Boolean), v = S.view, [sw, sh] = SHEET[v];
    const k = v === 'edge' ? 5 : 7.5, cw = sw * k, ch = sh * k, gap = 24;
    const vertical = list.length === 2 && v === 'edge', cols = list.length === 2 && !vertical ? 2 : 1, rows = vertical ? 2 : 1;
    const W = cols * cw + (cols - 1) * gap, H = rows * ch + (rows - 1) * gap, fs = Math.round(Math.max(cw * 0.05, W * 0.04));
    setCanvas(W, H);
    ctx.fillStyle = '#070911'; ctx.fillRect(0, 0, W, H);
    list.forEach((r, n) => {
      const x = cols === 2 ? n * (cw + gap) : 0, y = rows === 2 ? n * (ch + gap) : 0, st = shown(r);
      frame(ctx, r, v, st, x, y, cw, ch);
      stamp(ctx, st.t, x + fs * 0.6, y + fs * 1.4, fs);
    });
  }
  function drawScene() {
    if (S.mode === 'twelve') { setCanvas(1920, 1080); renderGrid(ctx, 1920, 1080, S.labels); return; }
    if (S.compact && !S.recording) { renderCompact(); return; }
    setCanvas(1920, 1080); renderRuns(ctx, 1920, 1080, S.labels);
  }

  // ---------- twelve methods grid (small canvases, sheets load when a tile comes into view) ----------
  function gridRuns() {
    const seen = new Set();
    return runs.filter(r => r.group === 'twelve' && levelOf(r) === S.level).sort(codeSort)
      .filter(r => { const c = codeOf(r); if (seen.has(c)) return false; seen.add(c); return true; });
  }
  function buildGrid() {
    if (S.observer) S.observer.disconnect();
    const v = S.view, [sw, sh] = SHEET[v], holder = $('tiles');
    S.tiles = gridRuns().map(r => {
      const fig = document.createElement('button'), c = document.createElement('canvas'), cap = document.createElement('span');
      const name = document.createElement('span'), time = document.createElement('span');
      fig.className = 'tile'; fig.type = 'button'; c.width = sw * 2; c.height = sh * 2; c.setAttribute('aria-hidden', 'true');
      cap.className = 'tile-cap'; name.className = 'code'; name.textContent = tileLabel(r);
      time.className = 't';
      cap.append(name, time); fig.append(c, cap);
      fig.addEventListener('click', () => { if (!S.recording) { $('run').value = r.id; $('compare').value = ''; setMode('runs'); select(); } });
      fig.title = `Open ${label(r)}`; fig.setAttribute('aria-label', `Open ${label(r)}, ${VIEW_NAME[v].toLowerCase()}`);
      return { run: r, fig, canvas: c, ctx: c.getContext('2d'), time, visible: false, key: '', th: '' };
    });
    holder.replaceChildren(...S.tiles.map(t => t.fig));
    holder.classList.toggle('face', v === 'face');
    S.observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
      for (const en of entries) { const t = S.tiles.find(x => x.fig === en.target); if (t) { t.visible = en.isIntersecting; if (t.visible) { sheet(t.run, S.view); t.key = ''; } } }
      requestDraw();
    }, { rootMargin: '300px 0px' }) : null;
    if (S.observer) S.tiles.forEach(t => S.observer.observe(t.fig)); else S.tiles.forEach(t => { t.visible = true; });
    $('gridHead').textContent = gridTitle();
    layoutGrid();
  }
  function layoutGrid() {
    if (S.mode !== 'twelve' || !S.tiles.length) return;
    const holder = $('tiles'), wide = matchMedia('(min-width: 900px)').matches, aspect = S.view === 'edge' ? 2 : 1;
    if (wide || document.fullscreenElement) {
      const L = bestGrid(S.tiles.length, holder.clientWidth, holder.clientHeight, aspect, 24, 12);
      holder.style.setProperty('--cols', L.cols); holder.style.setProperty('--tile-w', Math.floor(L.w) + 'px');
    } else {
      holder.style.setProperty('--cols', S.view === 'edge' ? 2 : 3); holder.style.removeProperty('--tile-w');
    }
  }
  function drawGrid() {
    for (const tile of S.tiles) {
      const r = tile.run, e = sheets.get(sheetURL(r, S.view));
      if (!tile.visible && !(e && e.ready)) continue;
      const st = shown(r), key = `${st.i}|${st.j}|${st.f.toFixed(3)}|${e ? e.ready + '' + e.failed : 'new'}`;
      if (key !== tile.key) { tile.key = key; frame(tile.ctx, r, S.view, st, 0, 0, tile.canvas.width, tile.canvas.height); }
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
      const rows = [S.current, S.comparison].filter(Boolean).map(r => `<p><b>${esc(label(r))}</b><span>${VIEW_NAME[S.view]} · ${timeHTML(shown(r).t)}</span></p>`).join('');
      if ($('captionRows').innerHTML !== rows) $('captionRows').innerHTML = rows;
    }
  }
  function detailBlock(r, heading) {
    const n = r.frames.length, L = levelOf(r), tags = [statusHTML(r)];
    if (r.group === 'twelve') tags.push('One of the twelve methods');
    if (r.group === 'boundary') tags.push('Boundary control');
    if (r.boundary) tags.push(esc(undash(r.boundary).replace(/^./, c => c.toUpperCase())));
    if (r.cooling === 'tabular') tags.push('Cooling on');
    const note = cleanNote(r.note);
    return `${heading ? `<h3>${esc(label(r))}</h3>` : ''}<p class="meta">Mach ${esc(r.mach)} · level ${L} · ${dims(L)} · ${n} frames to ${timeHTML(tEnd(r))}</p>`
      + `<p class="tags">${tags.filter(Boolean).map(s => `<span>${s}</span>`).join('')}</p>${note ? `<p class="note">${esc(note).replace(/t_cc/g, 't<sub>cc</sub>')}</p>` : ''}`;
  }
  function updateDetails() {
    if (S.mode === 'twelve') {
      const list = gridRuns();
      $('title').textContent = gridTitle();
      $('detailBody').innerHTML = `<p class="note">The twelve methods of the paper: eight grid codes with an inflowing wind (Athena++, AthenaPK, Athena 4.2, Enzo, Enzo-E, RAMSES, FLASH 4.8, Flash-X), the moving mesh code Arepo in a box periodic along the wind, and GIZMO MFM, GIZMO MFV and GADGET-4 in a box periodic on all faces. Every tile shows its own saved state nearest to the chosen time.</p>`
        + `<p class="meta">On this page at level ${S.level}: ${list.map(r => esc(codeOf(r))).join(', ')}.</p><p class="note">Select a tile to open that run.</p>`;
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
    $('rotate3d').href = 'viewer.html?run=new_' + encodeURIComponent(r.id);
    $('rotate3d').hidden = S.mode === 'twelve';
  }
  function syncURL() {
    clearTimeout(S.urlTimer);
    S.urlTimer = setTimeout(() => {
      const u = new URL(location), p = u.searchParams;
      p.delete('frame');
      p.set('run', S.current.id);
      if (S.comparison && S.mode === 'runs') p.set('compare', S.comparison.id); else p.delete('compare');
      p.set('view', S.view);
      p.set('t', fmt(shown(refRun()).t));
      if (S.mode === 'twelve') { p.set('mode', 'twelve'); p.set('level', String(S.level)); } else { p.delete('mode'); p.delete('level'); }
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
  function setPlayButton() { $('play').textContent = S.playing ? 'Ⅱ Pause' : '▶ Play'; $('play').setAttribute('aria-label', S.playing ? 'Pause' : 'Play'); }
  function ready() { // pictures needed right now are loaded
    if (S.mode === 'twelve') return S.tiles.every(t => !t.visible || (sheets.get(sheetURL(t.run, S.view)) || {}).ready || (sheets.get(sheetURL(t.run, S.view)) || {}).failed);
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
  function select() {
    S.current = byId.get($('run').value) || S.current;
    S.comparison = byId.get($('compare').value) || null;
    for (const c of document.querySelectorAll('.card')) c.classList.toggle('selected', c.dataset.id === S.current.id);
    refresh();
  }
  function setMode(mode) {
    if (mode === 'twelve' && !runs.some(r => r.group === 'twelve')) mode = 'runs';
    pause();
    S.mode = mode;
    const twelve = mode === 'twelve';
    $('modeRuns').setAttribute('aria-pressed', String(!twelve)); $('modeTwelve').setAttribute('aria-pressed', String(twelve));
    document.querySelectorAll('.run-only').forEach(e => { e.hidden = twelve; });
    document.querySelectorAll('.twelve-only').forEach(e => { e.hidden = !twelve; });
    $('studio').classList.toggle('twelve', twelve);
    canvas.hidden = twelve; $('grid').hidden = !twelve; $('caption').hidden = twelve || !S.compact;
    if (twelve) buildGrid(); else if (S.observer) { S.observer.disconnect(); S.observer = null; }
    refresh();
  }
  function measure() { // keep the picture and the Play button inside one window height on wide screens
    const wide = matchMedia('(min-width: 900px)').matches, root = document.documentElement;
    if (!wide) { root.style.removeProperty('--chrome'); return; }
    const top = $('studio').getBoundingClientRect().top + scrollY, tr = document.querySelector('.transport').offsetHeight;
    const cap = $('caption').hidden ? 0 : $('caption').offsetHeight;
    root.style.setProperty('--chrome', Math.round(top + tr + cap + 22) + 'px');
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
    if (S.mode === 'twelve') return `cloud-studio_twelve-methods_level${S.level}_${S.view}_t${t}`;
    return `cloud-studio_${slug(label(S.current))}${S.comparison ? '_vs_' + slug(label(S.comparison)) : ''}_${S.view}_t${t}`;
  }
  const loadAll = () => Promise.all(onScreen().map(r => sheet(r, S.view).promise));
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
        message(`Recording ${VIEW_NAME[S.view].toLowerCase()} from ${timePlain(lo)} to ${timePlain(hi)}`);
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

  // ---------- run list and cards ----------
  function groups(list) {
    const twelve = list.filter(r => r.group === 'twelve'), boundary = list.filter(r => r.group === 'boundary');
    const other = list.filter(r => r.group !== 'twelve' && r.group !== 'boundary'), out = [];
    for (const l of [...new Set(twelve.map(levelOf))].sort((a, b) => b - a)) out.push({ label: `Twelve methods · level ${l}`, runs: twelve.filter(r => levelOf(r) === l).sort(codeSort) });
    if (boundary.length) out.push({ label: 'Boundary control', runs: boundary.slice().sort((a, b) => levelOf(b) - levelOf(a) || label(a).localeCompare(label(b))) });
    if (other.length) out.push({ label: out.length ? 'Other complete runs' : '', runs: other });
    return out;
  }
  function fillRunSelect(sel) {
    for (const g of groups(runs)) {
      const parent = g.label ? Object.assign(document.createElement('optgroup'), { label: g.label }) : sel;
      for (const r of g.runs) parent.append(new Option(label(r), r.id));
      if (parent !== sel) sel.append(parent);
    }
  }
  function cardText(r) { return `${r.frames.length} frames to ${timeHTML(tEnd(r))}${r.group === 'twelve' ? ' · one of the twelve methods' : ''}`; }
  function buildFilter() {
    const f = $('filter'), add = (v, t) => f.add(new Option(t, v));
    if (runs.some(r => r.group === 'twelve')) add('twelve', 'Twelve methods');
    if (runs.some(r => r.group === 'boundary')) add('boundary', 'Boundary control');
    for (const c of [...new Set(runs.map(r => r.chi))].sort((a, b) => b - a)) add('chi:' + c, `χ ${c}`);
    const levels = [...new Set(runs.map(levelOf))].sort((a, b) => b - a);
    if (levels.length > 1) for (const l of levels) add('level:' + l, `Level ${l}`);
    if (runs.some(r => r.cooling === 'tabular')) add('cooling', 'Cooling on');
  }
  function keep(r, f) {
    if (f === 'all') return true;
    if (f === 'twelve' || f === 'boundary') return r.group === f;
    if (f === 'cooling') return r.cooling === 'tabular';
    const [k, v] = f.split(':');
    return k === 'chi' ? String(r.chi) === v : k === 'level' ? String(levelOf(r)) === v : true;
  }
  function buildCards() {
    const f = $('filter').value, holder = $('cards');
    holder.replaceChildren();
    for (const g of groups(runs)) for (const r of g.runs) {
      if (!keep(r, f)) continue;
      const b = document.createElement('button');
      b.className = 'card' + (S.current && r.id === S.current.id ? ' selected' : '');
      b.dataset.id = r.id; b.setAttribute('aria-label', 'Show ' + label(r));
      const thumb = document.createElement('div'), img = document.createElement('img'), stampEl = document.createElement('span');
      thumb.className = 'thumb'; img.loading = 'lazy'; img.decoding = 'async'; img.width = 512; img.height = 256;
      img.alt = `${label(r)}, edge-on, ${timePlain(tEnd(r))}`; img.src = posterURL(r, 'edge');
      img.onerror = () => { img.remove(); stampEl.remove(); thumb.classList.add('missing'); thumb.textContent = 'Preview unavailable'; };
      stampEl.className = 'stamp'; stampEl.innerHTML = timeHTML(tEnd(r));
      thumb.append(img, stampEl);
      const info = document.createElement('div'), strong = document.createElement('strong'), small = document.createElement('small');
      strong.textContent = label(r); small.innerHTML = cardText(r);
      info.append(strong, small); b.append(thumb, info);
      b.onclick = () => {
        if (S.recording) return;
        $('run').value = r.id;
        if (S.mode !== 'runs') setMode('runs');
        select();
        $('studio').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
      };
      holder.append(b);
    }
  }
  function buildLevels() {
    const levels = [...new Set(runs.filter(r => r.group === 'twelve').map(levelOf))].sort((a, b) => b - a);
    $('level').replaceChildren(...levels.map(l => new Option(`Level ${l} · ${dims(l)}`, String(l))));
    if (levels.length) S.level = levels.includes(S.level) ? S.level : levels[0];
    $('level').value = String(S.level);
  }

  // ---------- start ----------
  async function init() {
    fetch('data/smooth60.json?v=' + KEY).then(r => (r.ok ? r.json() : {})).then(m => { window.SMOOTH_60 = m; if (S.current) updateLinks(); }).catch(() => {});
    try {
      const res = await fetch('assets/recent/catalog.json?v=' + KEY);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      catalog = await res.json();
      runs = (catalog.runs || []).filter(r => r && r.id && Array.isArray(r.frames) && r.frames.length && (!r.views || r.views.includes('edge')));
      if (!runs.length) throw new Error('no runs');
      runs.forEach(r => byId.set(r.id, r));
    } catch (e) {
      showError('The run list did not load. Please reload the page.');
      $('error').querySelector('button').onclick = () => location.reload();
      $('count').textContent = 'Run list unavailable';
      return;
    }
    const q = new URL(location).searchParams;
    fillRunSelect($('run')); fillRunSelect($('compare'));
    buildFilter(); buildBar($('captionBar')); buildBar($('gridBar'));
    $('count').textContent = `${runs.length} runs`;
    $('modes').hidden = !runs.some(r => r.group === 'twelve');
    const first = runs.find(r => r.id === 'enzo-1000') || groups(runs)[0].runs[0];
    S.current = byId.get(q.get('run')) || first;
    S.comparison = byId.get(q.get('compare')) || null;
    $('run').value = S.current.id; $('compare').value = S.comparison ? S.comparison.id : '';
    if (['edge', 'face'].includes(q.get('view'))) S.view = q.get('view');
    $('view').value = S.view;
    const lvl = Number(q.get('level')); if (Number.isInteger(lvl)) S.level = lvl;
    buildLevels();
    S.smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches; $('smoothTime').checked = S.smooth;
    const tq = q.get('t'), fq = q.get('frame');
    S.t = tq !== null && tq !== '' && isFinite(+tq) ? +tq : fq !== null && fq !== '' && isFinite(+fq) ? +fq * OLD_LINK_STEP : tEnd(S.current);
    const twelveFirst = ['twelve', 'grid'].includes(q.get('mode'));
    buildCards();

    $('run').onchange = select; $('compare').onchange = select;
    $('view').onchange = () => { S.view = $('view').value; if (S.mode === 'twelve') buildGrid(); S.timeHTML = ''; refresh(); };
    $('level').onchange = () => { S.level = Number($('level').value); buildGrid(); refresh(); };
    $('modeRuns').onclick = () => setMode('runs'); $('modeTwelve').onclick = () => setMode('twelve');
    $('smoothTime').onchange = () => { S.smooth = $('smoothTime').checked; requestDraw(); };
    $('labels').onchange = () => { S.labels = $('labels').checked; requestDraw(); };
    $('filter').onchange = buildCards;
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
      try { await navigator.clipboard.writeText(location.href); message('View link copied.'); } catch { message(location.href); }
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
