"""Commit rebuilt 60 fps previews to the media-60fps branch in upload batches.

Each batch commit replaces up to 128 MiB of previews, so every push stays small.
The last commit holds exactly the previews listed in the receipt, the README and
the manifest. The website manifest is then pinned to that last commit.
Does not upload anything and does not change the source movies.
"""
from pathlib import Path
import json, subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent / 'CloudStudio-60fps.git'
REF = 'refs/heads/media-60fps'
LIMIT = 128 * 1024**2


def git(*args, data=None):
    return subprocess.check_output(['git', '--git-dir', str(REPO), *args], input=data).decode().strip()


receipt = json.loads((ROOT / 'analysis/smooth60_receipt.json').read_text())
files = receipt['files']
record_path = ROOT / 'analysis/media60_publication.json'
record = json.loads(record_path.read_text())
old = git('rev-parse', REF)
assert old == record['commit'], 'media branch moved since the last publication'
footers = {r.get('footer') for r in files.values()}
assert len(footers) == 1 and None not in footers, footers

blobs = {}
for original, r in sorted(files.items()):
    source = ROOT / r['src']
    assert source.parent == ROOT / 'assets/smooth60' and (ROOT / original).exists()
    assert source.stat().st_size == r['bytes'] < 100 * 1024**2 and r['fps'] == [60.0]
    blobs[source.name] = (git('hash-object', '-w', '--', str(source)), r['bytes'])

readme = f'''Cloud Studio 60 fps display previews

{len(files)} silent H.264 previews of the movies published on main.
Blended frames are display transitions, not additional simulation states.
Each preview carries the footer "{footers.pop()}".
The original movies stay on main and no simulation data is changed.
The main branch pins these files to this exact media commit.
'''.encode()
extra = {
    'README.txt': git('hash-object', '-w', '--stdin', data=readme),
    'manifest.json': git('hash-object', '-w', '--stdin', data=json.dumps(receipt, indent=2).encode()),
}

tree = {}
for line in git('ls-tree', old).splitlines():
    meta, name = line.split('\t', 1)
    tree[name] = meta.split()[2]
changed = [n for n in sorted(blobs) if tree.get(n) != blobs[n][0]]
batches, batch, size = [], [], 0
for name in changed:
    if batch and size + blobs[name][1] > LIMIT:
        batches.append(batch); batch, size = [], 0
    batch.append(name); size += blobs[name][1]
batches.append(batch)


def mktree(entries):
    return git('mktree', data=''.join(f'100644 blob {b}\t{n}\n' for n, b in sorted(entries.items())).encode())


final = {n: b for n, (b, _) in blobs.items()} | extra
if mktree(final) == git('rev-parse', old + '^{tree}'):
    print(json.dumps(dict(commit=old, unchanged=True)))
    raise SystemExit
removed = sorted(set(tree) - set(final))
commits, parent = [], old
for i, batch in enumerate(batches):
    for name in batch:
        tree[name] = blobs[name][0]
    message = f'Rebuild the movie previews with a new footer, batch {i + 1} of {len(batches)}\n'
    if i == len(batches) - 1:
        tree = final
        if removed:
            message += f'\nLeaves out the {len(removed)} earlier film previews that the site no longer uses; they remain in the history.\n'
    parent = git('commit-tree', mktree(tree), '-p', parent, data=message.encode())
    commits.append(parent)
git('update-ref', REF, parent, old)

public = {}
for original, r in files.items():
    public[original] = {k: r[k] for k in ('fps', 'duration', 'width', 'height', 'method')}
    public[original].update(localSrc=r['src'], src=f'https://raw.githubusercontent.com/KaanBoge/cloud-studio/{parent}/{Path(r["src"]).name}')
(ROOT / 'data/smooth60.json').write_bytes(json.dumps(public, separators=(',', ':')).encode())
summary = dict(commit=parent, branch='media-60fps', files=len(files), bytes=sum(r['bytes'] for r in files.values()),
               previous_commit=old, upload_commits=commits, footer=receipt['files'][next(iter(files))]['footer'])
record_path.write_bytes(json.dumps(summary, indent=2).encode())
print(json.dumps(dict(commit=parent, batches=len(batches), changed=len(changed), bytes=summary['bytes'])))
