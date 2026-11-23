'use strict';
// Research page: the analysis file list loads only when its section is opened.
(() => {
  const byId = id => document.getElementById(id);
  const number = value => Number(value).toLocaleString('en-US');
  const size = value => value >= 1e9 ? (value / 1e9).toFixed(2) + ' GB' : value >= 1e6 ? (value / 1e6).toFixed(2) + ' MB' : (value / 1e3).toFixed(1) + ' KB';
  const REPO = 'https://github.com/KaanBoge/cloud-studio/blob/main/';
  function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
  function message(text) { const row = node('tr'), cell = node('td', text); cell.colSpan = 3; row.append(cell); byId('file-rows').replaceChildren(row); }

  const details = byId('files');
  if (!details) return;
  let files = null, limit = 40, loading = false;

  function render() {
    if (!files) return;
    const query = byId('file-search').value.trim().toLowerCase(), kind = byId('file-kind').value;
    const matches = files.filter(f => (!query || f.path.toLowerCase().includes(query)) && (!kind || f.kind === kind));
    const rows = matches.slice(0, limit).map(file => {
      const row = node('tr'), name = node('td'), link = node('a', file.path.split('/').pop());
      link.href = REPO + file.path;
      name.append(link, node('span', file.path, 'path'));
      row.append(name, node('td', (file.kind || 'file').toUpperCase()), node('td', size(file.bytes)));
      return row;
    });
    if (rows.length) byId('file-rows').replaceChildren(...rows);
    else message('No files match. Try another code name or file type.');
    byId('file-count').textContent = number(matches.length) + (matches.length === 1 ? ' file' : ' files');
    byId('more-files').hidden = matches.length <= limit;
  }

  async function load() {
    if (files || loading) return;
    loading = true;
    byId('file-count').textContent = 'Loading the file list';
    try {
      const response = await fetch('data/research-files.json');
      if (!response.ok) throw new Error('list unavailable');
      const data = await response.json();
      files = Array.isArray(data.files) ? data.files : [];
      render();
    } catch {
      byId('file-count').textContent = 'The list is also available as a CSV download.';
      message('Use the CSV download above to see every file.');
    } finally { loading = false; }
  }

  details.addEventListener('toggle', () => { if (details.open) load(); });
  if (details.open) load();
  byId('file-search').addEventListener('input', () => { limit = 40; render(); });
  byId('file-kind').addEventListener('change', () => { limit = 40; render(); });
  byId('more-files').addEventListener('click', () => { limit += 80; render(); });
})();
