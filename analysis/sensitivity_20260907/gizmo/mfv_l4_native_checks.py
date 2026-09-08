"""New L4 native readers; no changes to frozen L3 helpers or native fields."""
import gc
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np

PREP=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/sharp_prepare_runner_v1')
sys.path.insert(0,str(PREP))
import mfv_sharp_prepare as prior
from mfv_short_controls import FIELDS, parameters, mass_account, check
from diagnose_mfv_restart import layouts, parse_dwarf

N=524288
DIMS=(128,64,64)
DX=20/128
BINARY=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/repaired/GIZMO_repaired')
BINARY_SHA='4784336422c25db4714c6f56ef95337347f4be18dfd622e2b7e9acf7e1fe3d3c'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def safe(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [safe(v) for v in value]
    return value


def save(path,value):
    with Path(path).open('x') as stream:json.dump(safe(value),stream,indent=2,allow_nan=False)


def validate_arrays(a,native=True):
    check(all(np.isfinite(v).all() for v in a.values()),'Nonfinite field')
    check('ParticleIDs' in a and np.array_equal(a['ParticleIDs'],np.arange(1,N+1)),'Wrong L4 IDs/count')
    if native:
        check({k:str(v.dtype) for k,v in a.items()}==FIELDS,'Wrong native L4 field schema')
        for key in ('Masses','Density','InternalEnergy','SmoothingLength'):
            check((a[key]>0).all(),'Nonpositive '+key)
        check((a['Coordinates']>=0).all() and (a['Coordinates']<=[20,10,10]).all(),'Native bounds')


def read(path,native=True):
    with h5py.File(path) as h:
        check(int(h['Header'].attrs['NumPart_Total'][0])==N and int(h['Header'].attrs['NumFilesPerSnapshot'])==1,'Wrong header count/files')
        a={k:v[:] for k,v in h['PartType0'].items()};t=float(h['Header'].attrs['Time'])
    order=np.argsort(a['ParticleIDs']);a={k:v[order] for k,v in a.items()}
    validate_arrays(a,native);check(math.isfinite(t) and t>=0,'Invalid header time')
    return a,t


def ic_law(a,p,mode):
    check(mode in (0,1),'Wrong law mode');validate_arrays(a,False)
    check(set(a)=={'Coordinates','Velocities','Masses','InternalEnergy','ParticleIDs'},'IC schema')
    r=np.linalg.norm(a['Coordinates'].astype(float)-p['center'],axis=1)
    rho=p['rho_wind']*(1+(p['chi']-1)*.5*(1-np.tanh((r-p['r_cloud'])/(p['density_width']*p['r_cloud']))))
    rv=p['rv_scale']*p['r_cloud'];vw=p['v_wind']
    v=vw*(1-.5*(1-np.tanh((r-rv)/(.1*p['r_cloud'])))) if mode else np.where(r>rv,vw,0)
    check(np.max(abs(a['Velocities'][:,0]-v))/vw<=2e-7 and (a['Velocities'][:,1:]==0).all(),'Wrong L4 velocity')
    pos=a['Coordinates'].astype(float);indices=np.floor(pos/DX).astype(int)
    check(np.max(abs(pos-(indices+.5)*DX))<=1e-6 and len(np.unique(np.ravel_multi_index(indices.T,DIMS)))==N,'Wrong lattice')
    check(np.max(abs(a['Masses'].astype(float)/DX**3-rho)/rho)<=2e-7,'Wrong density construction')
    check(np.max(abs(a['InternalEnergy'].astype(float)*(p['gamma']-1)*rho-p['p_wind']))<=2e-7,'Wrong thermal construction')
    return dict(elements=N,dims=DIMS,max_velocity_error=float(np.max(abs(a['Velocities'][:,0]-v))))


def clock_abi(types):
    check(types['global_data_all_processes'].fields['Ti_Current'][0].itemsize==8,'Wrong native integer clock ABI')


def take(blob,pos,dtype,count):
    dtype=np.dtype(dtype);check(type(count) is int and 0<=count<=N,'Invalid L4 rank count')
    end=pos+count*dtype.itemsize
    check(0<=pos<=end<=len(blob),'Truncated L4 restart prefix')
    return np.frombuffer(blob,dtype=dtype,count=count,offset=pos).copy(),end


def prefix(blob,types):
    h,pos=take(blob,0,types['global_data_all_processes'],1)
    n,pos=take(blob,pos,'<i4',1);check(0<int(n[0])<=N,'Invalid rank particles')
    a,pos=take(blob,pos,types['particle_data'],int(n[0]))
    ng,pos=take(blob,pos,'<i4',1);check(int(ng[0])==len(a),'Not all-gas restart')
    b,pos=take(blob,pos,types['gas_cell_data'],int(ng[0]))
    check(pos<len(blob),'Missing unparsed restart tail')
    return h[0],a,b,pos


def terminal(folder,p,ic):
    request={**prior.onset.ABI,'global_data_all_processes':prior.onset.ABI['global_data_all_processes']+['Ti_Current']}
    types,abi=layouts(parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(BINARY)],text=True)),request)
    clock_abi(types);parts=[];cells=[];headers=[];files=[];explicit=[]
    for rank in range(8):
        path=folder/'output/restartfiles'/f'restart.{rank}';digest=sha(path);blob=path.read_bytes()
        h,a,b,used=prefix(blob,types);parts.append(a);cells.append(b);headers.append(h)
        start=types['global_data_all_processes'].itemsize+4+len(a)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(b)))
        check(sha(path)==digest,'Restart changed while reading')
        files.append(dict(path=str(path),bytes=len(blob),sha256=digest,prefix_bytes=used,particles=len(a)))
    h=headers[0];check(all(all(x[k]==h[k] for k in h.dtype.names) for x in headers),'Rank headers differ')
    a,b=np.concatenate(parts),np.concatenate(cells);order=np.argsort(a['ID']);a,b=a[order],b[order]
    check(np.array_equal(a['ID'],ic['ParticleIDs']) and (a['Type']==0).all(),'Terminal L4 IDs/types')
    check(float(h['Time'])==float(h['TimeMax'])==float(p['TimeMax']) and float(h['TimeBegin'])==0,'Terminal endpoint')
    check(float(h['Timebase_interval'])==prior.clock(p)[1] and int(h['Ti_Current'])==1<<60,'Wrong terminal60-bit clock')
    check(int(h['TotNumPart'])==int(h['TotN_gas'])==N and float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and int(h['ComovingIntegrationOn'])==0,'Wrong terminal recipe')
    check(all(np.isfinite(x[k]).all() for x in (a,b) for k in x.dtype.names),'Nonfinite restart field')
    check(all((b[k]>0).all() for k in ('MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred')),'Nonpositive restart field')
    account=mass_account(ic['Masses'],b['MassTrue'],b['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'] and account['passes'] and account['response_detected'],'Short conserved mass ledger gate')
    return safe(dict(files=files,abi=abi,mass_account=account,clock=int(h['Ti_Current']),
        minima={k:float(min(b[k])) for k in ('Density','Pressure','InternalEnergy','InternalEnergyPred')}))


def audit(folder,p,ic):
    import yt
    import yt.frontends.gadget.io
    from yt.frontends.gizmo.api import GizmoDataset
    yt.set_log_level(40);rows=[];initial=None
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        digest=sha(path);a,t=read(path);m=a['Masses'].astype(float);rho=a['Density'].astype(float)
        direct=[float(m.sum()),float(m[rho>p['chi']*p['rho_wind']/3].sum())]
        ds=GizmoDataset(str(path),bounding_box=np.array([p['domain_left'],p['domain_right']]).T);ad=ds.all_data()
        ym=ad['PartType0','Masses'].to_value('code_mass').astype(float);yr=ad['PartType0','Density'].to_value('code_density').astype(float)
        sums=[float(ym.sum()),float(ym[yr>p['chi']*p['rho_wind']/3].sum())]
        errors=[abs(x-y)/max(abs(x),1e-12) for x,y in zip(direct,sums)]
        check(len(ym)==N and float(ds.current_time.to_value('code_time'))==t and max(errors)<=1e-11 and sha(path)==digest,'Independent L4 reader mismatch')
        if initial is None:
            initial=a
            for k in ('Coordinates','ParticleIDs','Masses','InternalEnergy'):check(np.array_equal(a[k],ic[k]),'Native initial mismatch '+k)
        rows.append(dict(path=str(path),sha256=digest,bytes=path.stat().st_size,time_code=t,t_over_tcc=t/p['t_cc'],elements=N,
            total_mass=direct[0],dense_mass=direct[1],independent_relative_errors=errors,min_energy=float(min(a['InternalEnergy']))))
        del ds,ad;gc.collect()
    check(initial is not None,'No native state')
    values=parameters((folder/'params.txt').read_text())
    cadence=prior.cadence([r['time_code'] for r in rows],values)
    term=terminal(folder,values,ic)
    rho=ic['Masses'].astype(float)/DX**3
    pressure=(p['gamma']-1)*initial['Density'].astype(float)*initial['InternalEnergy']
    return initial,dict(rows=rows,cadence=cadence,terminal=term,
        initial_pressure_min=float(min(pressure)),initial_pressure_max=float(max(pressure)),
        initial_density_vs_lattice_max_relative=float(np.max(abs(initial['Density']/rho-1))))
