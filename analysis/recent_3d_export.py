"""Derived 3D meshes for the 16 recently accepted runs. Never edits raw files."""
from pathlib import Path
import sys,os,json,gzip,struct,time,hashlib,importlib.util
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'deps'))
spec=importlib.util.spec_from_file_location('previous',ROOT.parent/'site_update_20261029_v1/export_recent.py')
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
np=prev.np;h5py=prev.h5py
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
OUT=ROOT.parent/'site_publish_20261029_v1/assets/recent3d';OUT.mkdir(parents=True,exist_ok=True)
DX=prev.DX;CAT=prev.load(prev.OUT/'catalog.json');published={r['id']:r for r in CAT['runs']}
# Reuse the established read-only grid readers, returning the density volume
# before projection. The original script and its completed exports are untouched.
source=(ROOT.parent/'site_update_20261029_v1/export_recent.py').read_text(encoding='utf-8')
start=source.index('def project(');end=source.index('\ndef main()',start)
grid_source=source[start:end].replace('def project(', 'def read_grid(').replace('return rho.sum(axis=0)*DX/chi,rho.sum(axis=2)*DX/chi,mass,md,t,files','return rho,mass,md,t,files')
ns=dict(vars(prev));exec(compile(grid_source,'established_grid_reader','exec'),ns);read_grid=ns['read_grid']

def particle_grid(r,i,row):
    base=r['raw'];j=r['receipt_data']
    if r['id']=='mfv-historical' and i<j['resume_provenance']['snapshot_next']:base=prev.win(j['resume_provenance']['source'])/'output'
    path=base/f'snapshot_{i:03d}.hdf5';massgrid=np.zeros((128,128,256),dtype='float64');md=mass=0.
    with h5py.File(path,'r') as f:
        g=f['PartType0'];t=float(f['Header'].attrs['Time']);count=len(g['Masses'])
        for a in range(0,count,65536):
            sl=slice(a,min(count,a+65536));m=g['Masses'][sl].astype('float64');pos=g['Coordinates'][sl];rho=g['Density'][sl]
            xyz=np.floor(pos/DX).astype(int);xyz%=np.array([256,128,128])
            np.add.at(massgrid,(xyz[:,2],xyz[:,1],xyz[:,0]),m)
            mass+=float(m.sum());md+=float(m[rho>r['chi']/3].sum())
    assert abs(massgrid.sum()-mass)/mass<1e-9
    return massgrid/DX**3,mass,md,t,[path]

def encode(rho,chi,periodic):
    # Full native grid -> modest display-only Gaussian -> regular two-cell mesh
    # sampling. No random triangle thinning or altered scientific reductions.
    field=gaussian_filter((rho/chi).astype('float32'),sigma=.8,mode='wrap' if periodic else 'nearest')
    shells=[];tris=0
    for level,color,opacity in [(.15,(.28,.48,.91),.38),(.6,(1.,.53,.23),.97)]:
        if not float(field.min())<level<float(field.max()):continue
        v,f,_,_=marching_cubes(field,level,spacing=(DX,DX,DX),step_size=2,allow_degenerate=False)
        v=v[:,[2,1,0]]+np.array([-3+DX/2,-5+DX/2,-5+DX/2]);f=f[:,[0,2,1]]
        lo=v.min(axis=0);hi=v.max(axis=0);q=np.rint((v-lo)/np.maximum(hi-lo,1e-20)*65535).astype('<u2')
        assert np.isfinite(v).all() and np.all(v>=[-3,-5,-5]) and np.all(v<=[17,5,5])
        header=struct.pack('<ff3f3f3fII',level,opacity,*color,*lo,*hi,len(v),len(f))
        shells.append(header+q.tobytes()+f.astype('<u4').tobytes());tris+=len(f)
    return gzip.compress(struct.pack('<B',len(shells))+b''.join(shells),compresslevel=6,mtime=0),tris,len(shells)

def main():
    manifest={};audit=[]
    for r in prev.runs:
        tag='new_'+r['id'];out=OUT/tag;out.mkdir(exist_ok=True);indexfile=out/'index.json'
        if indexfile.exists():
            index=prev.load(indexfile);manifest[tag]=index['display'];print('reuse',tag,flush=True);continue
        rows=r['rows'];tcc=float(rows[-1].get('nominal_time_code',rows[-1]['time_code']))/5
        index=dict(schema_version=2,frames=[],times=[],tris=[],shell_counts=[],display=dict(label=r['label'],code=r['label'].split(' χ')[0],chi=r['chi'],lvl=5,frames=21,note=r['note'],projection_id=r['id']),visualization=dict(field='total gas density / initial cloud density',grid=[256,128,128],gaussian_sigma_native_cells=.8,mesh_step_native_cells=2,position_bits=16,particle_deposition='cell mass / cell volume' if r['fmt']=='gizmo' else None,temporal_interpolation=False,source_receipt_sha256=published[r['id']]['receipt_sha256']),diagnostics=dict(schema_version=2,series=[dict(t_over_tcc=t,dense_mass_over_initial_dense_mass=d) for t,d in zip(published[r['id']]['times'],published[r['id']]['dense'])]))
        checks=[]
        for k,nominal in enumerate(np.linspace(0,5,21)):
            i=min(range(len(rows)),key=lambda n:abs(float(rows[n]['time_code'])/tcc-nominal));row=rows[i]
            rho,m,md,t,files=(particle_grid if r['fmt']=='gizmo' else read_grid)(r,i,row)
            ref=float(row.get('total_mass',row.get('mass')));dref=float(row['dense_mass']);err=max(abs(m-ref)/max(ref,1),abs(md-dref)/max(dref,1))
            assert err<2e-7 and abs(t-row['time_code'])<1e-8*max(t,1),(r['id'],i,err)
            blob,n,s=encode(rho,r['chi'],r['fmt']=='gizmo');del rho
            name=f'f{k:03d}.bin';(out/name).write_bytes(blob);index['frames'].append(name);index['times'].append(t/tcc);index['tris'].append(n);index['shell_counts'].append(s)
            checks.append(dict(snapshot_index=i,time=t/tcc,relative_error=err,sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob)))
        indexfile.write_text(json.dumps(index,separators=(',',':')),encoding='utf-8');manifest[tag]=index['display'];audit.append(dict(id=r['id'],frames=checks))
        (ROOT/'volume_export_audit.json').write_text(json.dumps(audit,indent=2))
        used=sum(f.stat().st_size for f in OUT.glob('*/*'));assert used<100*1024**2
        print('exported',r['id'],'21 frames; total',round(used/1024**2,1),'MiB',flush=True)
    (OUT/'catalog.js').write_text('var RECENT_3D='+json.dumps(manifest,separators=(',',':'))+';\n',encoding='utf-8')
    print('complete',len(manifest),'runs',flush=True)
if __name__=='__main__':main()
