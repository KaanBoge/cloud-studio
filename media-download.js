// Cross-origin media needs a local blob URL for the download attribute to work.
document.addEventListener('click', async event => {
  const link = event.target.closest('a[download]');
  if (!link || !link.href || new URL(link.href).origin === location.origin) return;
  event.preventDefault();
  if (link.dataset.busy) return;
  const label = link.textContent, source = link.href, name = link.download;
  link.dataset.busy = 'true'; link.textContent = 'Preparing download…';
  try {
    const response = await fetch(source);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const blob = await response.blob(), url = URL.createObjectURL(blob);
    const save = document.createElement('a'); save.href = url; save.download = name;
    document.body.append(save); save.click(); save.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    const status = document.getElementById('message');
    if (status) status.textContent = 'Download failed. Please retry, or choose an original video.';
  } finally { delete link.dataset.busy; link.textContent = label; }
});
