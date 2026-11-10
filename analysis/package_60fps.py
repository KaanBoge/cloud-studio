"""Create the media-only Git commit and pin the website manifest to that commit.

Does not change the worktree/index, upload anything, or modify source movies.
Push refs/heads/media-60fps before publishing the main site.
"""
from pathlib import Path
import json, subprocess, os

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
MEDIA_REPO = ROOT.parent / 'CloudStudio-60fps.git'
if not MEDIA_REPO.exists():
    subprocess.run(['git', 'init', '--bare', str(MEDIA_REPO)], check=True, capture_output=True)
    for key in ('user.name', 'user.email', 'credential.helper'):
        value = subprocess.check_output(['git', 'config', '--get', key]).decode().strip()
        subprocess.run(['git', '--git-dir', str(MEDIA_REPO), 'config', key, value], check=True)
    subprocess.run(['git', '--git-dir', str(MEDIA_REPO), 'remote', 'add', 'origin', 'https://github.com/KaanBoge/cloud-studio.git'], check=True)

def git(*args, data=None):
    return subprocess.check_output(['git', '--git-dir', str(MEDIA_REPO), *args], input=data).decode().strip()

receipt = json.loads(Path('analysis/smooth60_receipt.json').read_text())
files = receipt['files']
assert len(files) == 476
entries = []
for original, record in sorted(files.items()):
    source = Path(record['src'])
    assert source.parent == Path('assets/smooth60')
    assert source.stat().st_size == record['bytes'] < 100 * 1024**2
    assert record['fps'] == [60.0]
    blob = git('hash-object', '-w', '--', str(source))
    entries.append(f'100644 blob {blob}\t{source.name}\n')
readme = b'''Cloud Studio 60 fps display previews

476 silent H.264 derivatives of the original published movies.
Crossfades are display transitions, not additional simulated fluid states.
Original movies remain on main. No raw simulation fields are modified.
The main-branch manifest pins these files to this exact media commit.
'''
blob = git('hash-object', '-w', '--stdin', data=readme)
entries.append(f'100644 blob {blob}\tREADME.txt\n')
blob = git('hash-object', '-w', '--stdin', data=json.dumps(receipt, indent=2).encode())
entries.append(f'100644 blob {blob}\tmanifest.json\n')
tree = git('mktree', data=''.join(entries).encode())
ref = 'refs/heads/media-60fps'
exists = subprocess.run(['git', '--git-dir', str(MEDIA_REPO), 'rev-parse', '--verify', ref], capture_output=True, text=True)
old = exists.stdout.strip() if exists.returncode == 0 else None
if old and git('rev-parse', old + '^{tree}') == tree:
    commit = old
else:
    parents = ['-p', old] if old else []
    commit = git('commit-tree', tree, *parents, data=b'Add verified 60 fps blended display previews\n')
    git('update-ref', ref, commit, old or '0' * 40)
public = {}
for original, record in files.items():
    public[original] = {k: record[k] for k in ('fps', 'duration', 'width', 'height', 'method')}
    public[original].update(localSrc=record['src'], src=f'https://raw.githubusercontent.com/KaanBoge/cloud-studio/{commit}/{Path(record["src"]).name}')
Path('data/smooth60.json').write_text(json.dumps(public, separators=(',', ':')), encoding='utf-8',newline='\n')
summary = dict(commit=commit, branch='media-60fps', files=len(files), bytes=sum(r['bytes'] for r in files.values()))
Path('analysis/media60_publication.json').write_text(json.dumps(summary, indent=2), encoding='utf-8',newline='\n')
print(json.dumps(summary))
