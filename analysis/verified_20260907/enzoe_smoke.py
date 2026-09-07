"""Native Enzo-E 3D input with a masked sharp velocity boundary."""
import json
import math
import subprocess
from pathlib import Path
import h5py
import numpy as np

ROOT = Path('/home/kaan/ic_audit_20260907/enzoe_tests_v2')
VW = 2*math.sqrt(5/3)
results=[]
for chi in (10,100,1000):
    run=ROOT/f'chi{chi}'
    run.mkdir(parents=True,exist_ok=False)
    density=f'(1.0 + {chi-1}.0 * 0.5 * (1.0 - tanh((sqrt(x*x+y*y+z*z) - 1.0) / 0.1)))'
    energy=f'1.5/{density}'
    text=f'''# Audit test only. Density tanh, sharp velocity boundary at 1.3 R.
Domain {{ lower = [-3.0,-5.0,-5.0]; upper = [17.0,5.0,5.0]; }}
Mesh {{ root_rank=3; root_size=[64,32,32]; root_blocks=[2,1,1]; }}
Field {{ list=["density","velocity_x","velocity_y","velocity_z","total_energy","internal_energy","pressure"]; ghost_depth=4; gamma=1.6666666666666667; }}
Method {{ list=["ppm"]; ppm {{ courant=0.4; diffusion=true; flattening=3; steepening=true; dual_energy=false; }} }}
Initial {{ list=["value"]; value {{
 density=[{density}];
 velocity_x=[0.0, (x*x+y*y+z*z <= 1.69), {VW}];
 velocity_y=0.0; velocity_z=0.0;
 internal_energy=[{energy}];
 total_energy=[{energy}, (x*x+y*y+z*z <= 1.69), {energy}+{0.5*VW*VW}];
}} }}
Boundary {{ list=["inflow","outflow","yedge","zedge"];
 inflow {{ type="inflow"; axis="x"; face="lower";
 value {{ density=1.0; velocity_x={VW}; velocity_y=0.0; velocity_z=0.0; internal_energy=1.5; total_energy={1.5+0.5*VW*VW}; }} }}
 outflow {{ type="outflow"; axis="x"; face="upper"; }}
 yedge {{ type="outflow"; axis="y"; }} zedge {{ type="outflow"; axis="z"; }}
}}
Stopping {{ time=0.001; cycle=2; }}
Output {{ list=["data"]; data {{ type="data"; field_list=["density","velocity_x","velocity_y","velocity_z","total_energy","internal_energy","pressure"];
name=["ic-%03d-p%02d.h5","count","proc"]; schedule {{ var="time"; step=0.001; }} }} }}
'''
    (run/'cloud.in').write_text(text)
    with open(run/'run.log','x') as log:
        rc=subprocess.run(['/home/kaan/codes/enzoe/enzo-e/build/bin/enzo-e','cloud.in','+p1'],cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
    result={'chi':chi,'solver_returncode':rc,'outputs':[str(p) for p in run.glob('*.h5')]}
    if rc:
        result['log_tail']=(run/'run.log').read_text(errors='replace')[-1800:]
    results.append(result)
    print(json.dumps(result),flush=True)
(ROOT/'results.json').write_text(json.dumps(results,indent=2))
