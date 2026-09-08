"""Finish the never-started historical MFV control to characterize a native failure.

This is not resuming a failed run, changing numerics, or approving the sharp
case's zero-energy states. Original batch and all native files are retained.
"""
import fcntl,json,sys
from pathlib import Path
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1')
from run_full_l3 import ROOT,sha,save,check_dependencies,run_case

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    dest=ROOT/'mfv_failure_control.json'
    if dest.exists():raise ValueError('Existing failure control requires review')
    batch=json.loads((ROOT/'full_l3_batch.json').read_text());plan=batch['plan'];check_dependencies(plan)
    audit=json.loads((ROOT/'mfv_field_audit.json').read_text())
    if batch['status']!='stopped_needs_review' or len(batch['finished'])!=2 or audit['snapshots']!=101 or {x['field'] for x in audit['bad_fields']}!={'InternalEnergy'}:
        raise ValueError('Unexpected source failure; do not launch')
    folder=ROOT/'runs'/'L3_mfv_tanh13';case=json.loads((folder/'result.json').read_text())
    if (case['status'],case['variant'],case['mode'],case['level'])!=('prepared','mfv',1,3):raise ValueError('Case is not the never-started control')
    if any((folder/x).exists() for x in ('run.log','resources.jsonl')) or any((folder/'output').iterdir()):raise ValueError('Evidence of prior execution; not a resume')
    if sha(folder/'params.txt')!=case['input_sha256'] or sha(folder/'ics.hdf5')!=case['ic_sha256']:raise ValueError('Prepared input changed')
    report=dict(status='running_diagnostic_control',original_batch_sha256=sha(ROOT/'full_l3_batch.json'),
        source_field_audit_sha256=sha(ROOT/'mfv_field_audit.json'),script_sha256=sha(__file__),
        scope='Previously prepared historical MFV case, unchanged settings, to compare native thermal-output failure. Sharp case not certified.')
    save(dest,report)
    try:
        result=run_case(case,plan)
        report.update(status='native_control_passed_checks_pair_still_incomplete',case=result)
    except Exception as exc:
        report.update(status='control_needs_review',error=str(exc),case=json.loads((folder/'result.json').read_text()))
    finally:save(dest,report)
    print(json.dumps({k:v for k,v in report.items() if k!='case'},indent=2),flush=True)

if __name__=='__main__':main()
