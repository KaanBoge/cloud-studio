"""Demonstrate incompatibility from native t=0 samples; never certify whole runs.

Use only preserved native data. A small sample passing is not a full IC pass.
"""
import json
import math
from pathlib import Path
import sys
import numpy as np
import yt
yt.set_log_level(40)
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_params import parse_file
rows=json.loads(Path(__file__).with_name('reuse_inventory.json').read_text())
chosen=['ATHPP3D_chi10_256','ATHPP3D_chi100_256','M3D_L3_chi10','M3D_L3_chi100','M3D_L3_chi1000',
        'CW3D_chi10_256','prod3d_chi10','M3D_FLASH48_L5_chi10','M3D_ATHW_L5_chi10']
reports=[]
for row in rows:
    if Path(row['directory']).name not in chosen:continue
    item={'directory':row['directory'],'assessment':'not_classified'}
    try:
        p=row['parameters'];R=p['r_cloud'];vw=p['v_wind'];chi=p['chi'];rw=p['rho_wind']
        if any(v is None for v in (R,vw,chi,rw)):raise ValueError('Missing parameters')
        fn=row['initial_hdf_snapshots'][0] if row['initial_hdf_snapshots'] else row['first_native_file']
        ds=yt.load(fn);t=float(ds.current_time.to_value('code_time'))
        if abs(t)>1e-10:raise ValueError(f'Preserved output is not initial: time={t}')
        center=np.array([.3,.5,.5] if '/M3D_FLASH48_' in row['directory'] else [0,0,0])
        # Axis choice avoids accidentally sampling along a degenerate direction.
        ray=ds.ray(center,center+np.array([0,0,2*R]))
        xyz=np.stack([ray['index',a].to_value('code_length') for a in 'xyz'],axis=1)
        r=np.linalg.norm(xyz-center,axis=1)
        axis='y' if row['code']=='apk' else 'x'
        v=ray['gas','velocity_'+axis].to_value('code_velocity')
        rho=ray['gas','density'].to_value('code_density')
        sharp=np.where(r>1.3*R,vw,0)
        tanh=vw*.5*(1+np.tanh((r/R-1.3)/.1))
        moment=np.where(r>1.3*R,rw*vw/rho,0)
        errors={'sharp_velocity':float(np.max(abs(v-sharp))/vw),
                'tanh_velocity':float(np.max(abs(v-tanh))/vw),
                'tanh_velocity_at_density_edge':float(np.max(abs(v-vw*.5*(1+np.tanh((r/R-1)/.1))))/vw),
                'constant_momentum_exterior':float(np.max(abs(v-moment))/vw)}
        item.update(time=t,snapshot=fn,sampled_cells=len(r),errors=errors,
            assessment='incompatible_with_corrected_sharp_velocity' if errors['sharp_velocity']>3e-5 else 'sample_consistent_only_not_certified',
            identified_sampled_law=min(errors,key=errors.get) if min(errors.values())<3e-5 else 'none_of_tested_laws')
    except Exception as e:item['reason']=str(e)
    reports.append(item);print(json.dumps(item),flush=True)
Path(__file__).with_name('reuse_sample_results.json').write_text(json.dumps(reports,indent=2))
