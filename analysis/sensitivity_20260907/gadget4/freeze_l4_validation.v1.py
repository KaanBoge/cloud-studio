"""Freeze NEW L4 validation scripts; no native solver rebuild or run here."""
import json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,STAGED,sha,save,dependencies

dest=ROOT/'runner_validation_l4_v1'
if dest.exists():raise ValueError('Existing frozen validation cannot be overwritten')
dependencies()
files=['gadget_l4_controls.py','test_gadget_l4.py']
tests=subprocess.run([sys.executable,str(STAGED/'test_gadget_l4.py')],capture_output=True,text=True,check=True)
cadence=subprocess.run([sys.executable,str(STAGED/'test_native_cadence.py')],capture_output=True,text=True,check=True)
before={str(STAGED/name):sha(STAGED/name) for name in files};dest.mkdir()
for name in files:shutil.copy2(STAGED/name,dest/name)
if any(sha(path)!=digest for path,digest in before.items()):raise ValueError('Validation source changed during freeze')
pins={str(dest/name):sha(dest/name) for name in files}
for name in ('gadget_controls.py','native_cadence.py','build.json','experiment.json'):pins[str(ROOT/name)]=sha(ROOT/name)
pins['/home/kaan/verified_20260907/storage_guard.py']=sha('/home/kaan/verified_20260907/storage_guard.py')
proof=dict(status='tested_L4_validation_only',pinned_files=pins,tests=tests.stdout+tests.stderr,native_cadence_tests=cadence.stdout+cadence.stderr,
    scope='Native L4 short validation and measured full-pair storage audit only. No full controls or existing outputs changed.')
save(dest/'bundle.json',proof);print(json.dumps(proof,indent=2))
