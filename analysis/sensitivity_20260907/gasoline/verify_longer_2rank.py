"""Audit every saved state against the prospective protocol; no tolerance changes."""
import itertools
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
sys.path.insert(0,str(ROOT/'runner_longer_2rank_v1'))
import longer_checks_v2 as l
import gasoline_controls as g
sys.path.append(str(ROOT))
import verify_instrumentation_v3 as v
OUT=ROOT/'longer_2rank_audit_v1'


def compare(a,b,chi,gamma):
    exact={k:bool(np.array_equal(a[k],b[k])) for k in ('mass','eps','metals','phi')}
    dense=bool(np.array_equal(a['rho'].astype(np.float64)>chi/3,
                             b['rho'].astype(np.float64)>chi/3))
    precision={
        'rho':l.within_spacing(a['rho'],b['rho'],1.),
        'temp':l.within_spacing(a['temp'],b['temp'],1/((gamma-1)*chi)),
        'vel':l.within_spacing(a['vel'],b['vel'],2*np.sqrt(gamma)),
        'pos':l.within_spacing(a['pos'],b['pos'],.3125,np.array([20.,10.,10.]))}
    return dict(passed=all(exact.values()) and dense and all(x['passed'] for x in precision.values()),
                dense_membership_exact=dense,required_exact_fields=exact,
                finite_precision=precision,all_TIPSY_fields_bitwise_equal=bool(np.array_equal(a,b)))


def main():
    batch_path=l.WORK/'batch.json'
    if not batch_path.exists():raise RuntimeError('Native diagnostics not finished; do not start audit')
    if OUT.exists():raise FileExistsError('Existing audit must not be overwritten')
    batch=json.loads(batch_path.read_text())
    assert batch['status']=='native_diagnostics_finished_pending_field_validation'
    prep=json.loads((l.WORK/'preparation.json').read_text())
    bundle=json.loads((ROOT/'runner_longer_2rank_v1/bundle.json').read_text())
    for path,want in bundle['pinned_files'].items():assert g.sha(path)==want,path
    OUT.mkdir();v.OUT=OUT
    report=dict(status='checking',states=[],comparisons=[],full_science_controls_completed=0,
                protocol_sha256=prep['protocol_sha256'],solver_batch_sha256=g.sha(batch_path),
                cases=batch['cases'],initial={},limitations=[
                 '120 steps through approximately 1 t_cc only; not a full5 t_cc science run.',
                 'Finite-precision mass-diagnostic equivalence is not strict bitwise equivalence.',
                 'Original periodic boundaries, variable particle masses and SPH pressure mismatch retained.',
                 'Evolved cached pressure and saved energy represent different native stages.'])
    arrays={}
    try:
        for item in prep['cases']:
            case=item['name'];folder=l.WORK/case
            p=g.params((folder/'run.param').read_text())
            assert g.sha(folder/'run.param')==item['parameter_sha256']
            gamma=float(p['dConstGamma']);chi=100.
            if int(p['nSteps'])!=120 or int(p['iOutInterval'])!=6:raise ValueError('Unexpected native cadence')
            time=0.;expected={}
            for step in range(1,121):
                time+=float(p['dDelta'])
                if step%6==0:expected[f'state.{step:06d}']=time
            if item['hook']:expected['state.initial']=0.
            found={x.name for x in folder.iterdir() if x.is_file() and
                   (x.name=='state.initial' or (x.name.startswith('state.') and x.name[6:].isdigit()))}
            assert found==set(expected),(case,found)
            for name,want in sorted(expected.items(),key=lambda x:x[1]):
                path=folder/name;before=g.sha(path);t,a=g.read(path)
                assert len(a)==65536 and t==want,(case,name,t,want)
                ids=v.iorder(path,len(a));a=a[np.argsort(ids)]
                arrays[(case,name)]=a
                sidecars={}
                for f in sorted(folder.glob(name+'.*')):
                    vals=v.sidecar(f)
                    assert len(vals)==len(a)
                    if f.suffix in ('.pres','.SPHH'):assert (vals>0).all(),str(f)
                    sidecars[f.name]=dict(sha256=g.sha(f),bytes=f.stat().st_size)
                mass=v.sums(a['mass'].astype(float),a['rho'].astype(float),a['metals'].astype(float))
                independent=v.independent(path,mass)
                assert g.sha(path)==before
                report['states'].append(dict(case=case,path=str(path),sha256=before,
                    time_code=t,time_tcc=t/(np.sqrt(chi)/(2*np.sqrt(gamma))),count=len(a),
                    mass_sums=mass,independent=independent,sidecars=sidecars))
                if name=='state.initial':
                    ic=g.read(folder/'ic.std')[1]
                    for k in ('pos','mass','vel','temp','metals'):assert np.array_equal(a[k],ic[k]),k
                    pressure=(gamma-1)*a['rho'].astype(float)*a['temp'].astype(float)*g.energy_factor(p)
                    native_pressure=v.sidecar(str(path)+'.pres')[np.argsort(ids)]
                    err=float(np.max(abs(native_pressure-pressure)/pressure))
                    assert err<=8*np.finfo(np.float32).eps
                    report['initial']=dict(native_IC_fields_exact=True,pressure_min=float(pressure.min()),
                        pressure_max=float(pressure.max()),native_pressure_recovery_error=err,
                        dense_mass=mass[1],color_mass=mass[2])
            # Probe all preserved checkpoint headers again, including final-valid flag.
            check=l.checkpoints(folder,item['keep_checkpoints'])
            old=json.loads((folder/'checkpoint_validation.json').read_text())
            assert check==old
            print('independently checked',case,len(expected),'states and',len(check),'checkpoints',flush=True)
        for a,b in itertools.combinations([x['name'] for x in prep['cases']],2):
            for step in range(6,121,6):
                name=f'state.{step:06d}'
                result=compare(arrays[(a,name)],arrays[(b,name)],chi,gamma)
                report['comparisons'].append(dict(first=a,second=b,snapshot=name,**result))
        report['native_output_count']=len(report['states'])
        report['finite_precision_comparisons_passed']=all(x['passed'] for x in report['comparisons'])
        report['bitwise_comparisons_passed']=all(x['all_TIPSY_fields_bitwise_equal'] for x in report['comparisons'])
        report['status']='passed_prospective_one_tcc_mass_diagnostic_checks' if report['finite_precision_comparisons_passed'] else 'prospective_comparison_failed_needs_review'
        g.write_new(OUT/'report.json',report)
        print(json.dumps({k:report[k] for k in ('status','native_output_count','finite_precision_comparisons_passed','bitwise_comparisons_passed','initial')},indent=2))
    except Exception as exc:
        report.update(status='audit_stopped_needs_review',error=repr(exc))
        g.write_new(OUT/'partial_report.json',report)
        raise


if __name__=='__main__':main()
