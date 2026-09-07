"""Persistent finite benchmark driver; does not queue production simulations."""
import json
from pathlib import Path
import subprocess
import sys
import time
here=Path(__file__).resolve().parent
work=Path('/home/kaan/performance_20260907b');work.mkdir(exist_ok=True)
state=work/'driver_status.json'
commands=[['bash',str(here/'build_lto.sh')],
          [sys.executable,str(here/'bench.py'),'cpu_sweep'],
          [sys.executable,str(here/'bench.py'),'gpu_io'],
          [sys.executable,str(here/'bench.py'),'confirm'],
          [sys.executable,str(here/'verify.py')]]
records=[]
try:
    with (work/'driver.log').open('a') as log:
        for command in commands:
            state.write_text(json.dumps(dict(status='running',command=command,completed=records,updated=time.time()),indent=2))
            rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
            records.append(dict(command=command,rc=rc,finished=time.time()))
            if rc:raise RuntimeError(f'Command failed with {rc}')
    state.write_text(json.dumps(dict(status='complete',completed=records,updated=time.time()),indent=2))
except Exception as e:
    state.write_text(json.dumps(dict(status='failed',error=str(e),completed=records,updated=time.time()),indent=2))
    raise
