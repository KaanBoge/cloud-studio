'use strict';
// Progress log: the runs of the September 2026 velocity setup study, read from data/progress-catalog.json.
(() => {
  const $ = id => document.getElementById(id);
  const CODE = { 'Enzo E': 'Enzo-E', 'Flash X': 'Flash-X', 'Gadget4 SPH': 'GADGET-4', 'Gadget-4': 'GADGET-4', 'FLASH': 'FLASH 4.8' };
  const SETUP = { 'Sharp boundary': 'Sharp edge at 1.3 R', 'Earlier smooth edge': 'Earlier smooth edge', 'Earlier outer momentum': 'Earlier outer momentum' };
  const SETUP_NOTE = { 'Sharp boundary': 'Velocity zero inside 1.3 cloud radii', 'Earlier smooth edge': 'Velocity follows the tanh density edge', 'Earlier outer momentum': 'Constant momentum outside the cloud' };
  const code = r => CODE[r.code] || r.code;
  const number = v => Number(v).toLocaleString('en-US');
  let runs = [];
  function node(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
  function cell(main, sub) { const c = node('td'); c.append(node('strong', main)); if (sub) { const s = node('span', undefined, 'detail'); s.append(...[].concat(sub)); c.append(s); } return c; }
  function tcc(t) { const s = node('sub', 'cc'); return [`to ${t} t`, s]; }
  function duration(s) {
    if (!Number.isFinite(Number(s))) return '';
    s = Math.round(s); if (s < 60) return `${s} s`;
    const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = s % 60;
    return h ? `${h} h ${m} min` : `${m} min ${sec} s`;
  }
  function grid(level) { return `${2 ** (level + 3)} × ${2 ** (level + 2)} × ${2 ** (level + 2)}`; }
  function option(select, value, label) { const e = node('option', label); e.value = value; $(select).append(e); }

  function render() {
    const search = $('search').value.trim().toLowerCase(), c = $('code').value, level = $('level').value, sort = $('sort').value;
    const rows = runs.filter(r => (!c || code(r) === c) && (!level || r.level === Number(level)) &&
      (!search || `${code(r)} ${SETUP[r.law] || r.law}`.toLowerCase().includes(search)));
    rows.sort((a, b) => sort === 'slow' ? b.native_seconds - a.native_seconds
      : sort === 'level' ? b.level - a.level || code(a).localeCompare(code(b))
      : code(a).localeCompare(code(b)) || a.level - b.level || String(a.law).localeCompare(String(b.law)));
    const body = rows.map(r => {
      const tr = node('tr');
      tr.append(cell(code(r), r.hardware === 'GPU' ? 'Graphics card' : 'Processor'),
        cell(SETUP[r.law] || r.law, SETUP_NOTE[r.law]),
        cell(`Level ${r.level}`, grid(r.level)),
        cell(`χ ${number(r.chi)}`, `Mach ${number(r.mach)}`),
        cell(duration(r.native_seconds)),
        cell(String(r.frames), tcc(5)));
      return tr;
    });
    if (body.length) $('runs').replaceChildren(...body);
    else { const tr = node('tr'), td = node('td', 'No runs match these choices.'); td.colSpan = 6; tr.append(td); $('runs').replaceChildren(tr); }
    $('shown').textContent = `${rows.length} of ${runs.length} runs shown`;
  }

  async function init() {
    try {
      const response = await fetch('data/progress-catalog.json');
      if (!response.ok) throw new Error('catalog unavailable');
      const data = await response.json();
      if (!Array.isArray(data.runs)) throw new Error('unexpected catalog');
      runs = data.runs.filter(r => Number.isFinite(r.native_seconds) && Number.isInteger(r.frames));
      const seconds = runs.reduce((a, r) => a + r.native_seconds, 0);
      $('n-runs').textContent = number(runs.length);
      $('n-codes').textContent = number(new Set(runs.map(code)).size);
      $('n-states').textContent = number(runs.reduce((a, r) => a + r.frames, 0));
      $('n-time').textContent = (seconds / 3600).toFixed(1) + ' h';
      for (const name of [...new Set(runs.map(code))].sort((a, b) => a.localeCompare(b))) option('code', name, name);
      for (const level of [...new Set(runs.map(r => r.level))].sort((a, b) => a - b)) option('level', level, `Level ${level}`);
      render();
    } catch {
      $('shown').textContent = 'The run list is available as a JSON download below.';
    }
  }
  for (const id of ['code', 'level', 'sort']) $(id).addEventListener('change', render);
  $('search').addEventListener('input', render);
  init();
})();
