// Films and pictures served from another address ignore the download attribute,
// so fetch them and save a local copy under the name the link asks for.
document.addEventListener('click', async event => {
  const link = event.target.closest('a[download]');
  if (!link || !link.href || new URL(link.href, location.href).origin === location.origin) return;
  event.preventDefault();
  if (link.dataset.busy) return;
  const label = link.textContent, source = link.href, name = link.download || source.split('/').pop();
  link.dataset.busy = 'true'; link.setAttribute('aria-busy', 'true'); link.textContent = 'Preparing the download';
  try {
    const response = await fetch(source);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const blob = await response.blob(), url = URL.createObjectURL(blob);
    const save = document.createElement('a'); save.href = url; save.download = name;
    document.body.append(save); save.click(); save.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    const status = document.getElementById('message');
    if (status) status.textContent = 'The download did not start. Try again, or choose another version.';
  } finally { delete link.dataset.busy; link.removeAttribute('aria-busy'); link.textContent = label; }
});
