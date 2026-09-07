"""Prepare (never launch) the 12 measured-profile code/level/chi combinations."""
import subprocess
import sys
from pathlib import Path
from run_optimized import ROOTS, IC_VERSION
here=Path(__file__).resolve().parent
for code in ('athpp','apk'):
    for level in (5,6):
        for chi in (10,100,1000):
            command=[sys.executable,str(here/'run_optimized.py'),'--code',code,'--level',str(level),'--chi',str(chi)]
            if (ROOTS[code]/f'OPT_{IC_VERSION}_L{level}_chi{chi}').exists():command.append('--resume-prepared')
            subprocess.run(command,check=True)
