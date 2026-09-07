"""Export every schema-2 native uniform-grid snapshot without guessed times.

This is a lossy visualization, never a substitute for native fluid fields.
Output directory must be new. No cleanup, upload, filtering by t<=5, repetition,
random face thinning or temporal interpolation is performed.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from skimage.measure import marching_cubes
from run_params import parse_file
from figure1_v2 import native_density


def mesh_bytes(field,lo,spacing):
    shells=[];triangles=0
    for level,color,opacity in ((.15,(0,.447,.698),.42),(.6,(.835,.369,0),.96)):
        if not field.min()<level<field.max(): continue
        vertices,faces,_,_=marching_cubes(field,level=level,spacing=spacing)
        vertices+=lo
        qlo=vertices.min(axis=0);qhi=vertices.max(axis=0)
        q=np.rint(65535*(vertices-qlo)/np.where(qhi>qlo,qhi-qlo,1)).astype('<u2')
        header=struct.pack('<ff3f3f3fII',level,opacity,*color,*qlo,*qhi,len(vertices),len(faces))
        shells.append(header+q.tobytes()+faces.astype('<u4').tobytes())
        triangles+=len(faces)
    return gzip.compress(struct.pack('<B',len(shells))+b''.join(shells)),triangles


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--diagnostics',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--center',required=True,nargs=3,type=float)
    a=ap.parse_args();d=json.loads(Path(a.diagnostics).read_text())
    if d.get('schema_version')!=2:raise ValueError('Recompute schema-2 native diagnostics first')
    p=parse_file(d['parameters']['source'])
    if not p or p['parameter_sha256']!=d['parameters']['parameter_sha256']:
        raise ValueError('Parameter file mismatch')
    rows=d['series'];times=np.array([r['t_over_tcc'] for r in rows])
    if not len(times) or not np.all(np.isfinite(times)) or np.any(np.diff(times)<=0):
        raise ValueError('Invalid or duplicate measured native times')
    out=Path(a.out);out.mkdir(exist_ok=False)
    index={'schema_version':2,'times':times.tolist(),'frames':[],'tris':[],
           'parameters':p,'center_code':a.center,'comparison_group':d['comparison_group'],
           'diagnostic_sha256':hashlib.sha256(Path(a.diagnostics).read_bytes()).hexdigest(),
           'warning':'Lossy quantized isosurfaces; retain native snapshots for analysis.'}
    for i,row in enumerate(rows):
        panel={'kind':d['kind'],'parameters':p,'row':row,'center_code':a.center}
        field,lo,spacing=native_density(panel)
        blob,n=mesh_bytes(field,lo,spacing);name=f'f{i:04d}.bin'
        (out/name).write_bytes(blob)
        index['frames'].append(name);index['tris'].append(n)
    # No index is advertised until all measured snapshots have exported successfully.
    (out/'index.json').write_text(json.dumps(index,indent=2,allow_nan=False))
    print(f'Exported {len(rows)} distinct native times; none omitted or repeated.')


if __name__=='__main__':main()
