"""Read-only density projections for the public capture gallery. No solver runs.

Uses accepted receipt times, samples every 0.5 t_cc, checks projected mass and
dense mass against those receipts, and writes only small new assets here.
"""
from pathlib import Path
import sys, os, json, hashlib, struct, zlib, ast, time
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
ROOT=Path(__file__).resolve().parent
B=Path('D:/CloudCrushing/meeting_20261010_v1')
N=Path('D:/CloudCrushing/native_runs')
sys.path.insert(0,str(B/'paper_meeting_20261026_v1/deps'))
import numpy as np
import h5py
OUT=ROOT/'assets/recent';OUT.mkdir(parents=True,exist_ok=True)
DX=10/128
cm=ast.parse((B/'paper_meeting_20261014_v1/plot_dependencies_v1/site-packages/matplotlib/_cm_listed.py').read_text())
LUT=np.array(next(ast.literal_eval(n.value) for n in cm.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_magma_data' for t in n.targets)))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def win(p):return Path(str(p).replace('/mnt/d/','D:/'))
def png(path, rgb):
    h,w,_=rgb.shape
    def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    raw=b''.join(b'\0'+r.tobytes() for r in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def color(a):
    idx=np.floor(np.clip((np.log10(np.maximum(a,1e-30))-np.log10(.008))/(np.log10(5)-np.log10(.008)),0,1)*255).astype(int)
    return np.round(LUT[idx]*255).astype('uint8')[::-1]
runs=[]
def add(id,label,chi,fmt,receipt,raw,**extra):
    receipt=Path(receipt);j=load(receipt)
    rows=next(j[k] for k in ('series','outputs','snapshots') if isinstance(j.get(k),list))
    assert len(rows)>=101,(id,len(rows))
    runs.append(dict(id=id,label=label,chi=chi,fmt=fmt,receipt=receipt,raw=Path(raw),rows=rows,receipt_data=j,**extra))
for chi in (1000,10):
    root=N/f'enzo_L5_chi{chi}_20261010_v1/full_sharp13_v1'
    receipt=B/'enzo_L5_chi1000_analysis_v2/actual.json' if chi==1000 else root/'native_completion.json'
    add(f'enzo-{chi}',f'Enzo χ{chi}',chi,'enzo',receipt,root,note='Accepted saved-result screen; original controller failure retained.' if chi==1000 else 'Accepted bounded native result.')
for chi in (10,1000):
    root=N/f'enzoe_L5_chi{chi}_20261010_v1/full_sharp13'
    receipt=root/'evolution_series.json' if chi==1000 else root.parent/'full_validation_v1/evolution_series.json'
    add(f'enzoe-{chi}',f'Enzo-E χ{chi}',chi,'enzoe',receipt,root,note='Accepted bounded native result. No passive material tag in this run.')
for chi,root in [(10,N/'athpp_L5_chi10_20261010_v1/full_sharp13_v11'),(1000,N/'athpp_L5_chi1000_20261028_v1/full_sharp13_v23')]:
    add(f'athpp-{chi}',f'Athena++ χ{chi}',chi,'athpp',root/'native_completion.json',root,note='Accepted bounded native result; convergence has not been established.')
gizmo=[('mfm-sharp','GIZMO MFM · sharp','D:/CloudCrushing/local_queue_20261023_v4/validate_sharp0/validation.json',N/'sensitivity_20260907/gizmo_mfm_L5_20260924_v1/gizmo_mfm_L5_full_0_repair20261023_v3/output'),
('mfm-historical','GIZMO MFM · historical','D:/CloudCrushing/local_queue_20261023_v3/validate_full1/validation.json',N/'sensitivity_20260907/gizmo_mfm_L5_20260924_v1/gizmo_mfm_L5_full_1_repair20261022_v4/output'),
('mfv-sharp','GIZMO MFV · sharp','D:/CloudCrushing/mfv_L5_queue_20261023_v1/pipeline_v2/validate_full/validation.json',N/'sensitivity_20260907/gizmo_mfv_L5_20261023_v1/sharp0_full/output'),
('mfv-historical','GIZMO MFV · historical','D:/CloudCrushing/mfv_L5_queue_20261023_v1/historical_v3/validate_full/validation.json',N/'sensitivity_20260907/gizmo_mfv_L5_20261023_v1/historical3_resume/output')]
for id,label,r,root in gizmo:add(id,label,100,'gizmo',r,root,note='Periodic boundaries; particle masses and initial construction differ from grid runs. Historical velocity control retained separately.')
apk=[('apk-hlle-off','AthenaPK χ100 · cooling off · HLLE/PLM',B/'cooling_repair_source_v1/tracer_global_pair_20261026_v1/off',N/'tracer_pair_20261026_v1/global_v1/off'),
('apk-hlle-on','AthenaPK χ100 · cooling on · HLLE/PLM',B/'cooling_repair_source_v1/tracer_global_pair_20261026_v1/on',N/'tracer_pair_20261026_v1/global_v1/on'),
('apk-hlle-10','AthenaPK χ10 · HLLE/PLM',B/'apk_L5_chi10_queue_20261026_v2/chi10',None),
('apk-hllc-off','AthenaPK χ100 · cooling off · HLLC/PPM',B/'apk_hllc_handoff_20261027_v1/off',None),
('apk-hllc-on','AthenaPK χ100 · cooling on · HLLC/PPM',B/'tracer_proactive_repair_20261027_v5/on',None),
('apk-hllc-10','AthenaPK χ10 · HLLC/PPM',B/'chi10_followon_20261028_v1/validate_chi10',N/'tracer_endpoint_20261027_v1/chi10/run/chi10')]
for id,label,c,raw in apk:
    j=load(c/'validation_result.json')
    if raw is None:raw=win(load(c/'config.json')['target_windows'])
    note=f"Modified tracer/flux correction; {j['global_first_order_fallback_stages']} global first-order fallback stages. "
    note+='Cooling layer under-resolved. ' if j.get('cooling')=='tabular' else ''
    note+='HLLC/PPM cooling-on and off have different correction-source histories.' if 'hllc' in id else 'HLLE/PLM controls retained separately.'
    add(id,label,j.get('chi',100),'apk',c/'validation_result.json',raw,note=note,cooling=j.get('cooling','none'))

def project(run,i,row):
    fmt=run['fmt'];root=run['raw'];j=run['receipt_data'];chi=run['chi'];files=[]
    if fmt=='gizmo':
        if run['id']=='mfv-historical' and i<j['resume_provenance']['snapshot_next']:root=win(j['resume_provenance']['source'])/'output'
        p=root/f'snapshot_{i:03d}.hdf5';files=[p]
        edge=np.zeros((128,256));face=np.zeros((128,128));md=mass=0.
        with h5py.File(p,'r') as h:
            g=h['PartType0'];t=float(h['Header'].attrs['Time']);n=len(g['Masses'])
            for a in range(0,n,65536):
                sl=slice(a,min(a+65536,n));m=g['Masses'][sl].astype(float);rho=g['Density'][sl];pos=g['Coordinates'][sl]
                mass+=m.sum();md+=m[rho>chi/3].sum()
                edge+=np.histogram2d(pos[:,1],pos[:,0],bins=(np.arange(129)*DX,np.arange(257)*DX),weights=m)[0]
                face+=np.histogram2d(pos[:,2],pos[:,1],bins=(np.arange(129)*DX,np.arange(129)*DX),weights=m)[0]
        return edge/DX**2/chi,face/DX**2/chi,float(mass),float(md),t,files
    rho=np.zeros((128,128,256),dtype='float64')
    if fmt=='enzo':
        p=root/(row['base']+'.cpu0000');files=[p]
        with h5py.File(p,'r') as h:
            keys=[];h.visititems(lambda n,o:keys.append(n) if isinstance(o,h5py.Dataset) and n.split('/')[-1]=='Density' else None)
            assert len(keys)==1;rho=h[keys[0]][:];assert rho.shape==(128,128,256)
        t=row['time_code']
    elif fmt=='enzoe':
        covered=np.zeros((128,128,256),dtype='uint8')
        for n in range(8):
            p=root/f'ic-{i:03d}-p{n:02d}.h5';files.append(p)
            with h5py.File(p,'r') as h:
                t=float(h.attrs['time'][0])
                for g in h.values():
                    lo=np.rint((g.attrs['lower']-[-3,-5,-5])/DX).astype(int);a=g.attrs['enzo_GridStartIndex'];b=g.attrs['enzo_GridEndIndex']+1
                    r=g['field_density'][a[2]:b[2],a[1]:b[1],a[0]:b[0]]
                    s=tuple(slice(lo[k],lo[k]+r.shape[2-k]) for k in [2,1,0]);rho[s]=r;covered[s]+=1
        assert np.all(covered==1);del covered
    elif fmt=='athpp':
        p=root/row['snapshot'];files=[p]
        with h5py.File(p,'r') as h:
            assert list(h.attrs['RootGridSize'])==[256,128,128];t=float(h.attrs['Time']);ds=h['prim'];nz,ny,nx=ds.shape[2:]
            assert h.attrs['VariableNames'][0]==b'rho'
            for n,(x,y,z) in enumerate(h['LogicalLocations'][:]):rho[z*nz:(z+1)*nz,y*ny:(y+1)*ny,x*nx:(x+1)*nx]=ds[0,n]
    else:
        if row.get('segment'):root=win(j['retained_prefix_root'] if row['segment']=='prefix' else j['resume_root'])
        p=root/row['file'];files=[p]
        with h5py.File(p,'r') as h:
            assert list(h['Info'].attrs['RootGridSize'])==[128,256,128];t=float(h['Info'].attrs['Time'])
            for n,(x,y,z) in enumerate(h['LogicalLocations'][:]):
                # Native wind is along x2; canonical wind-horizontal projection.
                rho[z*32:(z+1)*32,x*32:(x+1)*32,y*32:(y+1)*32]=h['prim'][n,0].transpose(0,2,1)
    assert np.isfinite(rho).all() and rho.min()>0
    mass=float(rho.sum(dtype='float64')*DX**3);md=float(rho[rho>chi/3].sum(dtype='float64')*DX**3)
    return rho.sum(axis=0)*DX/chi,rho.sum(axis=2)*DX/chi,mass,md,t,files

def main():
    public=[];audit=[];start=time.monotonic()
    for r in runs:
        done=OUT/(r['id']+'.json')
        if done.exists():
            public.append(load(done));print('reuse',r['id'],flush=True);continue
        rows=r['rows'];end=float(rows[-1]['time_code']);tcc=float(rows[-1].get('nominal_time_code',end))/5;frames=[];edge=[];face=[];checks=[]
        for nominal in np.arange(0,5.01,.5):
            i=min(range(len(rows)),key=lambda k:abs(float(rows[k]['time_code'])/tcc-nominal));row=rows[i]
            e,f,m,md,t,files=project(r,i,row)
            ref=float(row.get('total_mass',row.get('mass')));dense=float(row['dense_mass']);err=max(abs(m-ref)/max(ref,1),abs(md-dense)/max(dense,1))
            assert err<2e-7,(r['id'],i,'mass mismatch',m,ref,md,dense)
            assert abs(t-row['time_code'])<1e-8*max(1,t),(r['id'],i,'time mismatch')
            assert abs(e.sum()*DX**2*r['chi']-m)/m<1e-10 and abs(f.sum()*DX**2*r['chi']-m)/m<1e-10
            edge.append(color(e));face.append(color(f));frames.append(dict(time=t/tcc,nominal=float(nominal)))
            checks.append(dict(index=i,mass_relative_error=err,files=[str(p) for p in files]))
        png(OUT/(r['id']+'-edge.png'),np.concatenate(edge,axis=0));png(OUT/(r['id']+'-face.png'),np.concatenate(face,axis=0))
        data=dict(id=r['id'],label=r['label'],chi=r['chi'],mach=2,n=128,cells=4194304,frames=frames,views=['edge','face'],note=r['note'],status='Accepted bounded result',receipt_sha256=hashlib.sha256(r['receipt'].read_bytes()).hexdigest(),receipt_name=r['receipt'].name,receipt_status=r['receipt_data'].get('status','accepted result screen'),cooling=r.get('cooling','none'),times=[float(x['time_code'])/tcc for x in rows],dense=[float(x['dense_mass'])/float(rows[0]['dense_mass']) for x in rows],extent=[-3,17,-5,5],image_shape=[128,256],color_range=[.008,5])
        done.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');public.append(data)
        audit.append(dict(id=r['id'],receipt=str(r['receipt']),checks=checks))
        (ROOT/'export_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
        print('exported',r['id'],'11 frames x 2 views',flush=True)
        assert time.monotonic()-start<3600
    (OUT/'catalog.json').write_text(json.dumps(dict(schema='cloud-studio-projections/1',runs=public,colormap=LUT.tolist(),projection='Total gas column density / (initial cloud density × initial radius)',sample_cadence_tcc=.5,limitations='Accepted numerical screens are not convergence or accuracy rankings. Projections are derived visualizations; original outputs remain on D.'),separators=(',',':')),encoding='utf-8')
    print('complete',len(public),'runs',sum(p.stat().st_size for p in OUT.iterdir()),'bytes',flush=True)
if __name__=='__main__':main()
