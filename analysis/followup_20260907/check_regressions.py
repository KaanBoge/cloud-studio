"""Exercise the corrected figure gates on retained native audit diagnostics."""
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,'/home/kaan/verified_20260907')
from figure1_v2 import select_panels
from figure2_v2 import load_runs
from comparison_checks import require_common_physics

ROOT=Path('/home/kaan/ic_audit_20260907/grid_tests')
WORK=Path('/home/kaan/followup_20260907/evidence')
files=sorted(ROOT.glob('*/mass_diagnostics_v2.json'))
data=[json.loads(p.read_text()) for p in files]
require_common_physics(data)
print('Physical checks passed on',len(data),'retained native diagnostic sequences',flush=True)
chosen=[ROOT/f'{code}_chi10/mass_diagnostics_v2.json' for code in ('athpp','apk')]
plan={'panels':[{'diagnostics':str(p),'center_code':[0,0,0]} for p in chosen]}
try:select_panels(plan,5,1e-5)
except ValueError:print('Missing late comparison time correctly rejected',flush=True)
else:raise AssertionError('Missing time accepted')
planfile=WORK/'figure_plan.json';planfile.write_text(json.dumps(plan,indent=2))
commands=[['figure1_v2.py','--plan',str(planfile),'--time','0','--out',str(WORK/'initial_audit_3d.png')],
          ['figure2_v2.py','--out',str(WORK/'short_audit_mass.png'),*[str(p) for p in chosen]]]
for c in commands:
    subprocess.run([sys.executable,str(Path('/home/kaan/verified_20260907')/c[0]),*c[1:]],check=True)
(WORK/'comparison_regression.json').write_text(json.dumps({'passed':True,'native_sequences_checked':len(data),
    'figures':['initial_audit_3d.png','short_audit_mass.png'],
    'scope':'Retained short IC audit outputs, not late-time production figures'},indent=2))
