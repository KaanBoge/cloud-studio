"""Test and freeze the new L3 runner. Does not run or overwrite simulations."""
import json,shutil,subprocess,sys
from pathlib import Path
from gadget_controls import ROOT,STAGED,dependencies,sha,save,storage_snapshot,require_storage
from run_full_l3 import budget

def main():
    dependencies();proof=json.loads((ROOT/'verification_v2.json').read_text())
    if proof['status']!='passed_L3_initial_and_short_evolved_mass_checks' or sha(STAGED/'verify_gadget.py')!=proof['checker_sha256']:raise ValueError('Independent validation changed')
    dest=ROOT/'runner_l3_v1'
    if dest.exists():raise ValueError('Frozen runner already exists')
    tests=[]
    for name in ('test_gadget_controls.py','test_verify_gadget.py','test_full_l3.py'):
        result=subprocess.run([sys.executable,str(STAGED/name)],capture_output=True,text=True,check=True)
        tests.append(dict(script=name,sha256=sha(STAGED/name),returncode=result.returncode,output=result.stdout+result.stderr))
    retained=budget();capacity=storage_snapshot(ROOT);require_storage(capacity,retained['pair_bytes'])
    dest.mkdir()
    for name in ('run_full_l3.py','verify_gadget.py','test_full_l3.py','test_verify_gadget.py'):
        shutil.copy2(STAGED/name,dest/name)
    bundle=dict(status='tested_for_full_L3_pair',files={path.name:sha(path) for path in dest.iterdir()},tests=tests,
        native_build_sha256=sha(ROOT/'build.json'),verification_sha256=sha(ROOT/'verification_v2.json'),budget=retained,capacity_at_freeze=capacity,
        caveat='Within existing Gadget-4 SPH initialization only: pressure peaks3.90x nominal in both laws. Not a uniform-pressure grid-code baseline. No smoothing-length patch or numerical setting changed.')
    save(dest/'bundle.json',bundle);print(json.dumps(bundle,indent=2))

if __name__=='__main__':main()
