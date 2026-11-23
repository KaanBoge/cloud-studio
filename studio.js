'use strict';
// Library page: the twelve methods, the boundary control and the searchable library of runs, films and images.
const $ = id => document.getElementById(id);
const params = new URL(location).searchParams;
const METHOD_ORDER = ['Athena++', 'AthenaPK', 'Athena 4.2', 'Enzo', 'Enzo-E', 'RAMSES', 'FLASH 4.8', 'Flash-X', 'Arepo', 'GIZMO MFM', 'GIZMO MFV', 'GADGET-4'];
const PHYSICS = { none: 'Nonradiative', tabular: 'Cooling on', mhd: 'Magnetized', unknown: 'Not specified' };
const BADGE = { recent: 'Complete run', '3d': '3D viewer', film: 'Film', image: 'Images', test: 'Test problem' };
const LOCAL = ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(location.hostname);
const DEFAULTS = { kind: 'all', q: '', code: 'all', chi: 'all', level: 'all', physics: 'all', sort: 'featured' };
const FILTERS = ['code', 'chi', 'level', 'physics', 'sort'];
const state = Object.fromEntries(Object.entries(DEFAULTS).map(([k, v]) => [k, params.get(k) || v]));
let all = [], shown = 0, activeFilm = null, opener = null, triedRemote = false;
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
const timeText = t => `t = ${fmtT(t)} t_cc`;
const levelText = r => r.level != null ? 'level ' + r.level : r.levelText || null;
const methodIndex = code => { const i = METHOD_ORDER.indexOf(code); return i < 0 ? METHOD_ORDER.length : i; };
const slug = s => String(s).toLowerCase().replace(/χ/g, 'chi').replace(/[^a-z0-9+]+/g, '-').replace(/^-|-$/g, '');
function link(text, href) { const a = el('a', '', text); a.href = href; return a; }
function storeSaved() { try { localStorage.setItem('cloud-studio-saved', JSON.stringify([...saved])); } catch { /* storage blocked */ } }

// ------------------------------------------------------------------ search and order
// Words a visitor may type to find an entry; every word of the query must start a word of the entry.
function words(r) {
  if (r._words) return r._words;
  const text = [r.label, r.code, r.note, r.status, BADGE[r.kind], PHYSICS[r.physics], r.boundary,
    r.chi ? `chi ${r.chi} χ${r.chi} chi${r.chi}` : '', r.level != null ? `level ${r.level} l${r.level}` : r.levelText,
    r.group === 'twelve' ? 'twelve methods paper' : r.group === 'boundary' ? 'boundary control' : '',
    r.variants ? 'film films' : '', r.viewer ? '3d' : '', r.images ? 'images' : ''].filter(Boolean).join(' ').toLowerCase();
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
    case 'all': return r.kind !== 'test';
    case '3d': return !!r.viewer;
    case 'film': return !!r.variants;
    case 'saved': return saved.has(r.id);
    default: return r.kind === state.kind;
  }
}
const matches = r => kindMatches(r) && queryMatches(r, state.q) && ['code', 'chi', 'level', 'physics'].every(k => state[k] === 'all' || String(r[k]) === state[k]);
// Default order: the twelve methods, other complete runs, entries with films, the rest.
const rank = r => r.group === 'twelve' ? 0 : r.kind === 'recent' ? 1 : r.variants ? 2 : 3;
function sortRows(rows) {
  if (state.sort === 'name') return rows.sort((a, b) => a.label.localeCompare(b.label));
  if (state.sort === 'resolution') return rows.sort((a, b) => (b.level ?? 0) - (a.level ?? 0) || a._i - b._i);
  return rows.sort((a, b) => rank(a) - rank(b) || (rank(a) === 0 ? methodIndex(a.code) - methodIndex(b.code) || (b.level ?? 0) - (a.level ?? 0) : 0) || a._i - b._i);
}

// ------------------------------------------------------------------ cards
function placeholder(r) {
  const ph = el('div', 'placeholder');
  ph.append(el('span', 'ph-code', r.code));
  const sub = [levelText(r), r.chi ? 'χ ' + r.chi : null].filter(Boolean).join(' · ');
  if (sub) ph.append(el('span', 'ph-sub', sub));
  return ph;
}
function pictureWords(r) {
  if (r.kind === 'recent') return 'edge on column density' + (r.posterTime != null ? ' at ' + timeText(r.posterTime) : '');
  if (r.images) return 'first picture of the set' + (r.posterTime != null ? ', ' + timeText(r.posterTime) : '');
  return 'last frame of the film';
}
function visual(r, withBadge = true) {
  const v = el('div', 'visual');
  if (r.poster) {
    const im = el('img'); im.src = r.poster; im.alt = r.label + ', ' + pictureWords(r); im.loading = 'lazy'; im.decoding = 'async';
    let readout = null;
    im.onerror = () => { im.replaceWith(placeholder(r)); readout?.remove(); };
    v.append(im);
    if (r.posterTime != null) v.append(readout = rich(el('span', 'readout'), timeText(r.posterTime)));
  } else v.append(placeholder(r));
  const cover = r.images ? link('', '#images') : r.variants ? link('', '#film=' + encodeURIComponent(r.id)) : r.viewer ? link('', r.viewer) : null;
  if (cover) {
    cover.setAttribute('aria-label', (r.images ? 'Browse the images of ' : r.variants ? 'Watch the film of ' : 'Open in the 3D viewer: ') + r.label);
    if (r.images) cover.onclick = e => { e.preventDefault(); openImages(r, cover); };
    else if (r.variants) cover.onclick = e => { e.preventDefault(); openFilm(r, cover); };
    v.append(cover);
  }
  if (withBadge) v.append(el('span', 'badge', BADGE[r.kind] || 'Entry'));
  const save = el('button', 'save');
  const paint = () => { const on = saved.has(r.id); save.textContent = on ? '♥' : '♡'; save.setAttribute('aria-pressed', on); save.setAttribute('aria-label', (on ? 'Remove from saved: ' : 'Save: ') + r.label); };
  save.onclick = () => { saved.has(r.id) ? saved.delete(r.id) : saved.add(r.id); storeSaved(); if (state.kind === 'saved') render(); else paint(); };
  paint(); v.append(save);
  return v;
}
function actions(r) {
  const box = el('div', 'card-actions');
  if (r.viewer) box.append(link('Explore 3D', r.viewer));
  if (r.variants) { const b = el('button', '', 'Watch film'); b.onclick = () => openFilm(r, b); box.append(b); }
  if (r.images) { const b = el('button', '', `Browse ${r.images.length} images`); b.onclick = () => openImages(r, b); box.append(b); }
  else if (r.projection) box.append(link('Compare', r.projection));
  return box;
}
function tags(r, extra = []) {
  const box = el('div', 'tags');
  for (const t of [r.chi ? 'χ ' + r.chi : null, levelText(r), r.physics && r.physics !== 'unknown' ? PHYSICS[r.physics] : null, ...extra]) if (t) box.append(rich(el('span'), t));
  return box;
}
function card(r) {
  const c = el('article', 'sim-card'), body = el('div', 'card-body');
  body.append(el('p', 'card-code', r.code), el('h3', '', r.label), tags(r));
  body.append(rich(el('p', 'card-note'), r.status + (r.frames ? ' · ' + r.frames + ' frames' : '')), actions(r));
  c.append(visual(r), body);
  return c;
}

// ------------------------------------------------------------------ the twelve methods and the boundary control
function filterTo(values) {
  Object.assign(state, DEFAULTS, values); syncControls(); shown = 0; render();
  $('library').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
function renderTwelve() {
  const byCode = new Map();
  for (const r of all.filter(r => r.group === 'twelve')) { if (!byCode.has(r.code)) byCode.set(r.code, []); byCode.get(r.code).push(r); }
  const codes = [...byCode.keys()].sort((a, b) => methodIndex(a) - methodIndex(b));
  $('twelveCards').replaceChildren(...codes.map(code => {
    const list = byCode.get(code).sort((a, b) => (b.level === 5) - (a.level === 5) || (b.level ?? 0) - (a.level ?? 0));
    const r = list[0], c = el('article', 'sim-card method'), body = el('div', 'card-body');
    body.append(el('h3', '', r.code), tags(r, [r.frames ? r.frames + ' frames' : null]));
    if (list.length > 1) {
      const also = el('p', 'also', 'Also at');
      for (const o of list.slice(1).sort((a, b) => (a.level ?? 0) - (b.level ?? 0))) {
        const a = link(levelText(o) || o.label, `?code=${encodeURIComponent(code)}&level=${o.level}#library`);
        a.onclick = e => { e.preventDefault(); filterTo({ code, level: String(o.level) }); };
        also.append(a);
      }
      body.append(also);
    }
    body.append(actions(r)); c.append(visual(r, false), body);
    return c;
  }));
  $('twelve').hidden = !codes.length;
  const controls = all.filter(r => r.group === 'boundary').sort((a, b) => String(a.boundary).localeCompare(String(b.boundary)) || (b.level ?? 0) - (a.level ?? 0));
  $('boundaryCards').replaceChildren(...controls.map(r => {
    const c = el('article', 'sim-card'), body = el('div', 'card-body');
    body.append(el('h4', '', [r.code, r.boundary].filter(Boolean).join(' · ')), tags(r), actions(r));
    c.append(visual(r, false), body);
    return c;
  }));
  $('boundary').hidden = !controls.length;
}

// ------------------------------------------------------------------ library
function pageSize() {
  const cols = getComputedStyle($('cards')).gridTemplateColumns.split(' ').filter(Boolean).length || 3;
  return cols * Math.max(3, Math.ceil(24 / cols));
}
function render() {
  const rows = sortRows(all.filter(matches));
  if (!shown) shown = pageSize();
  $('cards').replaceChildren(...rows.slice(0, shown).map(card));
  $('resultCount').textContent = `${rows.length} ${rows.length === 1 ? 'entry' : 'entries'}${rows.length > shown ? ' · showing ' + shown : ''}`;
  const emptySaved = state.kind === 'saved' && saved.size === 0;
  $('empty').hidden = rows.length > 0;
  $('emptyTitle').textContent = emptySaved ? 'Nothing saved yet' : 'No matches';
  $('emptyText').textContent = emptySaved ? 'Use the heart on any card to keep it here. Saved cards stay in this browser.' : 'Try another code, or clear the filters to see the whole library.';
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
function fillOptions(c) {
  const codes = [...new Set(all.map(r => r.code))].sort((a, b) => methodIndex(a) - methodIndex(b) || a.localeCompare(b));
  for (const v of codes) $('code').add(new Option(v, v));
  for (const v of [...new Set(all.map(r => r.chi).filter(Boolean))].sort((a, b) => a - b)) $('chi').add(new Option('χ ' + v, String(v)));
  for (const v of [...new Set(all.map(r => r.level).filter(v => v != null))].sort((a, b) => a - b)) $('level').add(new Option('level ' + v, String(v)));
  for (const v of Object.keys(PHYSICS).filter(p => all.some(r => r.physics === p))) $('physics').add(new Option(PHYSICS[v], v));
  $('runCount').textContent = c.counts.runs; $('codeCount').textContent = c.counts.codes; $('filmCount').textContent = c.counts.films;
}
function reset() { Object.assign(state, DEFAULTS); syncControls(); shown = 0; render(); }

document.querySelectorAll('[data-kind]').forEach(b => b.onclick = () => { state.kind = b.dataset.kind; shown = 0; render(); });
for (const k of FILTERS) $(k).onchange = () => { state[k] = $(k).value; shown = 0; render(); };
let searchTimer;
$('search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.q = $('search').value.trim(); shown = 0; render(); }, 150); };
$('reset').onclick = reset;
$('emptyReset').onclick = () => { if (state.kind === 'saved' && saved.size === 0) { state.kind = 'all'; shown = 0; render(); } else reset(); };
$('more').onclick = () => { const first = shown; shown += pageSize(); render(); $('cards').children[first]?.querySelector('a,button')?.focus({ preventScroll: true }); };
function layout(compact) {
  $('cards').classList.toggle('compact', compact); $('compact').setAttribute('aria-pressed', compact); $('tiles').setAttribute('aria-pressed', !compact);
  try { localStorage.setItem('cloud-studio-compact', String(compact)); } catch { /* storage blocked */ }
}
$('compact').onclick = () => layout(true); $('tiles').onclick = () => layout(false);
try { layout(localStorage.getItem('cloud-studio-compact') === 'true'); } catch { /* storage blocked */ }
document.addEventListener('keydown', e => { if (e.key === '/' && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) && !document.querySelector('dialog[open]')) { e.preventDefault(); $('search').focus(); } });

// ------------------------------------------------------------------ film player
const sourceOf = v => LOCAL && v.localSrc && !triedRemote ? v.localSrc : v.src;
const currentVariant = () => activeFilm.variants[Number($('variant').value) || 0];
function selectVariant() {
  const v = currentVariant(), vid = $('video'); triedRemote = false;
  vid.pause(); const src = sourceOf(v);
  vid.src = src; vid.poster = v.poster || activeFilm.poster || ''; vid.loop = $('loop').checked;
  $('download').href = src; $('download').download = slug(activeFilm.label + ' ' + v.label) + '.mp4';
  setRich($('playerNote'), [v.note, activeFilm.filmNote || activeFilm.note].filter(Boolean).join(' '));
  $('videoError').hidden = true; $('message').textContent = '';
  vid.load(); vid.playbackRate = Number($('rate').value);
  const u = new URL(location); u.searchParams.set('film', activeFilm.id); u.searchParams.set('view', String($('variant').value)); history.replaceState(null, '', u);
}
function openFilm(r, trigger) {
  opener = trigger; activeFilm = r;
  $('playerTitle').textContent = r.label; $('playerCode').textContent = r.code;
  $('variant').replaceChildren(...r.variants.map((v, i) => new Option(v.label, i)));
  const requested = new URL(location).searchParams.get('view');
  if (requested && Number(requested) < r.variants.length) $('variant').value = requested;
  selectVariant();
  if (!$('player').open) $('player').showModal();
  $('closePlayer').focus();
}
$('closePlayer').onclick = () => $('player').close();
$('player').addEventListener('close', () => {
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
  if (LOCAL && v.localSrc && !triedRemote) { triedRemote = true; $('video').src = v.src; $('download').href = v.src; $('video').load(); return; }
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
  $('galleryImage').src = file; $('galleryImage').alt = `${imageRun.label}, picture ${imageIndex + 1} of ${n}`;
  $('imageDownload').href = file; $('imageDownload').download = slug(imageRun.label) + '-' + String(imageIndex + 1).padStart(2, '0') + '.' + (file.split('.').pop() || 'jpg');
  $('imagePosition').textContent = `${imageIndex + 1} of ${n}`;
  $('imagePrev').disabled = imageIndex === 0; $('imageNext').disabled = imageIndex === n - 1;
}
function openImages(r, trigger) {
  imageRun = r; imageIndex = 0; imageOpener = trigger;
  $('imageTitle').textContent = r.label; setRich($('imageNote'), r.note);
  showImage(); $('imageViewer').showModal();
}
$('imagePrev').onclick = () => { imageIndex = Math.max(0, imageIndex - 1); showImage(); };
$('imageNext').onclick = () => { imageIndex = Math.min(imageRun.images.length - 1, imageIndex + 1); showImage(); };
$('closeImages').onclick = () => $('imageViewer').close();
$('imageViewer').addEventListener('close', () => imageOpener?.focus());
$('imageViewer').addEventListener('keydown', e => { if (e.key === 'ArrowLeft') $('imagePrev').click(); if (e.key === 'ArrowRight') $('imageNext').click(); });
$('galleryImage').onerror = () => { $('imageNote').textContent = 'This picture could not load. Try the next one, or the download link.'; };

// ------------------------------------------------------------------ start
fetch('data/studio-catalog.json?v=20261122').then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(c => {
  all = c.entries.map((r, i) => ({ ...r, _i: i }));
  fillOptions(c); syncControls(); renderTwelve(); render();
  const film = all.find(r => r.id === params.get('film') && r.variants);
  if (film) openFilm(film, null);
}).catch(() => { $('resultCount').textContent = 'The library could not load. Refresh the page to try again, or open the archive below.'; });
