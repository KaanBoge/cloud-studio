"""Read-only audit: existing byte-identical Windows copies of rendered PNGs only."""
import hashlib,json,os,stat
from pathlib import Path

RESULTS=Path('/mnt/c/Users/kaanb/CloudCrushing/results_A8')
ROOTS=[Path('/home/kaan/CloudCrushing/A8'),Path('/home/kaan/codes/athenapk/runs'),Path('/home/kaan/codes/athenapp/runs')]
DEST=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/gadget4/render_duplicate_audit.json')

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

if DEST.exists():raise ValueError('Existing audit must be retained')
rows=[];checked=0;bytes_checked=0
for backup_dir in sorted(RESULTS.iterdir()):
    if not backup_dir.is_dir() or backup_dir.is_symlink():continue
    for root in ROOTS:
        source_dir=root/backup_dir.name
        if not source_dir.is_dir() or source_dir.is_symlink():continue
        if source_dir.resolve().parent!=root.resolve():raise ValueError('Unexpected source mapping')
        for source in sorted(source_dir.glob('*.png')):
            backup=backup_dir/source.name
            if source.is_symlink() or backup.is_symlink() or not backup.is_file():continue
            s=source.stat();b=backup.stat()
            if not stat.S_ISREG(s.st_mode) or not stat.S_ISREG(b.st_mode) or s.st_size!=b.st_size:continue
            checked+=1;bytes_checked+=s.st_size;digest=sha(source)
            if digest!=sha(backup):continue
            rows.append(dict(source=str(source.resolve()),backup=str(backup.resolve()),sha256=digest,
                bytes=s.st_size,allocated_bytes=s.st_blocks*512,source_device=s.st_dev,backup_device=b.st_dev,
                source_inode=s.st_ino,backup_inode=b.st_ino))
report=dict(status='audit_only_nothing_deleted',scope='Only immediate PNG rendering files with pre-existing byte-identical Windows result copies; no native fields, ICs, restart files, logs or metadata.',
    roots=[str(p) for p in ROOTS],backup_root=str(RESULTS),matches=rows,count=len(rows),
    source_bytes=sum(r['bytes'] for r in rows),source_allocated_bytes=sum(r['allocated_bytes'] for r in rows),
    hash_candidates_checked=checked,bytes_hashed_each_side=bytes_checked)
with DEST.open('x') as out:json.dump(report,out,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='matches'},indent=2))
