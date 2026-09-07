import json
import subprocess
from pathlib import Path
import numpy as np
import yt
from grid_smokes import set_flat,VW
root=Path('/home/kaan/ic_audit_20260907/ramses_rect_tests')
template=Path('/home/kaan/codes/ramses/runs/RAM3D_chi10/RAM3D_chi10.nml').read_text()
template=template[template.index('&RUN_PARAMS'):]
for chi in (10,100,1000):
    run=root/f'chi{chi}'
    run.mkdir(parents=True,exist_ok=False)
    text=set_flat(template,{'levelmin':5,'levelmax':5,'ngridmax':100000,'chi':chi,'y_cloud':5,'z_cloud':5,
        'v_wind':repr(VW),'u_bound':repr(VW),'tend':.001,'delta_tout':.001,'courant_factor':.4})
    text=text.replace('&AMR_PARAMS','&AMR_PARAMS\nnx=2\nny=1\nnz=1')
    (run/'run.nml').write_text(text)
    with (run/'run.log').open('x') as log:
        rc=subprocess.run(['mpirun','-np','1','/home/kaan/ic_audit_20260907/bin/ramses_rect','run.nml'],cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
    result={'chi':chi,'returncode':rc,'snapshots':[str(p) for p in run.glob('output_*/info_*.txt')]}
    if not result['snapshots']:
        result['log_tail']=(run/'run.log').read_text(errors='replace')[-1600:]
    else:
        ds=yt.load(result['snapshots'][0]); ad=ds.all_data()
        result['time']=float(ds.current_time)
        result['domain']=[ds.domain_left_edge.tolist(),ds.domain_right_edge.tolist()]
        result['cells']=len(ad['gas','density'])
        result['units']={k:str(getattr(ds,k)) for k in ('length_unit','velocity_unit','density_unit','time_unit')}
        result['boxlen']=ds.parameters.get('boxlen')
        result['coordinate_range']=[float(ad['index','x'].min()),float(ad['index','x'].max())]
    print(json.dumps(result),flush=True)
    (run/'inspection.json').write_text(json.dumps(result,indent=2))
