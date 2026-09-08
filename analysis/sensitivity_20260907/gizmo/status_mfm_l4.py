"""Read-only live L4 status; a readable header is not a validated full snapshot."""
import json
from pathlib import Path
import h5py,psutil
ROOT=Path('/home/kaan/sensitivity_20260907/gizmo')

def main():
    root=ROOT/'full_mfm_l4_v1';record={}
    if (root/'batch.json').exists():
        b=json.loads((root/'batch.json').read_text())
        record.update(batch_status=b['status'],finished_controls=len(b['finished']),error=b.get('error'))
    cases=[]
    for law in ('sharp13','tanh13'):
        folder=root/law
        if not (folder/'result.json').exists():continue
        c=json.loads((folder/'result.json').read_text());paths=sorted((folder/'output').glob('snapshot_[0-9]*.hdf5'))
        row=dict(law=law,saved_status=c['status'],native_files_present=len(paths),wall_seconds=c.get('wall_seconds'))
        for path in reversed(paths):
            try:
                with h5py.File(path,'r') as f:t=float(f['Header'].attrs['Time'])
            except OSError:continue
            row.update(latest_readable_header=path.name,t_over_tcc=t/c['physics']['t_cc']);break
        resources=folder/'resources.jsonl'
        if resources.exists():
            for line in reversed(resources.read_text().splitlines()):
                try:row['resource_sample']=json.loads(line);break
                except json.JSONDecodeError:continue
        cases.append(row)
    workers=[]
    for proc in psutil.process_iter(['pid','name','status']):
        if proc.info['name']=='GIZMO_mfm_pair':
            try:
                if Path(proc.cwd()).parent==root:workers.append(proc.info)
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    record.update(cases=cases,actual_native_workers=workers,
        note='Files and readable times are progress observations, not accepted full snapshots. Final validation checks every saved state.')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
