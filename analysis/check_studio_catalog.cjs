// Check the library catalog before publishing.
//
//   node analysis/check_studio_catalog.cjs [--catalog FILE] [--recent FILE] [--recent3d FILE] [--base-root DIR]
//
//   --catalog    library catalog to check (default data/studio-catalog.json)
//   --recent     projection catalog it was built from (default assets/recent/catalog.json)
//   --recent3d   3D catalog script defining RECENT_3D (default assets/recent3d/catalog.js)
//   --base-root  folder that holds runs with a "base" address before they are published, one folder per
//                run id (DIR/<id>/edge.png, DIR/<id>/film-edge.mp4, DIR/<id>/3d/index.json, ...).
//                Without it the files under a base address are not looked for.
'use strict';
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const ROOT = path.resolve(__dirname, '..'); process.chdir(ROOT);
function option(name, fallback) {
  const i = process.argv.indexOf('--' + name);
  if (i < 0) return fallback;
  const v = process.argv[i + 1];
  if (!v || v.startsWith('--')) throw Error('--' + name + ' needs a value');
  return v;
}
const CATALOG = option('catalog', 'data/studio-catalog.json'), RECENT = option('recent', 'assets/recent/catalog.json');
const RECENT3D = option('recent3d', 'assets/recent3d/catalog.js'), BASE_ROOT = option('base-root', null);
const c = JSON.parse(fs.readFileSync(CATALOG, 'utf8'));
const recentRuns = JSON.parse(fs.readFileSync(RECENT, 'utf8')).runs;
const ctx = {}; ctx.window = ctx; vm.createContext(ctx); vm.runInContext(fs.readFileSync(RECENT3D, 'utf8'), ctx);
const recent3D = ctx.RECENT_3D || {};

const CODES = ['Athena++', 'AthenaPK', 'Athena 4.2', 'Enzo', 'Enzo-E', 'RAMSES', 'FLASH 4.8', 'Flash-X', 'Arepo', 'GIZMO MFM', 'GIZMO MFV', 'GADGET-4', 'Gasoline'];
const TWELVE = CODES.slice(0, 12);
const BOUNDARIES = ['inflow and outflow', 'periodic on all faces', 'periodic along the wind'];
const KINDS = ['recent', '3d', 'film', 'image', 'test'];
// Text a visitor reads: no dash punctuation, no file or internal run names.
const DASH = /[–—]|--| - /;
const INTERNAL = /_(?!cc\b)|\.(mp4|png|jpe?g|json|bin)\b|\b(ultra|hires|sharp\d*|try\d|lref\d+|full)\b|\bL\d\b|tcc\b/;
const problems = [];
const check = (ok, message) => { if (!ok) problems.push(message); };
const isUrl = s => /^https?:\/\//.test(s);

// ------------------------------------------------------------------ files
let localFiles = 0, baseFiles = 0, localPreviews = 0;
const sizeOf = f => { try { return fs.statSync(f).size; } catch { return 0; } };
function baseLocal(entry, url) {
  // a base address maps to BASE_ROOT/<run id>/<name>
  if (!BASE_ROOT || !entry.base || !url.startsWith(entry.base)) return null;
  return path.join(BASE_ROOT, entry.run, ...url.slice(entry.base.length).split('/'));
}
function checkFile(entry, f) {
  if (!f) return;
  if (isUrl(f)) {
    if (entry.base && f.startsWith(entry.base)) {
      const local = baseLocal(entry, f);
      if (local) { check(sizeOf(local) > 0, `${entry.id}: missing or empty ${local}`); baseFiles++; }
    } else check(/^https:\/\/raw\.githubusercontent\.com\//.test(f), `${entry.id}: unexpected address ${f}`);
    return;
  }
  check(!path.isAbsolute(f) && !f.includes('..'), `${entry.id}: unsafe path ${f}`);
  check(sizeOf(f) > 0, `${entry.id}: missing or empty ${f}`); localFiles++;
}
function pngSize(file) {
  const b = Buffer.alloc(24), fd = fs.openSync(file, 'r');
  try { fs.readSync(fd, b, 0, 24, 0); } finally { fs.closeSync(fd); }
  assert.equal(b.toString('latin1', 1, 4), 'PNG', file + ' is not a PNG');
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}
function checkIndex(id, dir, expectFrames) {
  const p = JSON.parse(fs.readFileSync(path.join(dir, 'index.json'), 'utf8'));
  check(Array.isArray(p.frames) && p.frames.length > 0, `${id}: 3D index without frames`);
  check(p.times.length === p.frames.length, `${id}: 3D index has ${p.frames.length} frames and ${p.times.length} times`);
  check(p.times.every((t, i) => i === 0 || t > p.times[i - 1]), `${id}: 3D times are not increasing`);
  if (expectFrames != null) check(p.frames.length === expectFrames, `${id}: RECENT_3D says ${expectFrames} frames, index has ${p.frames.length}`);
  for (const f of p.frames) check(sizeOf(path.join(dir, f)) > 0, `${id}: missing 3D frame ${f}`);
  return p.frames.length;
}

// ------------------------------------------------------------------ entries
const ids = new Set(), labels = new Map(), films = new Set();
check(c.entries.length > 0, 'empty catalog');
for (const r of c.entries) {
  check(!ids.has(r.id), 'duplicate id ' + r.id); ids.add(r.id);
  check(KINDS.includes(r.kind), `${r.id}: unknown kind ${r.kind}`);
  check(CODES.includes(r.code), `${r.id}: code "${r.code}" is not a site code name`);
  check(typeof r.label === 'string' && r.label.startsWith(r.code), `${r.id}: title does not start with the code`);
  const key = r.kind + '|' + r.label; check(!labels.has(key), `${r.id}: same title as ${labels.get(key)}`); labels.set(key, r.id);
  for (const [field, text] of [['label', r.label], ['status', r.status], ['note', r.note], ['filmNote', r.filmNote], ['levelText', r.levelText], ...(r.variants || []).flatMap(v => [['variant', v.label], ['variant note', v.note]])]) {
    if (text == null) continue;
    check(!DASH.test(text), `${r.id}: dash punctuation in ${field}: ${text}`);
    if (field !== 'note' && field !== 'filmNote' && field !== 'variant note') check(!INTERNAL.test(text), `${r.id}: internal name in ${field}: ${text}`);
  }
  check(r.level == null || (Number.isInteger(r.level) && r.level >= 1), `${r.id}: level ${r.level}`);
  if (r.level != null) check(r.label.includes('level ' + r.level), `${r.id}: title does not name level ${r.level}`);
  if (r.chi) check(r.label.includes('χ ' + r.chi), `${r.id}: title does not name χ ${r.chi}`);
  if (r.group != null) check(['twelve', 'boundary', 'solver', 'smooth', 'other'].includes(r.group), `${r.id}: group ${r.group}`);
  if (r.boundary != null) check(BOUNDARIES.includes(r.boundary), `${r.id}: boundary "${r.boundary}"`);
  if (r.group === 'twelve') check(TWELVE.includes(r.code) && r.chi === 100, `${r.id}: a twelve methods entry must be one of the twelve codes at χ 100`);
  if (r.group === 'boundary') check(!!r.boundary, `${r.id}: a boundary control needs its boundary`);
  if (r.base != null) check(isUrl(r.base) && r.base.endsWith('/') && !!r.run, `${r.id}: base must be an absolute address ending in / and the entry must name its run`);
  if (r.viewer) check(r.viewer.startsWith('viewer.html?run='), `${r.id}: viewer link ${r.viewer}`);
  for (const f of [r.poster, ...(r.images || []), ...(r.variants || []).flatMap(v => [v.src, v.poster])]) checkFile(r, f);
  for (const v of r.variants || []) {
    films.add(v.src); check(!!v.label, `${r.id}: film version without a label`);
    // local copies of the 60 fps films are ignored by git; check them only where they are present
    if (v.localSrc && sizeOf(v.localSrc) > 0) { localPreviews++; localFiles++; }
  }
  if (r.posterTime != null) check(Number.isFinite(r.posterTime) && r.posterTime >= 0, `${r.id}: posterTime ${r.posterTime}`);
}
check(films.size === c.counts.films, `counts.films is ${c.counts.films}, the catalog links ${films.size} distinct films`);
for (const name of fs.readdirSync('assets/movies').filter(n => n.endsWith('.mp4'))) check(films.has('assets/movies/' + name), 'film not in the library: ' + name);
check(Number.isInteger(c.counts.runs) && c.counts.runs > 0 && Number.isInteger(c.counts.codes) && c.counts.codes > 0 && c.counts.codes <= CODES.length, 'counts ' + JSON.stringify(c.counts));

// ------------------------------------------------------------------ complete runs against the projection catalog
const recent = c.entries.filter(r => r.kind === 'recent');
check(recent.length === recentRuns.length, `${recent.length} complete runs in the library, ${recentRuns.length} in ${RECENT}`);
let meshes = 0, sample = null;
for (const run of recentRuns) {
  const r = c.entries.find(e => e.id === 'new_' + run.id);
  if (!r) { problems.push('run ' + run.id + ' is not in the library'); continue; }
  const n = run.frames.length;
  check(r.frames === n, `${r.id}: ${r.frames} frames in the library, ${n} in the run`);
  check(Math.abs(r.end - run.frames.at(-1).time) < 1e-9, `${r.id}: end time differs from the last frame`);
  check(run.frames.every((f, i) => i === 0 || f.time > run.frames[i - 1].time), `${r.id}: frame times are not increasing`);
  check(r.level === (Number.isInteger(run.level) ? run.level : 5), `${r.id}: level ${r.level}`);
  // a run with a base address that stops before 5 t_cc carries its own status, and its frames must end before 5 t_cc
  const ownStatus = run.base && run.status && run.status !== 'Complete run' ? run.status : 'Complete run';
  check(r.status === ownStatus, `${r.id}: status ${r.status}, expected ${ownStatus}`);
  if (ownStatus !== 'Complete run') check(run.frames.at(-1).time < 4.99 && /^Stops at /.test(ownStatus), `${r.id}: status "${ownStatus}" with the last frame at ${run.frames.at(-1).time}`);
  else check(run.frames.at(-1).time > 4.99, `${r.id}: complete run whose last frame is at ${run.frames.at(-1).time}`);
  if (run.box != null) check(run.box === 100 && /100 R box/.test(r.label), `${r.id}: box ${run.box} or the title does not name the 100 R box`);
  check(r.physics === (run.cooling === 'tabular' ? 'tabular' : run.cooling === 'none' ? 'none' : 'unknown'), `${r.id}: physics ${r.physics} for cooling ${run.cooling}`);
  check((r.group || null) === (run.group || null) && (r.boundary || null) === (run.boundary || null), `${r.id}: group or boundary not carried`);
  check(!!r.viewer === !!recent3D['new_' + run.id], `${r.id}: 3D link does not match RECENT_3D`);
  if (run.base) {
    check(r.base === run.base, `${r.id}: base not carried`);
    const own = (r.variants || []).filter(v => v.src.startsWith(run.base));
    check(own.length === 2 && own.every(v => / 60 fps$/.test(v.label)), `${r.id}: a run with base needs one 60 fps film per view`);
    const m3 = recent3D['new_' + run.id];
    if (m3) check(m3.base === run.base, `${r.id}: RECENT_3D base differs from the run's base`);
    if (BASE_ROOT) {
      const dir = path.join(BASE_ROOT, run.id);
      for (const [name, width] of [['edge.png', 256], ['face.png', 128]]) {
        const f = path.join(dir, name);
        if (sizeOf(f) === 0) { problems.push(`${r.id}: missing ${f}`); continue; }
        const s = pngSize(f); baseFiles++;
        check(s.width === width && s.height === 128 * n, `${r.id}: ${name} is ${s.width} x ${s.height}, expected ${width} x ${128 * n}`);
      }
      if (m3) { const k = checkIndex(r.id, path.join(dir, '3d'), m3.frames); meshes += k; baseFiles += k + 1; }
    }
  } else {
    check(r.variants.filter(v => !v.interpolated).length === 2, `${r.id}: expected two original films`);
    for (const v of ['edge', 'face']) check(sizeOf(`assets/recent/${run.id}-${v}.png`) > 0, `${r.id}: missing assets/recent/${run.id}-${v}.png`);
    const m3 = recent3D['new_' + run.id];
    if (m3 && !sample) { sample = r.id; meshes += checkIndex(r.id, `assets/recent3d/new_${run.id}`, m3.frames); }
  }
}

if (problems.length) {
  console.error(problems.length + ' problem' + (problems.length === 1 ? '' : 's') + ':\n  ' + problems.slice(0, 80).join('\n  '));
  process.exit(1);
}
console.log(JSON.stringify({ passed: true, entries: c.entries.length, recent: recent.length, uniqueFilms: films.size, localAssetReferences: localFiles,
  localCopiesOf60fpsFilms: localPreviews, baseFilesChecked: BASE_ROOT ? baseFiles : 'skipped (no --base-root)', meshesChecked: meshes, sample3D: sample }));
