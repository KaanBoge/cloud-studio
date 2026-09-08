"""Launch the validated bounded queue detached from the chat tool process."""
import json
import os
from pathlib import Path
import subprocess
import time
import psutil
ROOT=Path('/home/kaan/sensitivity_20260907/athw')
SCRIPT='/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/athw/run_athw.py'
record=ROOT/'worker.json'
if record.exists():
    old=json.loads(record.read_text())
    if psutil.pid_exists(old['pid']):
        p=psutil.Process(old['pid'])
        if SCRIPT in p.cmdline():raise RuntimeError('Queue already running')
    raise RuntimeError('Previous worker exists; inspect before relaunch')
proof=json.loads((ROOT/'smoke_batch.json').read_text())
if proof['status']!='complete_native_checks':raise RuntimeError('Native smoke validation missing')
with (ROOT/'worker.log').open('x') as log:
    proc=subprocess.Popen(['/home/kaan/venv/bin/python',SCRIPT],stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
record.write_text(json.dumps(dict(pid=proc.pid,started_unix=time.time(),script=SCRIPT),indent=2))
time.sleep(1)
if proc.poll() is not None:raise RuntimeError('Worker exited; inspect worker.log')
print(record.read_text())
