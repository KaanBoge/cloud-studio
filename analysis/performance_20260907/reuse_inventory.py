"""Read-only inventory of existing baseline 3D grid runs. No inferred IC pass.

Native output presence and matching input parameters alone do not establish
that a completed run used the corrected IC. Preserved t=0 fields are needed.
"""
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_params import find_params
import h5py

BASES={
 'athpp':Path('/home/kaan/codes/athenapp/runs'),
 'apk':Path('/home/kaan/codes/athenapk/runs'),
 'enzo':Path('/home/kaan/codes/enzo/runs'),
 'athw_flash':Path('/home/kaan/CloudCrushing/A8'),
 'flashx':Path('/home/kaan/codes/flashx/runs'),
 'ramses':Path('/home/kaan/codes/ramses/runs')}
rows=[]
for code,base in BASES.items():
    for run in sorted(base.iterdir()):
        name=run.name
        if not run.is_dir() or not re.search(r'chi(?:10|100|1000)(?:_|$)',name):continue
        if any(x in name for x in ('2D','SMOKE','smoke','RVTEST','WK_','FL_','GPU_','GAL','IC_sharp')):continue
        if code=='athw_flash' and not any(x in name for x in ('F3D','ATHW3D','M3D','LAD_ATHW')):continue
        if code=='flashx' and not any(x in name for x in ('prod3d','POOL_')):continue
        try:p=find_params(str(run))
        except Exception as e:p={'error':str(e)}
        files=[]
        for pat in ('*.athdf','*.phdf','*hdf5_plt_cnt_????','DD????/CW_????','output_?????/info_?????.txt','id0/*.vtk'):
            files.extend(run.glob(pat))
        files=sorted(set(files))
        initial=[];terminal=[]
        for f in files:
            if f.suffix not in ('.athdf','.phdf'):continue
            try:
                with h5py.File(f) as h:
                    if f.suffix=='.athdf':t=float(h.attrs['Time'])
                    else:t=float(h['Info'].attrs['Time'])
                    if abs(t)<1e-12:initial.append(str(f))
                    terminal.append(t)
            except Exception:pass
        rows.append({'code':code,'directory':str(run),'native_snapshots_found':len(files),
                     'parameters':p,'initial_hdf_snapshots':initial,
                     'last_measured_hdf_time':max(terminal) if terminal else None,
                     'first_native_file':str(files[0]) if files else None,
                     'last_native_file':str(files[-1]) if files else None,
                     'status':'not_yet_IC_certified'})
out=Path(__file__).with_name('reuse_inventory.json')
out.write_text(json.dumps(rows,indent=2))
for code in BASES:
    selected=[r for r in rows if r['code']==code]
    print(code,'candidate directories',len(selected),'with native snapshots',sum(r['native_snapshots_found']>0 for r in selected),
          'with >=101 files',sum(r['native_snapshots_found']>=101 for r in selected),
          'with explicit t=0 HDF header',sum(bool(r['initial_hdf_snapshots']) for r in selected))
for r in rows:
    if '/TH_' in r['directory']:
        print(Path(r['directory']).name,'raw',r['native_snapshots_found'],'initial',len(r['initial_hdf_snapshots']))
