// Build the library catalog read by index.html (data/studio-catalog.json) from the display catalogs.
// It reads only display catalogs and the viewer's own run list; simulation data is never opened.
//
//   node analysis/build_studio_catalog.cjs [--out FILE] [--recent FILE] [--recent3d FILE] [--viewer FILE]
//
//   --out       where to write the catalog (default data/studio-catalog.json)
//   --recent    projection catalog (default assets/recent/catalog.json)
//   --recent3d  3D catalog script defining RECENT_3D (default assets/recent3d/catalog.js)
//   --viewer    page whose run list decides the 3D entries (default viewer.html)
//
// Runs in the projection catalog follow the data contract: "level" (default 5), "code", "group",
// "boundary" and "base" are optional; any number of frames is accepted. A run with "base" keeps all
// of its files under that address (poster-edge.jpg, film-edge.mp4, ...).
'use strict';
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const ROOT = path.resolve(__dirname, '..'); process.chdir(ROOT);

function option(name, fallback) {
  const i = process.argv.indexOf('--' + name);
  if (i < 0) return fallback;
  const v = process.argv[i + 1];
  if (!v || v.startsWith('--')) throw Error('--' + name + ' needs a value');
  return v;
}
const OUT = option('out', 'data/studio-catalog.json');
const RECENT = option('recent', 'assets/recent/catalog.json');
const RECENT3D = option('recent3d', 'assets/recent3d/catalog.js');
const VIEWER = option('viewer', 'viewer.html');
const read = p => fs.readFileSync(p, 'utf8');

// ------------------------------------------------------------------ names
// Display names of the codes, exactly as the site writes them. First match wins.
const CODES = [
  [/^athenapk|^apk/i, 'AthenaPK'],
  [/^athena\s*\+\+|^athpp/i, 'Athena++'],
  [/^athena|^athw|^ath2d/i, 'Athena 4.2'],
  [/^enzo-?e\b|^enzoe/i, 'Enzo-E'],
  [/^enzo|^cw2d/i, 'Enzo'],
  [/^ramses|^ram\d?/i, 'RAMSES'],
  [/^flash-?x/i, 'Flash-X'],
  [/^flash|^f3d|^f2d|^f_|^cloudcrush|^sedov|^cloudstatic|^solver_compare/i, 'FLASH 4.8'],
  [/^arepo/i, 'Arepo'],
  [/^gizmo[ _]?mfm|^gzmfm/i, 'GIZMO MFM'],
  [/^gizmo[ _]?mfv|^gzmfv/i, 'GIZMO MFV'],
  [/^gadget|^g4/i, 'GADGET-4'],
  [/^gasoline|^gas/i, 'Gasoline'],
];
function codeOf(text) {
  const s = String(text || '').replace(/^New · /, '').trim();
  for (const [re, name] of CODES) if (re.test(s)) return name;
  return null;
}
// Boundary each method uses in its standard setup; a run is only labelled by its boundary when it differs.
const STANDARD_BOUNDARY = { 'Arepo': 'periodic along the wind', 'GIZMO MFM': 'periodic on all faces', 'GIZMO MFV': 'periodic on all faces', 'GADGET-4': 'periodic on all faces' };
const standardBoundary = code => STANDARD_BOUNDARY[code] || 'inflow and outflow';

const fmtT = t => (Math.round(Number(t) * 100) / 100).toFixed(2);
const levelOfCells = n => { const L = Math.log2(Number(n)) - 3; return Number.isFinite(L) && Math.abs(L - Math.round(L)) < 0.02 && L >= 1 ? Math.round(L) : null; };
// "Code · extra · χ N · level L"
const title = (code, extra, chi, level, levelText) => [code, ...extra, chi ? 'χ ' + chi : null, level != null ? 'level ' + level : levelText].filter(Boolean).join(' · ');
const INTERNAL = /_|\.(mp4|png|jpe?g|json|bin)$|^(ultra|hires|try\d*|full|matched|l\d+|lref\d+|sharp\d*)$/i;

// ------------------------------------------------------------------ sources
const ctx = {}; ctx.window = ctx; vm.createContext(ctx);
for (const f of ['data/manifest.js', 'data/densemap.js', RECENT3D]) vm.runInContext(read(f), ctx);
const recent3D = ctx.RECENT_3D || {};
{
  const source = read(VIEWER), a = source.indexOf('let ids ='), b = source.indexOf('// ------------------------------------------------------------------- panes');
  if (a < 0 || b < a) throw Error(VIEWER + ': the run list ("let ids =" up to the "panes" marker) was not found');
  vm.runInContext('const recent3D=RECENT_3D;' + source.slice(a, b) + ';this.viewerEntries=ids.map(id=>({id,...meta(id)}));', ctx);
}
const recent = JSON.parse(read(RECENT)).runs;
const inventory = new Map(JSON.parse(read('data/streaming-inventory.json')).runs.map(x => [x.run_id, x]));
const smooth = fs.existsSync('data/smooth60.json') ? JSON.parse(read('data/smooth60.json')) : {};
const entries = [];

// ------------------------------------------------------------------ complete runs (projection catalog)
// Plain notes for the runs published before the data contract; their catalog notes are review records.
const NOTES = {
  'enzo-1000': 'Wind enters through the upstream face and leaves through the downstream face.',
  'enzo-10': 'Wind enters through the upstream face and leaves through the downstream face.',
  'athpp-10': 'Wind enters through the upstream face and leaves through the downstream face.',
  'athpp-1000': 'Wind enters through the upstream face and leaves through the downstream face.',
  'enzoe-10': 'Wind enters through the upstream face. This run has no passive tracer, so cloud gas is followed by its density.',
  'enzoe-1000': 'Wind enters through the upstream face. This run has no passive tracer, so cloud gas is followed by its density.',
  'mfm-sharp': 'Meshless finite mass method in a box that is periodic on all faces.',
  'mfv-sharp': 'Meshless finite volume method in a box that is periodic on all faces.',
  'mfm-historical': 'Meshless finite mass method in a box that is periodic on all faces. The wind starts with a smooth tanh velocity profile around the cloud.',
  'mfv-historical': 'Meshless finite volume method in a box that is periodic on all faces. The wind starts with a smooth tanh velocity profile around the cloud.',
  'apk-hlle-off': 'AthenaPK on the GPU with the HLLE solver and PLM reconstruction.',
  'apk-hlle-on': 'AthenaPK on the GPU with the HLLE solver and PLM reconstruction. Tabulated radiative cooling is on.',
  'apk-hlle-10': 'AthenaPK on the GPU with the HLLE solver and PLM reconstruction.',
  'apk-hllc-off': 'AthenaPK on the GPU with the HLLC solver and PPM reconstruction.',
  'apk-hllc-on': 'AthenaPK on the GPU with the HLLC solver and PPM reconstruction. Tabulated radiative cooling is on.',
  'apk-hllc-10': 'AthenaPK on the GPU with the HLLC solver and PPM reconstruction.',
  'apk-hllc-plm-off': 'AthenaPK on the GPU with the HLLC solver and PLM reconstruction.',
};
// Sentences in older notes that are review vocabulary rather than a description of the run.
const REVIEW = /accept|bounded|convergence|certif|screen|retain|controller|establish|ranking|pending|receipt|input\.in|fallback|correction|under-resolved/i;
const plainNote = text => String(text || '').split(/(?<=[.;])\s+/).filter(s => s.trim() && !REVIEW.test(s)).join(' ').replace(/;$/, '.').trim();

function recentExtras(r, code) {
  if (r.group === 'twelve') return [];
  const out = [];
  if (r.boundary && r.boundary !== standardBoundary(code)) out.push(r.boundary);
  for (const part of String(r.label || '').split(' · ').slice(1)) {
    const s = part.trim(), low = s.toLowerCase();
    if (!s || /^(sharp\d*|cooling off|nonradiative|periodic box|periodic|new)$/.test(low) || /periodic|inflow|outflow/.test(low)) continue;
    if (/^χ\s*[\d.]+$/.test(s) || /^(level|n)\s*\d+$/.test(low)) continue;
    if (low === 'historical') { out.push('smooth velocity profile'); continue; }
    if (low === 'cooling on') { out.push('with cooling'); continue; }
    if (INTERNAL.test(low)) continue;
    out.push(s);
  }
  return out.sort((a, b) => (b.includes('/') ? 1 : 0) - (a.includes('/') ? 1 : 0));
}

for (const r of recent) {
  if (!Array.isArray(r.frames) || !r.frames.length) throw Error('Run ' + r.id + ' has no frames');
  const level = Number.isInteger(r.level) ? r.level : 5;
  const code = codeOf(r.code) || codeOf(r.label);
  if (!code) throw Error('Run ' + r.id + ': unknown code ' + (r.code || r.label));
  const n = r.frames.length, t0 = r.frames[0].time, end = r.frames.at(-1).time;
  const base = typeof r.base === 'string' && r.base ? r.base : null;
  const span = `t = ${fmtT(t0)} to ${fmtT(end)} t_cc`;
  let variants, poster, filmNote;
  if (base) {
    poster = base + 'poster-edge.jpg';
    variants = [['edge', 'Edge on'], ['face', 'Face on']].map(([v, name]) => ({ src: base + `film-${v}.mp4`, label: name + ', 60 fps', view: name, poster: base + `poster-${v}.jpg`, fps: 60 }));
    filmNote = `All ${n} saved states from ${span}, played at 60 fps with crossfades between neighbouring states.`;
  } else {
    poster = `assets/posters/${r.id}-edge.jpg`;
    variants = [['edge', 'Edge on'], ['face', 'Face on']].map(([v, name]) => ({ src: `assets/films/${r.id}-${v}.mp4`, label: name + ', original', view: name, poster: `assets/posters/${r.id}-${v}.jpg` }));
    filmNote = `${n} saved states from ${span}, each held for 2 seconds.`;
  }
  const note = base ? plainNote(r.note) : (NOTES[r.id] || plainNote(r.note));
  const entry = {
    id: 'new_' + r.id, run: r.id, label: title(code, recentExtras(r, code), r.chi, level), code, chi: r.chi, level,
    physics: r.cooling === 'tabular' ? 'tabular' : r.cooling === 'none' ? 'none' : 'unknown', kind: 'recent', status: 'Complete run',
    frames: n, end, poster, posterTime: end, projection: 'recent.html?run=' + encodeURIComponent(r.id), variants, note, filmNote,
  };
  if (recent3D['new_' + r.id]) entry.viewer = 'viewer.html?run=' + encodeURIComponent('new_' + r.id);
  if (r.group) entry.group = r.group;
  if (r.boundary) entry.boundary = r.boundary;
  if (base) entry.base = base;
  entries.push(entry);
}

// ------------------------------------------------------------------ earlier runs in the 3D viewer
// The viewer describes a run as "<code> · <variant>" (older viewer pages: "<code> M=0.5 · cooling NOT enabled").
// The library uses the viewer's own variant words so both pages name a run the same way.
function viewerExtras(m) {
  if (typeof m.variant === 'string') return m.variant.split(' · ').map(s => s.trim()).filter(Boolean);
  const text = String(m.code), out = []; let r;
  if ((r = text.match(/M=([\d.]+)/))) out.push('Mach ' + r[1]);
  if (/cooling NOT enabled/i.test(text)) out.push('cooling inactive');
  if (/tracking/i.test(text)) out.push('cloud tracking');
  if ((r = text.match(/MHD β=(\d+)/))) out.push('MHD β ' + r[1]);
  return out;
}
for (const m of ctx.viewerEntries) {
  if (recent3D[m.id]) continue;   // complete runs above already carry their 3D link
  const code = codeOf(m.base) || codeOf(m.code) || codeOf(m.id);
  if (!code) throw Error('3D run ' + m.id + ': unknown code ' + m.code);
  const inv = inventory.get(m.id), partial = inv && inv.last_t_tcc < 4.99;
  const frames = inv?.index_frame_count ?? (ctx.DENSE_RUNS && ctx.DENSE_RUNS[m.id]) ?? undefined;
  const physics = m.id.includes('_mhd_') ? 'mhd' : /^(apk|athpp|athw|enzo|flash|arepo|gzm|ramses|g4)/.test(m.id) ? 'none' : 'unknown';
  entries.push({
    id: m.id, label: title(code, viewerExtras(m), m.chi, m.lvl), code, chi: m.chi, level: m.lvl, physics, kind: '3d',
    status: partial ? `Ends at t = ${fmtT(inv.last_t_tcc)} t_cc` : 'Earlier run', frames, end: inv?.last_t_tcc,
    viewer: 'viewer.html?run=' + encodeURIComponent(m.id),
    note: 'Earlier run, shown as density surfaces in the 3D viewer.' + (/^apkcool/.test(m.id) ? ' Earlier run without radiative cooling.' : ''),
  });
}

// ------------------------------------------------------------------ earlier films (assets/movies)
const PREFIX = { apk: 'AthenaPK', athpp: 'Athena++', athw: 'Athena 4.2', enzo: 'Enzo', flash: 'FLASH 4.8', flash3d: 'FLASH 4.8', flashx: 'Flash-X', gas: 'Gasoline', gzmfm: 'GIZMO MFM', gzmfv: 'GIZMO MFV', arepo: 'Arepo', ramses: 'RAMSES', g4: 'GADGET-4' };
const SHOCK = n => { const L = 6 + Math.log2(n / 256), r = Math.round(L); return Math.abs(L - r) < 0.02 ? { level: r } : { levelText: 'about level ' + r }; };
const cells = (n, dims) => { const l = levelOfCells(n); return l ? { level: l } : { levelText: dims || n + ' cells long' }; };
// What a film shows, from its file name: code, χ, level and the kind of picture.
function filmInfo(name) {
  let r;
  const res = (code, chi, extra, lv) => ({ code, chi: chi == null ? null : +chi, extra, ...lv });
  if ((r = name.match(/^terrain_flash_chi(\d+)_lref(\d+)$/))) return res('FLASH 4.8', r[1], ['2D terrain flyover'], { level: +r[2] });
  if ((r = name.match(/^terrain_(athw|apk|athpp)_chi(\d+)_(\d+)$/))) return res(PREFIX[r[1]], r[2], ['2D terrain flyover'], cells(r[3]));
  if ((r = name.match(/^(athpp|ramses|enzo|apk|athw|cw2d)_chi(\d+)_(\d+)$/))) return res(r[1] === 'cw2d' ? 'Enzo' : PREFIX[r[1]], r[2], ['2D'], cells(r[3]));
  if ((r = name.match(/^apk2d_chi(\d+)_(\d+)$/))) return res('AthenaPK', r[1], ['2D'], cells(r[2]));
  if ((r = name.match(/^arepo_chi(\d+)$/))) return res('Arepo', r[1], ['2D'], { level: 6 });
  if ((r = name.match(/^gizmo_(mfm|mfv)_chi(\d+)$/))) return res('GIZMO ' + r[1].toUpperCase(), r[2], ['2D'], { levelText: '400 × 200 particles' });
  if ((r = name.match(/^gasoline_chi(\d+)$/))) return res('Gasoline', r[1], ['thin 3D slab'], { levelText: '320 × 160 × 8 particles' });
  if ((r = name.match(/^gadget4_chi(\d+)$/))) return res('GADGET-4', r[1], ['2D'], { level: 6 });
  if ((r = name.match(/^flashx_chi(\d+)(?:_l(\d+))?$/))) return res('Flash-X', r[1], ['2D'], { level: r[2] ? +r[2] : 6 });
  if ((r = name.match(/^flash_chi(\d+)_lref(\d+)(_partial)?$/))) return res('FLASH 4.8', r[1], ['2D'], { level: +r[2], partial: !!r[3] });
  if ((r = name.match(/^cloudcrush_lref(\d+)$/))) return res('FLASH 4.8', 10, ['2D'], { level: +r[1] });
  if ((r = name.match(/^flash3d_chi(\d+)_lref(\d+)$/))) return res('FLASH 4.8', r[1], ['3D slice'], { level: +r[2] });
  if ((r = name.match(/^(apk|athw|athpp)3d_chi(\d+)_(\d+)$/))) return res(PREFIX[r[1]], r[2], ['3D slice'], cells(r[3]));
  if ((r = name.match(/^(apk|athw|athpp)3d_chi(\d+)_l(\d)_(matched|full)$/i))) return res(PREFIX[r[1]], r[2], [/matched/i.test(r[4]) ? '3D slice' : '3D slice'], { level: +r[3] });
  if ((r = name.match(/^athena_shock_d(\d+)_(\d+)$/))) return res('Athena 4.2', r[1], ['2D shock driven'], SHOCK(+r[2]));
  if ((r = name.match(/^athena_shk_cloud_(hires|ultra)$/))) return res('Athena 4.2', 10, ['2D shock driven'], SHOCK(r[1] === 'hires' ? 1800 : 3600));
  if ((r = name.match(/^full_([a-z]+?(?:3d)?)(\d+)?_(?:L(\d)_)?chi(\d+)$/))) {
    const code = PREFIX[r[1].replace(/3d$/, '')] || PREFIX[r[1]];
    const lv = r[3] ? { level: +r[3] } : r[2] ? cells(+r[2]) : {};
    return res(code, r[4], ['3D surfaces'], lv);
  }
  return res(codeOf(name), (name.match(/chi(\d+)/) || [])[1], [], {});
}
const ORIGINAL = name => name === 'flash3d_chi100_lref6_smooth' ? 'Original, held frames at 30 fps' : name.endsWith('_smooth') ? 'Original, smoothed' : name.endsWith('_slow') ? 'Original, slow motion' : 'Original';
const movies = new Map();
const movieFiles = [...new Map(ctx.STUDIO_MOVIES.map(m => [m.src, m])).values()];
for (const f of fs.readdirSync('assets/movies').filter(f => f.endsWith('.mp4'))) {
  if (!movieFiles.some(m => m.src === 'assets/movies/' + f)) movieFiles.push({ src: 'assets/movies/' + f, name: f.slice(0, -4) });
}
for (const m of movieFiles) {
  if (!fs.existsSync(m.src)) throw Error('Missing film ' + m.src);
  const base = m.name.replace(/_(slow|smooth)$/, '');
  if (!movies.has(base)) movies.set(base, []);
  movies.get(base).push({ src: m.src, label: ORIGINAL(m.name), poster: 'assets/posters/' + base + '.jpg' });
}
for (const [name, variants] of movies) {
  const f = filmInfo(name);
  if (!f.code) throw Error('Film ' + name + ': unknown code');
  entries.push({
    id: 'film_' + name, label: title(f.code, f.extra, f.chi, f.level, f.levelText), code: f.code, chi: f.chi, level: f.level ?? null,
    ...(f.levelText ? { levelText: f.levelText } : {}), physics: 'unknown', kind: 'film', status: 'Earlier film', variants,
    poster: variants[0].poster, note: variants.length + (variants.length === 1 ? ' version' : ' versions') + ' of this film.',
    filmNote: 'Earlier film made from the saved outputs of this run.' + (f.partial ? ' The run stops before t = 5 t_cc.' : ''),
  });
}

// ------------------------------------------------------------------ earlier image sets and test problems
function galleryInfo(g) {
  const tag = String(g.tag || ''), kindText = String(g.kind || '');
  const dims = (kindText.match(/(\d+)x(\d+)/) || []).slice(1).map(Number);
  const about = kindText.match(/about level (\d+)/), stated = kindText.match(/\blevel (\d+)/);
  const lv = about ? { levelText: 'about level ' + about[1] } : stated ? { level: +stated[1] } : dims.length ? cells(Math.max(...dims)) : {};
  const code = codeOf(g.code) || codeOf(tag);
  const size = dims.length ? dims.join(' × ') + ' cells' : '';
  if (/^sedov/i.test(tag)) return { code, chi: null, extra: ['Sedov blast wave'], ...lv, test: true, note: [size, 'Sedov blast wave test of the solver'].filter(Boolean).join(', ') + '.' };
  if (/static/i.test(tag)) return { code, chi: g.chi, extra: ['static cloud'], ...lv, test: true, note: 'A cloud with no wind, a test that the cloud stays in place.' };
  if (/solver/i.test(tag)) return { code, chi: g.chi, extra: ['Roe and HLLC solvers'], ...lv, test: true, note: 'The same run with the Roe and the HLLC Riemann solvers, side by side.' };
  const shock = /shock/i.test(kindText);
  return {
    code, chi: g.chi || null, extra: [shock ? '2D shock driven' : '2D'], ...lv,
    note: [size, shock ? 'cloud hit by a shock' : /wind tunnel/i.test(kindText) ? 'wind tunnel setup' : '', /partial/i.test(kindText + tag) ? 'the run stops before t = 5 t_cc' : ''].filter(Boolean).join(', ').replace(/^./, c => c.toUpperCase()) + '.',
  };
}
for (const g of ctx.STUDIO_GALLERY) {
  const info = galleryInfo(g);
  if (!info.code) throw Error('Image set ' + g.dir + ': unknown code');
  const preview = g.files.find(f => /Slice|slice|dens|proj/i.test(f)) || g.files[0];
  const entry = {
    id: 'gallery_' + g.dir.split('/').pop(), label: title(info.code, info.extra, info.chi, info.level, info.levelText), code: info.code,
    chi: info.chi || null, level: info.level ?? null, ...(info.levelText ? { levelText: info.levelText } : {}), physics: 'unknown',
    kind: info.test ? 'test' : 'image', status: info.test ? 'Test problem' : 'Earlier image set', poster: g.dir + '/' + preview,
    images: g.files.map(f => g.dir + '/' + f), note: info.note, projection: 'archive.html#gallery',
  };
  // the first output of a run is its initial state, so its time is known
  if (/(^|[_.])0+([_.])/.test(preview) && !/_t\d/.test(preview)) entry.posterTime = 0;
  entries.push(entry);
}

// ------------------------------------------------------------------ 60 fps versions of the films on this site
for (const r of entries) {
  if (!r.variants || r.base) continue;
  const previews = r.variants.filter(v => smooth[v.src]).map(v => ({
    src: smooth[v.src].src, localSrc: smooth[v.src].localSrc, label: v.view ? v.view + ', 60 fps' : v.label.replace(/^Original/, '60 fps'),
    poster: v.poster, interpolated: true, originalSource: v.src, note: 'Played at 60 fps, with crossfades between neighbouring saved frames.',
  }));
  r.variants = [...previews, ...r.variants];
}
for (const r of entries) if (r.variants) r.variants = r.variants.map(({ view, ...rest }) => rest);

// ------------------------------------------------------------------ titles are unique within a kind
// Among entries that share a title, a twelve methods run keeps it, then a boundary control, then the entry
// with the most frames; the others name their frame count, or a number when that does not separate them.
{
  const word = { recent: 'run', '3d': 'run', film: 'film', image: 'set', test: 'set' }, groups = new Map();
  for (const r of entries) { const key = r.kind + '|' + r.label; if (!groups.has(key)) groups.set(key, []); groups.get(key).push(r); }
  const taken = new Set(entries.map(r => r.kind + '|' + r.label));
  const prio = r => r.group === 'twelve' ? 0 : r.group === 'boundary' ? 1 : 2;
  for (const list of groups.values()) {
    if (list.length < 2) continue;
    const order = list.map((r, i) => ({ r, i })).sort((a, b) => prio(a.r) - prio(b.r) || (b.r.frames || 0) - (a.r.frames || 0) || a.i - b.i).map(x => x.r);
    let n = 1;
    for (const r of order.slice(1)) {
      let label = r.frames && r.frames !== order[0].frames ? `${r.label} · ${r.frames} frames` : null;
      while (!label || taken.has(r.kind + '|' + label)) label = `${r.label} · ${word[r.kind] || 'entry'} ${++n}`;
      taken.add(r.kind + '|' + label); r.label = label;
    }
  }
}

const viewerCode = m => recent3D[m.id] ? codeOf(recent3D[m.id].code) || codeOf(recent3D[m.id].label) : codeOf(m.base) || codeOf(m.code) || codeOf(m.id);
const out = {
  schema: 'cloud-studio-library/2',
  description: 'The Cloud Studio library: complete runs, earlier runs in the 3D viewer, films and image sets, with the code, χ and level of each.',
  counts: {
    runs: ctx.viewerEntries.length,
    codes: new Set(ctx.viewerEntries.map(viewerCode).filter(Boolean)).size,
    films: new Set(entries.flatMap(r => (r.variants || []).map(v => v.src))).size,
  },
  entries,
};
fs.mkdirSync(path.dirname(path.resolve(OUT)), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
const kinds = {}; for (const r of entries) kinds[r.kind] = (kinds[r.kind] || 0) + 1;
console.log(JSON.stringify({ out: path.resolve(OUT), entries: entries.length, kinds, ...out.counts }));
