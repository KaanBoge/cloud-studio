"""Reconcile requested campaign with verified new-run manifests, without launching."""
import collections
import json
from pathlib import Path

OUT=Path('/mnt/c/Users/kaanb/CloudCrushing/performance_20260907c')
FAMILIES={'athpp':'Athena++','apk':'AthenaPK','athw':'Athena 4.2','enzo':'Enzo',
          'enzoe':'Enzo-E','flash':'FLASH 4.8','flashx':'Flash-X','ramses':'RAMSES',
          'arepo':'Arepo','gzmfm':'GIZMO MFM','gzmfv':'GIZMO MFV','gadget4':'Gadget-4','gas':'Gasoline'}


def main():
    recent=json.loads(Path('/home/kaan/restart_20260907/batch.json').read_text())
    queue=json.loads(Path('/home/kaan/queued_20260907/queue.json').read_text())
    finished={(r['code'],r['level'],r['chi']):r for r in recent['finished']}
    finished.update({(j['code'],j['level'],j['chi']):j['result'] for j in queue['jobs'] if j['status']=='completed'})
    held={(j['code'],j['level'],j['chi']):j for j in queue['jobs'] if j['status']=='held_resources'}
    rows=[]
    for code,name in FAMILIES.items():
        for level in range(1,7):
            for chi in (10,100,1000):
                key=code,level,chi
                row=dict(code=code,name=name,level=level,chi=chi,mach=2,
                         dimensions_streamwise=[8*2**level,4*2**level,4*2**level],
                         target_native_times=101,status='needs_native_run_and_reuse_audit')
                if key in finished:
                    proof=finished[key]
                    folder=Path(proof['directory'])
                    native=json.loads((folder/'provenance.json').read_text())
                    ic=json.loads((folder/'initial_conditions.json').read_text())
                    paths=[folder/x[1] for x in native['native_time_rows']]
                    if native['status']=='finished_native_checks_passed' and ic['passed'] and all(p.exists() for p in paths):
                        row.update(status='completed_basic_native_checks',directory=str(folder),
                            native_snapshots=native['unique_snapshots'],publication='not yet published',
                            comparison_validation='BC/tracer matching, common time and retention still need review')
                    else:row.update(status='evidence_needs_review',directory=str(folder))
                elif key in held:
                    row.update(status='queued_storage_hold',directory=held[key]['directory'],
                        required_free_gib=held[key]['required_with_safety_gib'])
                elif level in (1,2):
                    row['prerequisite']='Coarse cloud/edge resolution and native output-cadence validation'
                elif code in ('arepo','gzmfm','gzmfv','gadget4','gas'):
                    row['prerequisite']='Validate native particle density/resolution, tracer and boundary implementation; IC generation alone is insufficient'
                else:
                    row['prerequisite']='Review retained historical native runs for reuse, then verify complete-run launcher, boundary conditions and tracer'
                rows.append(row)
    report=dict(scope='Requested Mach-2 nonradiative baseline, not a declaration that every old run must be repeated.',
        memory_sources=['C:/Users/kaanb/.claude/projects/C--/memory/cloud-crushing-mentorship.md',
                        'C:/Users/kaanb/.claude/projects/C--/memory/cloud-crushing-3d-ceiling.md'],
        memory_caveat='August notes are historical and contain superseded IC, resolution-limit and deletion claims. Current September audit takes precedence.',
        code_families=12,solver_variants=13,target_cells=len(rows),
        counts=dict(collections.Counter(r['status'] for r in rows)),baseline=rows,
        further_work=[
            {'task':'Mach 0.5, 1.5 and 5 subsets','status':'historical outputs require corrected-IC/reuse audit; not enabled by this queue'},
            {'task':'Figure 1 common late time in 2D slices and genuine 3D, plus terrain visualization','status':'needs all-material retention and matched-time checks; 2D visualization is not a new 2D simulation'},
            {'task':'Figure 2 mass evolution with overplotted resolutions','status':'use retained native cells, initial mass denominator, measured time; new L3/L4 raw series now available'},
            {'task':'Galilean tracking','status':'restart/coordinate checks passed, retention failed at chi100/1000; not ready for matched production'},
            {'task':'Radiative cooling','status':'old cooling-labelled runs had cooling disabled; physical scale, cooling table/integrator tests required before reruns from t=0'},
            {'task':'MHD','status':'separate research extension; transverse-boundary instability requires validation'},
            {'task':'Publish all measured native times','status':'12 new corrected runs are local only; validate exports before adding, never replace raw data with visualization'}])
    (OUT/'campaign_inventory.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ('code_families','solver_variants','target_cells','counts')},indent=2))


if __name__=='__main__':main()
