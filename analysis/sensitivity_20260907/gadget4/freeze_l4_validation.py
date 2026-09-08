"""Freeze NEW L4 validation scripts; no native solver rebuild or run here."""
import json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,STAGED,sha,save,dependencies

dest=ROOT/'runner_validation_l4_v2'
if dest.exists():raise ValueError('Existing frozen validation cannot be overwritten')
dependencies()
files={name:STAGED/name for name in ('gadget_l4_controls.py','test_gadget_l4.py')}
prior=ROOT/'runner_l3_v2';old=json.loads((prior/'bundle.json').read_text())
for name in ('native_cadence.py','test_native_cadence.py'):
    if sha(prior/name)!=old['files'][name]:raise ValueError('Source-derived scheduler helper changed')
    files[name]=prior/name
before={str(path):sha(path) for path in files.values()}
dependencies_to_pin=[ROOT/name for name in ('gadget_controls.py','build.json','experiment.json')]
dependencies_to_pin.append(Path('/home/kaan/verified_20260907/storage_guard.py'))
pins={str(path):sha(path) for path in dependencies_to_pin}
dest.mkdir()
for name,path in files.items():shutil.copy2(path,dest/name)
if any(sha(path)!=digest for path,digest in before.items()):raise ValueError('Validation source changed during freeze')
pins.update({str(dest/name):sha(dest/name) for name in files})
tests=subprocess.run([sys.executable,str(dest/'test_gadget_l4.py')],capture_output=True,text=True,check=True)
cadence=subprocess.run([sys.executable,str(dest/'test_native_cadence.py')],capture_output=True,text=True,check=True)
proof=dict(status='tested_L4_validation_only',pinned_files=pins,tests=tests.stdout+tests.stderr,native_cadence_tests=cadence.stdout+cadence.stderr,
    scope='Native L4 short validation and measured full-pair storage audit only. No full controls or existing outputs changed.',
    previous_attempt='runner_validation_l4_v1 is retained incomplete: freeze used a nonexistent root scheduler path; no native case was launched. V2 copies the exact pinned scheduler into its own bundle and tests that frozen copy.')
save(dest/'bundle.json',proof);print(json.dumps(proof,indent=2))
