"""Retarget only untouched, resource-held L5 GPU jobs to tested lossless IO."""
import fcntl
import json
from pathlib import Path
import sys
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/restart_20260907')
import queue_more as m

with (m.WORK/'worker.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=json.loads(m.MANIFEST.read_text())
    oldfile=Path('/home/kaan/performance_20260907c/queue_before_l5_io.json')
    if oldfile.exists():raise RuntimeError('Queue migration already attempted')
    oldfile.write_text(json.dumps(manifest,indent=2))
    count=0
    for i,job in enumerate(manifest['jobs']):
        if job['code']!='apk' or job['level']!=5:continue
        if job['status']!='held_resources':raise RuntimeError('Job is not safely held')
        old=Path(job['directory'])
        if {f.name for f in old.iterdir()}!={'athinput','provenance.json'}:
            raise RuntimeError('Existing output in old prepared directory')
        replacement=m.definition('apk',5,job['chi'])
        replacement.update(status='held_resources',reason=job['reason'],
                           supersedes_prepared_directory=str(old),
                           optimization='Tested lossless prim compression 1; unchanged physics and cadence')
        manifest['jobs'][i]=replacement;count+=1
    if count!=3:raise RuntimeError('Unexpected migration count')
    m.q.save(m.MANIFEST,manifest)
    print('Updated three held L5 GPU jobs; old preparations and all raw data retained.')
