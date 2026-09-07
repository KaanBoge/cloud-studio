"""Prepare (never launch) the 12 measured-profile code/level/chi combinations."""
import subprocess
import sys
import json
from pathlib import Path
from run_optimized import ROOTS, IC_VERSION
here=Path(__file__).resolve().parent
profiles=json.loads((here/'optimized_profiles.json').read_text())
for code in ('athpp','apk'):
    for level in (5,6):
        for chi in (10,100,1000):
            command=[sys.executable,str(here/'run_optimized.py'),'--code',code,'--level',str(level),'--chi',str(chi)]
            prefix=profiles[f'{code}_L{level}'].get('directory_prefix','OPT')
            if (ROOTS[code]/f'{prefix}_{IC_VERSION}_L{level}_chi{chi}').exists():command.append('--resume-prepared')
            subprocess.run(command,check=True)
