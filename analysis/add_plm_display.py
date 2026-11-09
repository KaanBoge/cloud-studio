"""Export only the missing accepted HLLC/PLM display products; never run a solver.

Reuses the established density reader and display mesh encoding. Existing exports
are preserved; the small receipt comparison below applies only to new samples.
"""
import ast, hashlib, json, os, sys, struct, gzip
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=['D:/CloudStudio-tools','D:/CloudCrushing/meeting_20261010_v1/paper_meeting_20261026_v1/deps']
import numpy as np
import h5py
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
DX=10/128
def win(p): return Path(str(p).replace('/mnt/d/','D:/'))
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
source=(ROOT/'analysis/recent_gallery_export.py').read_text(encoding='utf-8')
tree=ast.parse(source)
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='project':
        code=ast.get_source_segment(source,node).replace('def project(', 'def read_grid(').replace('return rho.sum(axis=0)*DX/chi,rho.sum(axis=2)*DX/chi,mass,md,t,files','return rho,mass,md,t,files')
        exec(code)
source=(ROOT/'analysis/recent_3d_export.py').read_text(encoding='utf-8')
for node in ast.parse(source).body:
    if isinstance(node,ast.FunctionDef) and node.name=='encode': exec(ast.get_source_segment(source,node))
from PIL import Image
base=Path('D:/CloudCrushing/meeting_20261010_v1')
integration=load(base/'chi10_followon_20261028_v1/plm_v13_validated_result_integration.json')
assert integration['status']=='ACCEPTED_BOUNDED_MATCHED_L5'
receipt=Path(integration['validation_control'])/'validation_result.json'
j=load(receipt)
assert hashlib.sha256(receipt.read_bytes()).hexdigest()==integration['validation_result_sha256']
rows=next(j[k] for k in ('series','outputs','snapshots') if isinstance(j.get(k),list))
rid='apk-hllc-plm-off'; tag='new_'+rid
catalog=load(ROOT/'assets/recent/catalog.json')
if any(r['id']==rid for r in catalog['runs']):
    raise SystemExit('Existing PLM export retained; no repeat work.')
note='Nonradiative HLLC/PLM reconstruction control; 36 first-order fallback stages may add diffusion. Accepted bounded numerical screen, not convergence or an accuracy ranking.'
r=dict(id=rid,label='AthenaPK χ100 · cooling off · HLLC/PLM',chi=100,fmt='apk',raw=Path(integration['raw']),receipt_data=j,note=note)
tcc=float(rows[-1]['time_code'])/5
lut=np.array(catalog['colormap'])
def color(a):
    idx=np.floor(np.clip((np.log10(np.maximum(a,1e-30))-np.log10(.008))/np.log10(5/.008),0,1)*255).astype(int)
    return np.round(lut[idx]*255).astype('uint8')[::-1]
out=ROOT/'assets/recent3d'/tag;out.mkdir(parents=True,exist_ok=True)
index=dict(schema_version=2,frames=[],times=[],tris=[],shell_counts=[],display=dict(label=r['label'],code='AthenaPK',chi=100,lvl=5,frames=21,note=note,projection_id=rid),visualization=dict(field='total gas density / initial cloud density',grid=[256,128,128],gaussian_sigma_native_cells=.8,mesh_step_native_cells=2,position_bits=16,temporal_interpolation=False,source_receipt_sha256=integration['validation_result_sha256']),diagnostics=dict(schema_version=2,series=[dict(t_over_tcc=x['time_code']/tcc,dense_mass_over_initial_dense_mass=x['dense_mass']/rows[0]['dense_mass']) for x in rows]))
edge=[];face=[];frames=[];audit=[]
for k,nominal in enumerate(np.linspace(0,5,21)):
    i=min(range(len(rows)),key=lambda n:abs(rows[n]['time_code']/tcc-nominal));row=rows[i]
    rho,m,md,t,files=read_grid(r,i,row)
    mass=row.get('total_mass',row.get('mass'));err=max(abs(m-mass)/max(mass,1),abs(md-row['dense_mass'])/max(row['dense_mass'],1))
    assert err<2e-7 and abs(t-row['time_code'])<1e-8*max(t,1)
    if k%2==0:
        edge.append(color(rho.sum(axis=0)*DX/100));face.append(color(rho.sum(axis=2)*DX/100));frames.append(dict(time=t/tcc,nominal=float(nominal)))
    blob,n,s=encode(rho,100,False);name=f'f{k:03d}.bin';(out/name).write_bytes(blob)
    index['frames'].append(name);index['times'].append(t/tcc);index['tris'].append(n);index['shell_counts'].append(s)
    audit.append(dict(snapshot_index=i,time=t/tcc,relative_error=err,bytes=len(blob)))
    del rho
(out/'index.json').write_text(json.dumps(index,separators=(',',':')),encoding='utf-8')
for view,imgs in [('edge',edge),('face',face)]: Image.fromarray(np.concatenate(imgs)).save(ROOT/f'assets/recent/{rid}-{view}.png')
data=dict(id=rid,label=r['label'],chi=100,mach=2,n=128,cells=4194304,frames=frames,views=['edge','face'],note=note,status='Accepted bounded result',receipt_sha256=integration['validation_result_sha256'],receipt_name=receipt.name,receipt_status=j.get('status'),cooling='none',times=[x['time_code']/tcc for x in rows],dense=[x['dense_mass']/rows[0]['dense_mass'] for x in rows],extent=[-3,17,-5,5],image_shape=[128,256],color_range=[.008,5])
(ROOT/f'assets/recent/{rid}.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
catalog['runs'].append(data);(ROOT/'assets/recent/catalog.json').write_text(json.dumps(catalog,separators=(',',':')),encoding='utf-8')
p=ROOT/'assets/recent3d/catalog.js';manifest=json.loads(p.read_text().split('=',1)[1].rstrip(';\n'));manifest[tag]=index['display'];p.write_text('var RECENT_3D='+json.dumps(manifest,separators=(',',':'))+';\n',encoding='utf-8')
(ROOT/'analysis/plm_display_audit.json').write_text(json.dumps(dict(receipt_sha256=integration['validation_result_sha256'],samples=audit,original_data_modified=False),indent=2))
print('Added HLLC/PLM: 22 projection frames, 21 meshes; saved scalar agreement passed.')
