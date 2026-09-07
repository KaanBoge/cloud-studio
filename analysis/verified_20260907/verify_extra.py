import json
from pathlib import Path
import numpy as np
import h5py
from check_snapshot import check
root=Path('/home/kaan/ic_audit_20260907')
results=[]
for chi in (10,100,1000):
    run=root/'grid_tests'/f'athw_chi{chi}'
    result=check(str(run/'id0/Cloud.0000.vtk'),str(run/'athinput'),'athw',[0,0,0],(64,32,32))
    result.update(kind='athw',chi=chi,correction='Native VTK output lives in id0, not the run root')
    (run/'verification_reader_corrected.json').write_text(json.dumps(result,indent=2))
    results.append(result)
    print('athw',chi,result['passed'],result['errors'])
for chi in (10,100,1000):
    run=root/'enzoe_tests_v2'/f'chi{chi}'
    errors=[]; count=0
    with h5py.File(run/'ic-000-p00.h5') as f:
        assert f.attrs['rank'][0]==3 and f.attrs['time'][0]==0
        assert np.allclose(f.attrs['lower'],[-3,-5,-5]) and np.allclose(f.attrs['upper'],[17,5,5])
        for name in f:
            group=f[name]
            start=group.attrs['enzo_GridStartIndex']; end=group.attrs['enzo_GridEndIndex']+1
            widths=group.attrs['enzo_CellWidth']; left=group.attrs['lower']
            x,y,z=[left[i]+(np.arange(end[i]-start[i])+.5)*widths[i] for i in range(3)]
            Z,Y,X=np.meshgrid(z,y,x,indexing='ij')
            radius=np.sqrt(X*X+Y*Y+Z*Z)
            region=tuple(slice(int(start[i]),int(end[i])) for i in (2,1,0))
            rho=group['field_density'][region]
            v=[group['field_velocity_'+a][region] for a in 'xyz']
            energy=group['field_total_energy'][region]
            ref=1+(chi-1)*.5*(1-np.tanh((radius-1)/.1))
            vw=2*np.sqrt(5/3)
            refv=np.where(radius>1.3,vw,0)
            recovered_pressure=(5/3-1)*rho*(energy-.5*sum(a*a for a in v))
            errors.append([np.max(abs(rho-ref)/ref),np.max(abs(v[0]-refv))/vw,
                           max(np.max(abs(v[1])),np.max(abs(v[2])))/vw,np.max(abs(recovered_pressure-1))])
            count+=rho.size
    error=np.array(errors).max(axis=0)
    result={'code':'enzoe','chi':chi,'passed':bool(np.max(error)<3e-5 and count==65536),'cells':count,
            'errors':dict(zip(['density_relative','velocity_over_vwind','transverse_velocity','pressure_from_total_energy'],error.tolist())),
            'scope':'native t=0 3D fields; pressure recovered from conserved energy'}
    results.append(result)
    print('enzoe',chi,result['passed'],result['errors'])
    (run/'verification.json').write_text(json.dumps(result,indent=2))
assert all(x['passed'] for x in results)
