"""Read-only native MFV failure audit; no filtering, floor changes or relaunches.

The output is diagnostic evidence, not a certification of valid MFV evolution.
Reads all stored fields and original header times, and preserves input hashes.
"""
import fcntl,json,sys
from pathlib import Path
import h5py,numpy as np
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1')
from run_full_l3 import ROOT,sha,save,check_times,restart_files
from verify_gizmo import snapshots,pair,BASE

def resource_summary(folder):
    rows=[json.loads(line) for line in (folder/'resources.jsonl').read_text().splitlines()]
    samples=[r['busy_cpu_cores'] for r in rows if r['elapsed_seconds']>=4]
    return dict(samples=len(rows),median_busy_cpu_cores=float(np.median(samples)),
        peak_sampled_child_rss_gib=max(r['child_rss_bytes'] for r in rows)/2**30,
        resources_sha256=sha(folder/'resources.jsonl'))

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    dest=ROOT/'mfv_pair_audit.json'
    if dest.exists():raise ValueError('Completed audit exists; do not overwrite')
    build=json.loads((ROOT/'build.json').read_text())
    source=ROOT/'native_io.c'
    if sha(source)!=build['pinned_files'][source.name]:raise ValueError('Source evidence hash changed')
    if 'DMAX(All.MinEgySpec, SphP[pindex].InternalEnergyPred)' not in source.read_text():
        raise ValueError('Native energy-output convention differs')
    records=[];cases=[]
    for mode,law in ((0,'sharp13'),(1,'tanh13')):
        folder=ROOT/'runs'/f'L3_mfv_{law}'
        case=json.loads((folder/'result.json').read_text());cases.append(case)
        if (case['variant'],case['mode'],case['level'],case['returncode'])!=('mfv',mode,3,0):
            raise ValueError('Unexpected native case/termination')
        for name,key in (('params.txt','input_sha256'),('ics.hdf5','ic_sha256')):
            if sha(folder/name)!=case[key]:raise ValueError('Native input changed')
        if sha(ROOT/'GIZMO_mfv_pair')!=case['binary_sha256']:raise ValueError('Executable changed')
        log=(folder/'run.log').read_text()
        if 'Simulation ends.' not in log or 'Final time=' not in log:raise ValueError('No native terminal marker')
        frames=[];bad=[];expected=dict(BASE,ParticleVelocities='float32')
        for path in snapshots(folder/'output'):
            digest=sha(path)
            with h5py.File(path,'r') as h:
                g=h['PartType0'];arrays={k:v[:] for k,v in g.items()}
                if {k:str(v.dtype) for k,v in arrays.items()}!=expected:raise ValueError('Unexpected schema')
                ids=arrays['ParticleIDs'];t=float(h['Header'].attrs['Time'])
                if len(ids)!=65536 or len(np.unique(ids))!=65536:raise ValueError('Unexpected element IDs')
                row=dict(snapshot=str(path),sha256=digest,time_code=t,t_over_tcc=t/case['physics']['t_cc'],fields={})
                for name,x in arrays.items():
                    finite=np.isfinite(x);positive=name in ('Masses','Density','InternalEnergy','SmoothingLength')
                    invalid=(~finite)|((x<=0) if positive else np.zeros(x.shape,dtype=bool))
                    row['fields'][name]=dict(dtype=str(x.dtype),min=float(x[finite].min()) if np.any(finite) else None,
                        max=float(x[finite].max()) if np.any(finite) else None,
                        nonfinite=int(np.count_nonzero(~finite)),nonpositive=int(np.count_nonzero(x<=0)) if positive else None)
                    ii=np.flatnonzero(invalid if x.ndim==1 else np.any(invalid,axis=1))
                    if len(ii):
                        # Every offending ID is recorded, not only a small sample.
                        bad.append(dict(snapshot=path.name,t_over_tcc=row['t_over_tcc'],field=name,count=len(ii),
                            ids=ids[ii].tolist(),values=x[ii].tolist(),masses=arrays['Masses'][ii].tolist(),
                            density=arrays['Density'][ii].tolist(),positions=arrays['Coordinates'][ii].tolist()))
            if sha(path)!=digest:raise ValueError('Snapshot changed during read')
            frames.append(row)
        cadence=check_times([r['time_code'] for r in frames],case['physics'])
        record=dict(law=law,mode=mode,status='needs_review' if bad else 'fields_passed_only',
            returncode=case['returncode'],wall_seconds=case['wall_seconds'],peak_child_rss_gib=case['peak_child_rss_gib'],
            input_sha256=case['input_sha256'],ic_sha256=case['ic_sha256'],binary_sha256=case['binary_sha256'],
            cadence=cadence,resources=resource_summary(folder),bad_snapshots=len({r['snapshot'] for r in bad}),
            bad_fields=sorted({r['field'] for r in bad}),first_bad=bad[0] if bad else None,
            bad_entries=bad,frames=frames,
            restart_files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in restart_files(folder)])
        records.append(record)
        print(json.dumps({k:v for k,v in record.items() if k not in ('frames','bad_entries','restart_files')},indent=2),flush=True)
    report=dict(status='needs_review_not_certified',scope='Native MFV L3 sharp/historical failure comparison only.',
        script_sha256=sha(__file__),native_io_sha256=sha(source),paired_initial_checks=pair(*cases),cases=records,
        original_batch_sha256=sha(ROOT/'full_l3_batch.json'),failure_control_sha256=sha(ROOT/'mfv_failure_control.json'),
        interpretation='Stored InternalEnergy is the floor-clamped predicted value, not necessarily conserved energy. Zero output fails the positive-state requirement; its occurrence in both laws does not isolate the numerical cause. No native values, floors, cadence or files changed. Neither MFV control is counted as a validated full comparison.')
    save(dest,report)

if __name__=='__main__':main()
