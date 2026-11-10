"""Split the existing media tree into resumable, fast-forward upload batches.

Reuses already verified Git blobs; does not reread or re-encode videos.
The final tree is exactly the original packaged tree.
"""
from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent/'CloudStudio-60fps.git'
def git(*args,data=None):
    return subprocess.check_output(['git','--git-dir',str(REPO),*args],input=data).decode().strip()
record_path=ROOT/'analysis/media60_publication.json'
record=json.loads(record_path.read_text())
old=record['commit']
if record.get('upload_commits'):
    print(json.dumps(record));raise SystemExit
receipt=json.loads((ROOT/'analysis/smooth60_receipt.json').read_text())['files']
sizes={Path(v['src']).name:v['bytes'] for v in receipt.values()}
entries=git('ls-tree',old).splitlines()
batches=[];batch=[];size=0
for entry in entries:
    name=entry.split('\t',1)[1];n=sizes.get(name,0)
    if batch and size+n>128*1024**2:
        batches.append(batch);batch=[];size=0
    batch.append(entry);size+=n
if batch:batches.append(batch)
all_entries=[];commits=[];parent=None
for i,batch in enumerate(batches):
    all_entries.extend(batch)
    tree=git('mktree',data=('\n'.join(all_entries)+'\n').encode())
    parent=git('commit-tree',tree,*(['-p',parent] if parent else []),data=f'Add smooth movie previews, batch {i+1} of {len(batches)}\n'.encode())
    commits.append(parent)
assert git('rev-parse',parent+'^{tree}')==git('rev-parse',old+'^{tree}')
git('update-ref','refs/heads/media-60fps-single',old)
git('update-ref','refs/heads/media-60fps',parent,old)
record.update(commit=parent,upload_commits=commits,identical_media_tree=True)
record_path.write_bytes(json.dumps(record,indent=2).encode())
manifest=ROOT/'data/smooth60.json'
manifest.write_bytes(manifest.read_text().replace('/'+old+'/', '/'+parent+'/').encode())
print(json.dumps({'commit':parent,'batches':len(batches),'bytes':record['bytes']}))
