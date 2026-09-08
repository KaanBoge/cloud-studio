"""Test and freeze the new L3 runner. Does not run or overwrite simulations."""
import json,shutil,subprocess,sys
from pathlib import Path
from gadget_controls import ROOT,STAGED,dependencies,sha,save,storage_snapshot,require_storage
from run_full_l3 import budget

def main():
    dependencies();proof=json.loads((ROOT/'verification_v2.json').read_text())
    if proof['status']!='passed_L3_initial_and_short_evolved_mass_checks' or sha(STAGED/'verify_gadget.py')!=proof['checker_sha256']:raise ValueError('Independent validation changed')
    audit=json.loads((ROOT/'native_cadence_audit.json').read_text())
    if audit['status']!='passed_exact_native_schedule' or sha(STAGED/'native_cadence.py')!=audit['corrected_checker_sha256']:raise ValueError('Missing native schedule evidence')
    dest=ROOT/'runner_l3_v2'
    if dest.exists():raise ValueError('Frozen runner already exists')
    tests=[]
    for name in ('test_gadget_controls.py','test_verify_gadget.py','test_full_l3.py','test_native_cadence.py'):
        result=subprocess.run([sys.executable,str(STAGED/name)],capture_output=True,text=True,check=True)
        tests.append(dict(script=name,sha256=sha(STAGED/name),returncode=result.returncode,output=result.stdout+result.stderr))
    retained=budget();capacity=storage_snapshot(ROOT);require_storage(capacity,retained['pair_bytes'])
    dest.mkdir()
    for name in ('run_full_l3_v2.py','verify_gadget.py','native_cadence.py','test_native_cadence.py','test_verify_gadget.py'):
        shutil.copy2(STAGED/name,dest/name)
    bundle=dict(status='tested_for_revalidation_and_unstarted_historical_L3',files={path.name:sha(path) for path in dest.iterdir()},tests=tests,
        native_cadence_audit_sha256=sha(ROOT/'native_cadence_audit.json'),original_full_bundle_sha256=sha(ROOT/'runner_l3_v1/bundle.json'),
        native_build_sha256=sha(ROOT/'build.json'),verification_sha256=sha(ROOT/'verification_v2.json'),budget=retained,capacity_at_freeze=capacity,
        caveat='Within existing Gadget-4 SPH initialization only: pressure peaks3.90x nominal in both laws. Not a uniform-pressure grid-code baseline. No smoothing-length patch or numerical setting changed.')
    save(dest/'bundle.json',bundle);print(json.dumps(bundle,indent=2))

if __name__=='__main__':main()
