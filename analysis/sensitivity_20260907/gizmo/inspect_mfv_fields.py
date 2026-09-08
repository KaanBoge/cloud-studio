"""Read-only audit of every native MFV field after a failed positivity check."""
import json
from pathlib import Path
import h5py,numpy as np
from smoke_gizmo import ROOT,save,sha
from verify_gizmo import snapshots

def main():
    folder=ROOT/'runs'/'L3_mfv_sharp13';dest=ROOT/'mfv_field_audit.json'
    if dest.exists():raise ValueError('Existing field audit; do not overwrite')
    frames=[];bad=[]
    for path in snapshots(folder/'output'):
        digest=sha(path)
        with h5py.File(path) as h:
            g=h['PartType0'];time=float(h['Header'].attrs['Time']);row=dict(file=str(path),time=time,sha256=digest,fields={})
            for field in ('Masses','Density','InternalEnergy','SmoothingLength'):
                x=g[field][:];indices=np.flatnonzero((x<=0)|~np.isfinite(x))
                row['fields'][field]=dict(min=float(np.min(x)),max=float(np.max(x)),nonpositive=int(np.sum(x<=0)),nonfinite=int(np.sum(~np.isfinite(x))))
                if len(indices):
                    ii=indices[:8];bad.append(dict(file=str(path),time=time,field=field,count=len(indices),ids=g['ParticleIDs'][ii].tolist(),
                        values=x[ii].tolist(),masses=g['Masses'][ii].tolist(),density=g['Density'][ii].tolist(),
                        internal_energy=g['InternalEnergy'][ii].tolist(),positions=g['Coordinates'][ii].tolist()))
        if sha(path)!=digest:raise ValueError('Native file changed during read')
        frames.append(row)
    report=dict(status='audited_no_native_changes',snapshots=len(frames),bad_fields=bad,frames=frames,script_sha256=sha(__file__))
    save(dest,report);print(json.dumps(dict(snapshots=len(frames),bad_entries=len(bad),first_bad=bad[:3],last_bad=bad[-1:]),indent=2))

if __name__=='__main__':main()
