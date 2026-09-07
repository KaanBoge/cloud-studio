"""Read native 3D RAMSES leaf cells for the audited six-face boundary layout.

The standard yt frontend assumes a unit cube and drops the second interior
coarse cell of this rectangular patch. Return native coordinates and fields.
This reader explicitly rejects other boundary layouts rather than guessing.
"""
import struct
from pathlib import Path
import numpy as np


class Records:
    def __init__(self,path):
        self.f=open(path,'rb')
    def rec(self):
        header=self.f.read(4)
        if len(header)!=4:
            raise EOFError('Missing Fortran record')
        n=struct.unpack('<i',header)[0]
        if n<0:
            raise ValueError('Unsupported split Fortran record')
        payload=self.f.read(n); trailer=self.f.read(4)
        if len(payload)!=n or trailer!=header:
            raise ValueError('Corrupt Fortran record')
        return payload
    def ints(self): return np.frombuffer(self.rec(),dtype='<i4')
    def doubles(self): return np.frombuffer(self.rec(),dtype='<f8')
    def skip(self,n=1):
        for _ in range(n): self.rec()
    def close(self): self.f.close()


def read_output(directory):
    chunks=[]; metadata=None
    files=sorted(Path(directory).glob('amr_*.out*'))
    if not files: raise ValueError('No native AMR files')
    for path in files:
        cpu=int(path.name.split('.out')[-1])
        a=Records(path); h=Records(path.with_name(path.name.replace('amr_','hydro_',1)))
        try:
            ncpu=int(a.ints()[0]); ndim=int(a.ints()[0]); coarse=a.ints()
            nlevel=int(a.ints()[0]); a.skip(); nb=int(a.ints()[0]); a.skip()
            boxlen=float(a.doubles()[0]); a.skip(3); time=float(a.doubles()[0])
            a.skip(7)
            a.skip(2)
            counts=a.ints().reshape(nlevel,ncpu).T
            a.skip()
            if nb:
                a.skip(2); boundaries=a.ints().reshape(nlevel,nb).T
            else: boundaries=np.zeros((0,nlevel),dtype=int)
            a.skip(); ordering=a.rec().decode().strip()
            a.skip(5 if ordering=='bisection' else 1)
            a.skip(3)
            hn=int(h.ints()[0]); nvar=int(h.ints()[0]); hd=int(h.ints()[0])
            hl=int(h.ints()[0]); hb=int(h.ints()[0]); gamma=float(h.doubles()[0])
            if (ndim,nb)!=(3,6) or tuple(coarse)!=(4,3,3):
                raise ValueError(f'Unsupported layout: ndim={ndim}, boundary={nb}, coarse={coarse}')
            if (hn,hd,hl,hb)!=(ncpu,ndim,nlevel,nb) or len(files)!=ncpu:
                raise ValueError('Inconsistent or missing output shards')
            scale=boxlen/(int(coarse[0])-2)
            current={'time':time,'boxlen':boxlen,'domain_width':[boxlen,scale,scale],
                     'gamma':gamma,'nvar':nvar,'ncpu':ncpu}
            if metadata and current!=metadata: raise ValueError('Shard metadata mismatch')
            metadata=current
            for level in range(1,nlevel+1):
                dx=.5**level
                for owner in range(1,ncpu+nb+1):
                    n=int(counts[owner-1,level-1] if owner<=ncpu else boundaries[owner-ncpu-1,level-1])
                    if int(h.ints()[0])!=level or int(h.ints()[0])!=n:
                        raise ValueError('Hydro and AMR block ordering mismatch')
                    if not n: continue
                    a.skip(3)
                    positions=np.stack([a.doubles() for _ in range(ndim)],axis=1)
                    a.skip(1+2*ndim)
                    sons=np.stack([a.ints() for _ in range(8)],axis=1)
                    a.skip(16)
                    fields=np.empty((n,8,nvar))
                    for child in range(8):
                        for var in range(nvar): fields[:,child,var]=h.doubles()
                    if owner!=cpu: continue
                    for child in range(8):
                        leaf=sons[:,child]==0
                        offsets=np.array([(child>>i & 1)-.5 for i in range(3)])
                        xyz=(positions[leaf]+dx*offsets-1)*scale
                        chunks.append(np.column_stack((xyz,np.full(leaf.sum(),dx*scale),fields[leaf,child])))
        finally:
            a.close();h.close()
    return metadata,np.vstack(chunks)


if __name__=='__main__':
    import json
    from run_params import parse_file
    root=Path('/home/kaan/ic_audit_20260907/ramses_rect_tests')
    for chi in (10,100,1000):
        run=root/f'chi{chi}'
        meta,c=read_output(run/'output_00001')
        p=parse_file(run/'run.nml')
        r=np.linalg.norm(c[:,:3]-[3,5,5],axis=1)
        ref=1+(chi-1)*.5*(1-np.tanh((r-1)/.1))
        v=np.where(r>1.3,p['v_wind'],0)
        errors={'density':float(np.max(abs(c[:,4]-ref)/ref)),
                'velocity':float(np.max(abs(c[:,5]-v))/p['v_wind']),
                'transverse_velocity':float(np.max(abs(c[:,6:8]))/p['v_wind']),
                'pressure':float(np.max(abs(c[:,8]-1)))}
        bounds=[(c[:,:3]-c[:,3,None]/2).min(axis=0).tolist(),(c[:,:3]+c[:,3,None]/2).max(axis=0).tolist()]
        passed=meta['time']==0 and len(c)==65536 and max(errors.values())<3e-5 and np.allclose(bounds,[[0,0,0],[20,10,10]])
        result={'code':'ramses','chi':chi,'passed':bool(passed),'cells':len(c),'errors':errors,'bounds':bounds,'metadata':meta,
                'reader':'native rectangular six-face layout; all CPU shards included'}
        (run/'verification.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
        if not passed: raise SystemExit(1)
