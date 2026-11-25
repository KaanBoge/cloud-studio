'use strict';
// Runs page. The complete runs are listed by group from assets/recent/catalog.json, the records the Compare page and
// the 3D viewer name their runs from, with Figure 1 of the twelve methods. The library lists every entry of
// data/studio-catalog.json: complete runs, earlier runs in the 3D viewer, films, image sets and test problems; it opens
// on the earlier entries, since the complete runs are already in the tables above it.
const $ = id => document.getElementById(id);
const params = new URL(location).searchParams;

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
function runName(r) {           // name under a group heading: the code, then what the run changes
  let v = runVariant(r);
  if (runGroup(r) === 'smooth') v = v.replace(/,?\s*smooth velocity profile/i, '').replace(/^,\s*/, '');
  return v ? runCode(r) + ', ' + v : runCode(r);
}
// name in a run table row: words that the Box faces column already gives are left out
function runRowName(r) {
  const faces = runFaces(r).toLowerCase().split(/,\s*/), [code, ...rest] = runName(r).split(', ');
  return [code, ...rest.filter(s => !faces.includes(s.toLowerCase()))].join(', ');
}
// full name where neither a group heading nor a Box faces column stands next to it (library, film player, menus)
const runTitle = r => { const v = runVariant(r); return v ? runCode(r) + ', ' + v : runCode(r); };
const runMeta = r => `χ ${r.chi}, level ${runLevel(r)}`;
// box faces; a 100 R box is named once, also when the catalog text already says so
const runFaces = r => { const b = String(r.boundary || ''); return runBox(r) === 100 && !/100 ?R\b/i.test(b) ? (b ? b + ', ' : '') + '100 R long box' : b; };
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

const METHOD_ORDER = ['Athena++', 'AthenaPK', 'Athena 4.2', 'Enzo', 'Enzo-E', 'RAMSES', 'FLASH 4.8', 'Flash-X', 'Arepo', 'GIZMO MFM', 'GIZMO MFV', 'GADGET-4'];
const OTHER_GROUP = { key: 'other', title: 'Other complete runs', about: 'Complete runs outside the groups above.' };
// side by side sets of the Compare page for the groups below the twelve methods and the boundary control
const SIDE_BY_SIDE = {
  solver: ['solver', 'Side by side, standard and changed setting'],
  smooth: ['smooth', 'Side by side, sharp velocity edge and smooth velocity profile'],
  contrast: ['contrast', 'Side by side, χ 10 and χ 1000'],
  apk: ['cooling', 'Side by side, cooling off and cooling on'],
  level6: ['level6', 'Side by side, level 5 and level 6'],
};
const CBAR = '<div class="cbar" aria-hidden="true"><span class="cbar-strip"></span><span class="cbar-ticks"><span style="left:0%">0.008</span><span style="left:28.47%">0.05</span><span style="left:50%">0.2</span><span style="left:75%">1</span><span style="left:100%">5</span></span></div>\n<p class="meta">Column density Σ / (ρ<sub>c,0</sub> R), logarithmic scale from 0.008 to 5, the same in every picture and film.</p>';
const PHYSICS = { none: 'Nonradiative', tabular: 'Cooling on', mhd: 'Magnetized', unknown: 'Not specified' };
const KIND_WORDS = { recent: 'complete run', '3d': 'earlier run 3d surfaces', film: 'earlier film', image: 'image set pictures', test: 'test problem pictures' };
const LOCAL = ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(location.hostname);
const FIRST_FRAME = '#t=0.001';                      // the player shows the first frame of the film (t = 0.00) before it plays
const DEFAULTS = { kind: 'earlier', q: '', code: 'all', chi: 'all', level: 'all', physics: 'all', sort: 'featured' };
const FILTERS = ['code', 'chi', 'level', 'physics', 'sort'];
const PAGE = 24;
const CONTENTS_TAIL = [...$('contents').children];
const state = Object.fromEntries(Object.entries(DEFAULTS).map(([k, v]) => [k, params.get(k) || v]));
let entries = [], runs = [], shown = 0, activeFilm = null, opener = null, triedRemote = false;
let twelveRuns = [], twelveLevel = 5;
const libById = new Map(), runByKey = new Map();
let saved = new Set();
try { saved = new Set(JSON.parse(localStorage.getItem('cloud-studio-saved') || '[]')); } catch { /* storage blocked */ }

// ------------------------------------------------------------------ small helpers
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
// Append text to a node, writing every "t_cc" as t with a subscript cc.
function rich(node, text) {
  String(text ?? '').split('t_cc').forEach((part, i) => { if (i) { node.append('t'); node.append(el('sub', '', 'cc')); } if (part) node.append(part); });
  return node;
}
const setRich = (node, text) => { node.replaceChildren(); return rich(node, text); };
const fmtT = t => (Math.round(Number(t) * 100) / 100).toFixed(2);
const timeText = t => `t = ${fmtT(t)} t_cc`;      // never broken across lines
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const methodIndex = code => { const i = METHOD_ORDER.indexOf(code); return i < 0 ? METHOD_ORDER.length : i; };
const slug = s => String(s).toLowerCase().replace(/χ/g, 'chi').replace(/[^a-z0-9+]+/g, '-').replace(/^-|-$/g, '');
function link(text, href) { const a = el('a', '', text); a.href = href; return a; }
function storeSaved() { try { localStorage.setItem('cloud-studio-saved', JSON.stringify([...saved])); } catch { /* storage blocked */ } }

// ------------------------------------------------------------------ complete runs
// the time stored with the last saved state, and the number of saved states
const runEnd = r => { const f = r.frames || [], t = f.length ? f[f.length - 1].time : (r.times || [])[(r.times || []).length - 1]; return t == null || !Number.isFinite(Number(t)) ? null : Number(t); };
const runStart = r => { const f = r.frames || []; return f.length && Number.isFinite(Number(f[0].time)) ? Number(f[0].time) : 0; };
const runStates = r => (r.frames || r.times || []).length;
const libFor = r => libById.get('new_' + runKey(r)) || null;
// paper order of the codes, then level from high to low, then χ, then name
function byPaperOrder(a, b) {
  const ca = runCode(a), cb = runCode(b);
  return methodIndex(ca) - methodIndex(cb) || (ca === cb ? 0 : ca.localeCompare(cb)) || runLevel(b) - runLevel(a) ||
    Number(a.chi) - Number(b.chi) || runTitle(a).localeCompare(runTitle(b)) || runFaces(a).localeCompare(runFaces(b));
}
// films of a run: the library entry, or the two films every run folder holds when the library does not list the run yet
function filmFor(r) {
  const lib = libFor(r);
  if (lib && lib.variants) return lib;
  if (!r.base) return null;
  const end = runEnd(r);
  return { id: 'new_' + runKey(r), run: runKey(r), label: r.label, kind: 'recent', poster: r.base + 'poster-edge.jpg',
    filmNote: `All ${runStates(r)} saved states from ${timeText(runStart(r))} to ${end == null ? 'the last saved state' : timeText(end)}, played at 60 fps with crossfades between neighbouring states.`,
    variants: [{ src: r.base + 'film-edge.mp4', label: 'Edge on, 60 fps', poster: r.base + 'poster-edge.jpg' },
      { src: r.base + 'film-face.mp4', label: 'Face on, 60 fps', poster: r.base + 'poster-face.jpg' }] };
}
function findFilm(id) {
  const lib = libById.get(id);
  if (lib && lib.variants) return lib;
  const run = runByKey.get(String(id || '').replace(/^new_/, ''));
  return run ? filmFor(run) : null;
}
// Names in the library and the dialogs follow the run tables: a name, then "χ 100, level 5" as a second part.
// A complete run is named from its record in the recent catalog (runTitle, runMeta); other entries split their
// catalog label "Code · what · χ 10 · level 5" the same way.
const META_PART = /^(χ|chi)\s*[\d.]+$|^(about )?level\s*\d+$/i;
const labelParts = r => String(r.label || '').split(' · ').map(s => s.trim()).filter(Boolean);
const runOf = r => r._run || (r.kind === 'recent' ? runByKey.get(runKey(r)) || null : null);
function entryName(r) {
  const run = runOf(r);
  return run ? runTitle(run) : labelParts(r).filter(s => !META_PART.test(s)).join(', ') || String(r.label || '');
}
function entryMeta(r) { const run = runOf(r); return run ? runMeta(run) : labelParts(r).filter(s => META_PART.test(s)).join(', '); }
const entryText = r => [entryName(r), entryMeta(r)].filter(Boolean).join(', ');
function titleInto(node, r) { node.replaceChildren(entryName(r)); const m = entryMeta(r); if (m) node.append(el('span', 'meta', m)); }
const isCoolingOn = r => /cooling on/i.test(String(r.label || '')) || (!!r.cooling && !/^(none|off|no)$/i.test(String(r.cooling)));
function pickLevel(list, preferred) {
  const levels = [...new Set(list.map(runLevel))].sort((a, b) => a - b);
  return levels.includes(preferred) ? preferred : levels.includes(5) ? 5 : levels[levels.length - 1];
}
const sideHref = (set, level) => `recent.html?mode=twelve&set=${set}&view=both` + (level ? '&level=' + level : '');

function runRow(r) {
  const tr = el('tr'), th = el('th');
  th.scope = 'row';
  th.append(runRowName(r), el('span', 'meta', runMeta(r)));
  const end = runEnd(r), status = r.status && r.status !== 'Complete run' ? String(r.status) : '';
  // "Ends at" only where the status does not already say where the run stops ("Stops at 3.55 t_cc, where the solver failed")
  const early = end != null && end < 4.995 && !/\b(stops|ends) at\b/i.test(status);
  if (status || early) th.append(rich(el('span', 'meta'), [status ? status + '.' : '', early ? `Ends at ${timeText(end)}.` : ''].filter(Boolean).join(' ')));
  const faces = el('td', 'faces', runFaces(r) || 'not recorded');
  const states = rich(el('td', 'states'), end == null ? String(runStates(r)) : `${runStates(r)} to ${timeText(end)}`);
  const open = el('td', 'open'), film = filmFor(r), lib = libFor(r);
  if (film) { const a = link('Film', filmHref(r)); a.onclick = e => { e.preventDefault(); openFilm(film, a); }; open.append(a); }
  if (lib && lib.viewer) open.append(link('3D', viewerHref(r)));
  open.append(link('Compare', compareHref(r, runTwin(r, runs))));
  tr.append(th, faces, states, open);
  return tr;
}
function runTable(list, caption) {
  const wrap = el('div', 'table-scroll group-table'), table = el('table', 'runs'), head = el('thead'), hr = el('tr'), body = el('tbody');
  for (const h of ['Run', 'Box faces', 'Saved states', 'Open']) { const th = el('th', '', h); th.scope = 'col'; hr.append(th); }
  head.append(hr); body.append(...list.map(runRow));
  table.append(el('caption', 'visually-hidden', caption), head, body); wrap.append(table);
  return wrap;
}
function colourBar() { const t = document.createElement('template'); t.innerHTML = CBAR; return t.content; }
function linksRow(pairs) { const p = el('p', 'links-row'); for (const [text, href] of pairs) p.append(link(text, href)); return p; }

// Figure 1: the edge on picture of the last saved state of each method at the chosen level
function figure1(list) {
  const fig = el('figure', 'fig'), ul = el('ul', 'fig-grid');
  for (const r of list) {
    const li = el('li'), a = link('', filmHref(r)), end = runEnd(r), film = filmFor(r), name = runCode(r);
    const src = r.base ? r.base + 'poster-edge.jpg' : (libFor(r) || {}).poster;
    if (src) {
      const im = el('img'); im.src = src; im.width = 768; im.height = 384; im.loading = 'lazy'; im.decoding = 'async';
      im.alt = `${name}, ${runMeta(r)}, edge on column density` + (end == null ? '' : ` at t = ${fmtT(end)} cloud crushing times`);
      im.onerror = () => im.replaceWith(el('span', 'no-pic', 'Picture not available'));
      a.append(im);
    } else a.append(el('span', 'no-pic', 'Picture not available'));
    const label = el('span', 'fig-label');
    label.append(el('span', 'fig-name', name));
    if (end != null) label.append(rich(el('span', 'fig-t'), timeText(end)));
    a.append(label);
    if (film) a.onclick = e => { e.preventDefault(); openFilm(film, a); };
    li.append(a); ul.append(li);
  }
  const which = list.length === 12 ? 'the twelve methods' : `the ${list.length} methods with a complete run`;
  fig.append(ul, el('figcaption', '', `Figure 1. Column density of ${which} at level ${twelveLevel}, edge on, at the last saved state of each run. The wind blows from left to right; the box is 20 cloud radii long. Each picture opens the film of that run.`));
  return fig;
}
function drawTwelve() {
  document.querySelectorAll('#twelve .choice button').forEach(b => b.setAttribute('aria-pressed', Number(b.dataset.level) === twelveLevel));
  const list = twelveRuns.filter(r => runLevel(r) === twelveLevel);
  $('twelveLevel').replaceChildren(figure1(list), colourBar(),
    linksRow([['Side by side, edge on and face on, as in the paper', sideHref('twelve', twelveLevel)]]),
    runTable(list, `Twelve methods at level ${twelveLevel}`));
}
function buildTwelve(sec, list) {
  twelveRuns = list;
  const levels = [...new Set(list.map(runLevel))].sort((a, b) => a - b), standard = pickLevel(list, 5);
  twelveLevel = pickLevel(list, Number(params.get('twelve')));
  sec.append(el('p', 'lede', 'Level 3, 4 and 5 are grids of 64 × 32 × 32, 128 × 64 × 64 and 256 × 128 × 128 cells over a box 20 × 10 × 10 cloud radii; the particle and moving mesh runs are binned onto the same grids for the pictures.'));
  if (levels.length > 1) {
    const choice = el('div', 'choice');
    choice.setAttribute('role', 'group'); choice.setAttribute('aria-label', 'Level of the twelve methods');
    for (const level of levels) {
      const b = el('button', '', 'Level ' + level); b.type = 'button'; b.dataset.level = level;
      b.onclick = () => {
        twelveLevel = level; drawTwelve();
        const u = new URL(location);
        if (level === standard) u.searchParams.delete('twelve'); else u.searchParams.set('twelve', level);
        history.replaceState(null, '', u);
      };
      choice.append(b);
    }
    sec.append(choice);
  }
  const holder = el('div'); holder.id = 'twelveLevel'; sec.append(holder);
  drawTwelve();
}
function buildBoundary(sec, list) {
  const links = [];
  for (const [box, title] of [[20, '20 R boxes'], [100, '100 R boxes']]) {
    const part = list.filter(r => runBox(r) === box);
    if (!part.length) continue;
    sec.append(el('h3', '', title), runTable(part, 'Boundary control, ' + title));
    links.push(['Side by side, ' + title, sideHref('boundary' + box, pickLevel(part, 5))]);
  }
  if (links.length) sec.append(linksRow(links));
}
function buildGroup(sec, g, list) {
  sec.append(runTable(list, g.title));
  const set = SIDE_BY_SIDE[g.key];
  if (!set) return;
  const has = g.key === 'apk' ? list.some(isCoolingOn)
    : g.key === 'contrast' ? list.some(r => Number(r.chi) === 10) && list.some(r => Number(r.chi) === 1000)
    : list.some(r => runTwin(r, runs));
  if (has) sec.append(linksRow([[set[1], sideHref(set[0])]]));
}
function renderGroups() {
  const by = new Map([...RUN_GROUPS, OTHER_GROUP].map(g => [g.key, []])), box = $('groups'), items = [];
  for (const r of runs) (by.get(runGroup(r)) || by.get('other')).push(r);
  box.replaceChildren();
  for (const g of [...RUN_GROUPS, OTHER_GROUP]) {
    const list = by.get(g.key).sort(byPaperOrder);
    if (!list.length) continue;                       // a group without runs is not shown
    const sec = el('section'), h = el('h2', '', g.title);
    sec.id = g.key; h.id = g.key + 'Title'; sec.setAttribute('aria-labelledby', h.id);
    // the sentence on the 100 R boxes only while such runs are listed
    const about = g.key === 'boundary' && !list.some(r => runBox(r) === 100) ? g.about.replace(/\s*The 100 R boxes [^.]*\.$/, '') : g.about;
    sec.append(h, el('p', 'lede', about));
    box.append(sec);
    if (g.key === 'twelve') buildTwelve(sec, list);
    else if (g.key === 'boundary') buildBoundary(sec, list);
    else buildGroup(sec, g, list);
    const li = el('li'); li.append(link(g.title, '#' + g.key), el('span', 'meta', `(${list.length})`)); items.push(li);
  }
  if (!items.length) box.append(el('p', 'meta', 'No complete runs are listed yet.'));
  $('contents').replaceChildren(...items, ...CONTENTS_TAIL);
}

// ------------------------------------------------------------------ library: search and order
const groupRank = key => { const i = RUN_GROUPS.findIndex(g => g.key === key); return i < 0 ? RUN_GROUPS.length : i; };
function prepare(r, i) {
  const run = r.kind === 'recent' ? runByKey.get(runKey(r)) || null : null;
  return { ...r, _i: i, _run: run, _rank: r.kind === 'recent' ? groupRank(runGroup(run || r)) : r.variants ? 20 : 21 };
}
// Words a visitor may type to find an entry; every word of the query must start a word of the entry.
function words(r) {
  if (r._words) return r._words;
  const g = r.kind === 'recent' ? RUN_GROUPS.find(x => x.key === runGroup(r._run || r)) : null;
  const text = [entryName(r), r.label, r.code, r.note, r.status, KIND_WORDS[r.kind], PHYSICS[r.physics], r.boundary,
    r.chi ? `chi ${r.chi} χ${r.chi} chi${r.chi}` : '', r.level != null ? `level ${r.level} l${r.level}` : r.levelText,
    g ? g.title : '', r.variants ? 'film films' : '', r.viewer ? '3d' : '', r.images ? 'images' : ''].filter(Boolean).join(' ').toLowerCase();
  return (r._words = text.split(/[\s·,;:()/]+/).map(w => w.replace(/[.]+$/, '')).filter(Boolean));
}
function queryMatches(r, q) {
  const terms = q.toLowerCase().replace(/·/g, ' ').split(/\s+/).filter(Boolean);
  if (!terms.length) return true;
  const ws = words(r);
  return terms.every(t => /^\d+(\.\d+)?$/.test(t) ? ws.includes(t) : ws.some(w => w.startsWith(t)));
}
function kindMatches(r) {
  switch (state.kind) {
    case 'earlier': return r.kind !== 'recent' && r.kind !== 'test';
    case 'all': return r.kind !== 'test';
    case '3d': return !!r.viewer;
    case 'film': return !!r.variants;
    case 'saved': return saved.has(r.id);
    default: return r.kind === state.kind;
  }
}
const matches = r => kindMatches(r) && queryMatches(r, state.q) && ['code', 'chi', 'level', 'physics'].every(k => state[k] === 'all' || String(r[k]) === state[k]);
// Paper order: the complete runs by group as above, then entries with films, then the rest.
function sortRows(rows) {
  if (state.sort === 'name') return rows.sort((a, b) => entryText(a).localeCompare(entryText(b)) || a._i - b._i);
  if (state.sort === 'resolution') return rows.sort((a, b) => (b.level ?? 0) - (a.level ?? 0) || a._i - b._i);
  return rows.sort((a, b) => a._rank - b._rank || (a._rank < 20 ? byPaperOrder(a._run || a, b._run || b) : 0) || a._i - b._i);
}

// ------------------------------------------------------------------ library: entries
// "χ 100, level 5, 101 saved states to t = 5.00 t_cc." for a complete run, "χ 10, level 4, earlier film, 6 versions." and so on
function metaLine(r) {
  let s, picture = '';
  if (r.kind === 'recent') {
    const n = r._run ? runStates(r._run) : r.frames, end = r._run ? runEnd(r._run) : r.end;
    s = (n ? `${n} saved states` : 'complete run') + (end != null ? ` to ${timeText(end)}` : '');
    // the picture is the last saved state; its time is named only where it differs from the end time
    if (r.poster && r.posterTime != null && (end == null || Math.abs(Number(r.posterTime) - end) > 0.005)) picture = ` Picture: edge on at ${timeText(r.posterTime)}.`;
  } else if (r.kind === '3d') {
    s = 'earlier run in the 3D viewer' + (r.frames ? `, ${r.frames} saved states` : '') + (/^Ends at/.test(r.status || '') ? ', e' + r.status.slice(1) : '');
  } else if (r.kind === 'film') s = `earlier film, ${plural(r.variants.length, 'version', 'versions')}`;
  else if (r.kind === 'image') s = `image set, ${plural(r.images.length, 'picture', 'pictures')}`;
  else if (r.kind === 'test') s = `test problem, ${plural((r.images || []).length, 'picture', 'pictures')}`;
  else s = r.status ? r.status.charAt(0).toLowerCase() + r.status.slice(1) : '';
  const line = [entryMeta(r), s].filter(Boolean).join(', ');          // χ stays lower case
  return (line ? (/^[a-z]/.test(line) ? line[0].toUpperCase() + line.slice(1) : line) + '.' : '') + picture + (r.physics === 'tabular' ? ' Cooling on.' : '');
}
function row(r) {
  const li = el('li', 'lib-item'), name = entryName(r), links = el('div', 'lib-links');
  let first = null;
  if (r.variants) { const a = link('Film', 'index.html?film=' + encodeURIComponent(r.id)); a.onclick = e => { e.preventDefault(); openFilm(r, a); }; links.append(a); first = a; }
  if (r.viewer) { const a = link('3D', r.viewer); links.append(a); first = first || a; }
  if (r.images) { const a = link(`Images (${r.images.length})`, r.projection || 'archive.html#gallery'); a.onclick = e => { e.preventDefault(); openImages(r, a); }; links.append(a); first = first || a; }
  else if (r._run) links.append(link('Compare', compareHref(r._run, runTwin(r._run, runs))));
  else if (/^recent\.html/.test(r.projection || '')) links.append(link('Compare', r.projection));
  const save = el('button'); save.type = 'button'; save.setAttribute('aria-label', 'Save ' + entryText(r));
  const paint = () => { const on = saved.has(r.id); save.textContent = on ? 'Saved' : 'Save'; save.setAttribute('aria-pressed', on); };
  save.onclick = () => { saved.has(r.id) ? saved.delete(r.id) : saved.add(r.id); storeSaved(); if (state.kind === 'saved') render(); else paint(); };
  paint(); links.append(save);
  // the picture repeats the first action of the entry for pointers; keyboards and screen readers use the text links
  const thumb = el(first ? 'a' : 'span', 'thumb');
  if (first) {
    thumb.href = first.href; thumb.tabIndex = -1; thumb.setAttribute('aria-hidden', 'true');
    thumb.onclick = e => { if (first.onclick) { e.preventDefault(); first.click(); } };
  }
  if (r.poster) {
    const im = el('img'); im.src = r.poster; im.alt = ''; im.width = 160; im.height = 80; im.loading = 'lazy'; im.decoding = 'async';
    im.onerror = () => im.replaceWith(el('span', 'no-pic', 'No picture'));
    thumb.append(im);
  } else thumb.append(el('span', 'no-pic', r.viewer ? '3D surfaces only' : 'No picture'));
  const body = el('div', 'lib-body');
  body.append(el('h3', '', name), rich(el('p', 'meta'), metaLine(r)), links);
  li.append(thumb, body);
  return li;
}
function render() {
  const rows = sortRows(entries.filter(matches));
  if (!shown) shown = PAGE;
  $('libList').replaceChildren(...rows.slice(0, shown).map(row));
  $('resultCount').textContent = plural(rows.length, 'entry', 'entries') + (rows.length > shown ? `, showing ${shown}` : '');
  const emptySaved = state.kind === 'saved' && saved.size === 0;
  $('empty').hidden = rows.length > 0;
  $('emptyTitle').textContent = emptySaved ? 'Nothing saved yet' : 'No matches';
  $('emptyText').textContent = emptySaved ? 'Use Save on any entry to keep it here. Saved entries stay in this browser.' : 'Try another code, or clear the filters to see the whole library.';
  $('emptyReset').textContent = emptySaved ? 'Show the whole library' : 'Clear filters';
  $('more').hidden = rows.length <= shown;
  document.querySelectorAll('[data-kind]').forEach(b => b.setAttribute('aria-pressed', b.dataset.kind === state.kind));
  persist();
}
function persist() {
  const u = new URL(location);
  for (const [k, v] of Object.entries(state)) { if (v === DEFAULTS[k]) u.searchParams.delete(k); else u.searchParams.set(k, v); }
  history.replaceState(null, '', u);
}
function syncControls() {
  $('search').value = state.q;
  for (const k of FILTERS) { if ([...$(k).options].some(o => o.value === state[k])) $(k).value = state[k]; else state[k] = $(k).value = DEFAULTS[k]; }
}
function fillOptions() {
  const codes = [...new Set(entries.map(r => r.code).filter(Boolean))].sort((a, b) => methodIndex(a) - methodIndex(b) || a.localeCompare(b));
  for (const v of codes) $('code').add(new Option(v, v));
  for (const v of [...new Set(entries.map(r => r.chi).filter(Boolean))].sort((a, b) => a - b)) $('chi').add(new Option('χ ' + v, String(v)));
  for (const v of [...new Set(entries.map(r => r.level).filter(v => v != null))].sort((a, b) => a - b)) $('level').add(new Option('level ' + v, String(v)));
  for (const v of Object.keys(PHYSICS).filter(p => entries.some(r => r.physics === p))) $('physics').add(new Option(PHYSICS[v], v));
}
function reset() { Object.assign(state, DEFAULTS); syncControls(); shown = 0; render(); }

document.querySelectorAll('[data-kind]').forEach(b => b.onclick = () => { state.kind = b.dataset.kind; shown = 0; render(); });
for (const k of FILTERS) $(k).onchange = () => { state[k] = $(k).value; shown = 0; render(); };
let searchTimer;
$('search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.q = $('search').value.trim(); shown = 0; render(); }, 150); };
$('reset').onclick = reset;
$('emptyReset').onclick = () => { if (state.kind === 'saved' && saved.size === 0) { state.kind = 'all'; shown = 0; render(); } else reset(); };
$('more').onclick = () => { const first = shown; shown += PAGE; render(); $('libList').children[first]?.querySelector('a:not([tabindex="-1"]),button')?.focus({ preventScroll: true }); };
function layout(pictures) {
  $('libList').classList.toggle('pictures', pictures);
  $('layoutPictures').setAttribute('aria-pressed', pictures); $('layoutList').setAttribute('aria-pressed', !pictures);
  try { localStorage.setItem('cloud-studio-layout', pictures ? 'pictures' : 'list'); } catch { /* storage blocked */ }
}
$('layoutList').onclick = () => layout(false); $('layoutPictures').onclick = () => layout(true);
let startPictures = false;
try { startPictures = localStorage.getItem('cloud-studio-layout') === 'pictures'; } catch { /* storage blocked */ }
layout(startPictures);
document.addEventListener('keydown', e => { if (e.key === '/' && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) && !document.querySelector('dialog[open]')) { e.preventDefault(); $('search').focus(); } });

// ------------------------------------------------------------------ film player
const sourceOf = v => LOCAL && v.localSrc && !triedRemote ? v.localSrc : v.src;
const currentVariant = () => activeFilm.variants[Number($('variant').value) || 0];
function selectVariant() {
  const v = currentVariant(), vid = $('video'); triedRemote = false;
  vid.pause(); const src = sourceOf(v);
  // no poster: a poster of the last saved state would stand before a film that starts at t = 0
  vid.removeAttribute('poster'); vid.src = src + FIRST_FRAME; vid.loop = $('loop').checked;
  $('download').href = src; $('download').download = slug(entryText(activeFilm) + ' ' + v.label) + '.mp4';
  setRich($('playerNote'), [v.note, activeFilm.filmNote || activeFilm.note].filter(Boolean).join(' '));
  $('videoError').hidden = true; $('message').textContent = '';
  vid.load(); vid.playbackRate = Number($('rate').value);
  const u = new URL(location); u.searchParams.set('film', activeFilm.id); u.searchParams.set('view', String($('variant').value)); history.replaceState(null, '', u);
}
function openFilm(r, trigger) {
  opener = trigger; activeFilm = r;
  titleInto($('playerTitle'), r);
  $('variant').replaceChildren(...r.variants.map((v, i) => new Option(v.label, i)));
  const requested = new URL(location).searchParams.get('view');
  if (requested && Number(requested) < r.variants.length) $('variant').value = requested;
  selectVariant();
  if (!$('player').open) $('player').showModal();
  $('closePlayer').focus();
}
$('closePlayer').onclick = () => $('player').close();
$('player').addEventListener('close', () => {
  if ($('player').open) return;                      // another film was opened before this event arrived
  const vid = $('video'); vid.pause(); vid.removeAttribute('src'); vid.load();
  const u = new URL(location); u.searchParams.delete('film'); u.searchParams.delete('view'); history.replaceState(null, '', u);
  opener?.focus();
});
for (const d of ['player', 'imageViewer']) $(d).addEventListener('click', e => {
  if (e.target !== $(d)) return;
  const b = e.target.getBoundingClientRect();
  if (e.clientX < b.left || e.clientX > b.right || e.clientY < b.top || e.clientY > b.bottom) e.target.close();
});
$('variant').onchange = selectVariant;
$('rate').onchange = () => { $('video').playbackRate = Number($('rate').value); };
$('loop').onchange = () => { $('video').loop = $('loop').checked; };
$('video').onerror = () => {
  if (!activeFilm || !$('video').getAttribute('src')) return;
  const v = currentVariant();
  // a local preview copy may be absent: fall back to the published film once
  if (LOCAL && v.localSrc && !triedRemote) { triedRemote = true; $('video').src = v.src + FIRST_FRAME; $('download').href = v.src; $('video').load(); return; }
  $('videoError').hidden = false; $('videoError').textContent = 'This film could not load. Try another version, or use the download link.';
};
$('pip').hidden = !document.pictureInPictureEnabled;
$('pip').onclick = async () => { try { if (document.pictureInPictureElement) await document.exitPictureInPicture(); else await $('video').requestPictureInPicture(); } catch { $('message').textContent = 'Start the film before opening picture in picture.'; } };
$('shareFilm').onclick = async () => { try { await navigator.clipboard.writeText(location.href); $('message').textContent = 'Link copied, with this film and version.'; } catch { $('message').textContent = 'Copy this address: ' + location.href; } };
document.addEventListener('visibilitychange', () => { if (document.hidden && !document.pictureInPictureElement) $('video').pause(); });

// ------------------------------------------------------------------ image sets
let imageRun = null, imageIndex = 0, imageOpener = null;
function showImage() {
  const file = imageRun.images[imageIndex], n = imageRun.images.length;
  $('galleryImage').src = file; $('galleryImage').alt = `${entryText(imageRun)}, picture ${imageIndex + 1} of ${n}`;
  $('imageDownload').href = file; $('imageDownload').download = slug(entryText(imageRun)) + '-' + String(imageIndex + 1).padStart(2, '0') + '.' + (file.split('.').pop() || 'jpg');
  $('imagePosition').textContent = `${imageIndex + 1} of ${n}`;
  $('imagePrev').disabled = imageIndex === 0; $('imageNext').disabled = imageIndex === n - 1;
}
function openImages(r, trigger) {
  imageRun = r; imageIndex = 0; imageOpener = trigger;
  titleInto($('imageTitle'), r); setRich($('imageNote'), r.note);
  showImage(); $('imageViewer').showModal();
  $('closeImages').focus();
}
$('imagePrev').onclick = () => { imageIndex = Math.max(0, imageIndex - 1); showImage(); };
$('imageNext').onclick = () => { imageIndex = Math.min(imageRun.images.length - 1, imageIndex + 1); showImage(); };
$('closeImages').onclick = () => $('imageViewer').close();
$('imageViewer').addEventListener('close', () => imageOpener?.focus());
$('imageViewer').addEventListener('keydown', e => { if (e.key === 'ArrowLeft') $('imagePrev').click(); if (e.key === 'ArrowRight') $('imageNext').click(); });
$('galleryImage').onerror = () => { $('imageNote').textContent = 'This picture could not load. Try the next one, or the download link.'; };

// ------------------------------------------------------------------ start
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw Error(r.status); return r.json(); });
Promise.allSettled([getJSON('assets/recent/catalog.json?v=20261125'), getJSON('data/studio-catalog.json?v=20261125')]).then(([recent, library]) => {
  if (library.status === 'fulfilled') for (const r of library.value.entries || []) libById.set(r.id, r);
  if (recent.status === 'fulfilled') {
    runs = Array.isArray(recent.value.runs) ? recent.value.runs : [];
    for (const r of runs) runByKey.set(runKey(r), r);
    renderGroups();
  } else $('groups').replaceChildren(el('p', 'error', 'The list of complete runs could not load. Refresh the page to try again; the runs are also on the Compare page.'));
  if (library.status === 'fulfilled') { entries = (library.value.entries || []).map(prepare); fillOptions(); syncControls(); render(); }
  else $('resultCount').textContent = 'The library could not load. Refresh the page to try again, or open the archive below.';
  const want = params.get('film') || (location.hash.startsWith('#film=') ? decodeURIComponent(location.hash.slice(6)) : null);
  const film = want ? findFilm(want) : null;
  if (film) openFilm(film, null);
  else if (location.hash.length > 1 && !location.hash.startsWith('#film=')) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
});
