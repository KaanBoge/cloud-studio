"""Read-only follow-up: MFV uninitialized flux timestep and terminal mass state.

No solver execution or native edits. A warning-only compiler invocation writes
assembly to /dev/null under the shared locks; no native object/binary is replaced.
Uses new DWARF field selections, not a rerun of the completed energy-export audit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import h5py
import numpy as np
from diagnose_mfv_restart import layouts, parse_dwarf, read_prefix, sha, check

ROOT = Path('/home/kaan/sensitivity_20260907/gizmo')
SOURCE = Path('/home/kaan/codes/gizmo')
REQUESTS = {
    'global_data_all_processes': ['Time', 'MinEgySpec', 'Timebase_interval', 'cf_hubble_a'],
    'particle_data': ['ID', 'Mass', 'GravAccel'],
    'gas_cell_data': ['MassTrue', 'dMass', 'DtMass', 'InternalEnergy', 'InternalEnergyPred',
                      'DtInternalEnergy', 'Density', 'Pressure'],
}


def mass_summary(initial, predicted, conserved, integrated_change, derivative):
    arrays = [np.asarray(x, dtype=np.float64) for x in
              (initial, predicted, conserved, integrated_change, derivative)]
    check(all(x.ndim == 1 and x.shape == arrays[0].shape for x in arrays), 'Mass field shapes differ')
    check(len(arrays[0]) > 0 and all(np.all(np.isfinite(x)) for x in arrays), 'Invalid mass arrays')
    initial, predicted, conserved, integrated_change, derivative = arrays
    check(np.all(initial > 0), 'Invalid initial mass')
    return dict(particles=len(initial),
        conserved_mass_different_from_ic=int(np.count_nonzero(conserved != initial)),
        predicted_mass_different_from_conserved=int(np.count_nonzero(predicted != conserved)),
        nonzero_accumulated_dMass=int(np.count_nonzero(integrated_change)),
        nonzero_DtMass=int(np.count_nonzero(derivative)),
        max_abs_conserved_minus_ic=float(np.max(np.abs(conserved-initial))),
        max_abs_DtMass=float(np.max(np.abs(derivative))))


def limiter_probe(energy, derivative, quantum):
    check(energy > 0 and quantum > 0 and all(np.isfinite(x) for x in (energy, derivative, quantum)), 'Invalid limiter inputs')
    trial = energy + derivative * quantum
    return dict(energy=energy, derivative=derivative, clock_quantum=quantum,
        trial_after_one_clock_quantum=trial, would_half_limit=bool(trial < .5*energy),
        max_dt_before_half_limit=(-.5*energy/derivative if derivative < 0 else None),
        interpretation='Counterfactual endpoint probe using saved derivative, not an executed next kick or past limiter count.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    check(not args.out.exists(), 'Refuse to overwrite follow-up report')
    binary = ROOT/'GIZMO_mfv_pair'
    diagnosis_path=ROOT/'mfv_restart_diagnosis_v1.json'
    review_path=ROOT/'mfv_restart_review_v1.json'
    check(sha(diagnosis_path)=='88fbb20c30aeab70b9f7dd60638c05a0abcf1afd876ee091a2ebf0ab5e7956b3', 'Prior diagnosis changed')
    check(sha(review_path)=='23cf16be3830b7d3a153fb8ae62e67e255cb6a8961b945c25250b09f62aa6f4e', 'Prior histories changed')
    d=json.loads(diagnosis_path.read_text()); review=json.loads(review_path.read_text())
    check(sha(binary)==d['binary_sha256'], 'Binary changed')
    commit=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    files=['hydro/hydro_evaluate.h','hydro/hydro_toplevel.c','hydro/hydro_core_meshless.h',
           'kicks.c','predict.c','allvars.h','eos/eos.c']
    hashes={f:sha(SOURCE/f) for f in files}
    for name in files:
        tracked=subprocess.check_output(['git','-C',str(SOURCE),'show',commit+':'+name])
        check(hashlib.sha256(tracked).hexdigest()==hashes[name], 'Tracked native source modified: '+name)
    command=['flock','-n','/home/kaan/performance_20260907/benchmark.lock',
        'flock','-n','/home/kaan/performance_20260907/production.lock','nice','-n','19',
        'mpicc','-g','-O1','-ffast-math','-fcommon','-Wall','-Wuninitialized','-Wmaybe-uninitialized',
        '-DDISABLE_ALIGNED_ALLOC','-DH5_USE_16_API','-I/usr/include/hdf5/openmpi','-I.',
        '-S','hydro/hydro_toplevel.c','-o','/dev/null']
    c=subprocess.run(command,cwd=SOURCE,capture_output=True,text=True,timeout=60)
    check(c.returncode==0 and re.search(r'dt_hydrostep_i.*(?:may be used|is used) uninitialized',c.stderr), 'Expected warning missing')
    warning_lines=[x for x in c.stderr.splitlines() if 'warning:' in x and 'uninitialized' in x]
    dwarf=subprocess.check_output(['readelf','--debug-dump=info',str(binary)],text=True)
    types,abi=layouts(parse_dwarf(dwarf), REQUESTS)
    cases=[]
    for case in d['cases']:
        law=case['law']; folder=ROOT/'runs'/f'L3_mfv_{law}'
        ic=folder/'ics.hdf5'; check(sha(ic)==case['input_hashes']['ics.hdf5'],'IC changed')
        with h5py.File(ic,'r') as f:
            ids=f['PartType0']['ParticleIDs'][:]
            initial=f['PartType0']['Masses'][:][np.argsort(ids)].astype('f8')
        pp,ss,headers=[],[],[]
        for r in case['restarts']:
            path=Path(r['path']); check(sha(path)==r['sha256'],'Restart changed')
            a,part,gas,used=read_prefix(path.read_bytes(),types)
            check(used==r['parsed_prefix_bytes'],'Prefix length changed')
            check(sha(path)==r['sha256'],'Restart changed during read')
            pp.append(part);ss.append(gas);headers.append(a)
        part=np.concatenate(pp);gas=np.concatenate(ss);ix=np.argsort(part['ID']);part=part[ix];gas=gas[ix]
        check(np.array_equal(part['ID'],np.arange(1,65537)),'Unexpected IDs')
        a=headers[0]
        check(all(all(h[n]==a[n] for n in a.dtype.names) for h in headers),'Header disagreement')
        check(a['Time']==case['time_code'] and a['MinEgySpec']==0 and a['cf_hubble_a']==1,'Wrong native endpoint')
        check(np.all(part['GravAccel']==0),'Nonzero gravity would change limiter interpretation')
        metrics=mass_summary(initial,part['Mass'],gas['MassTrue'],gas['dMass'],gas['DtMass'])
        affected=[]
        rc=next(x for x in review['cases'] if x['law']==law)
        for old in case['affected_particles']:
            i=old['id']-1
            check(gas['InternalEnergy'][i]==old['conserved_energy'],'Energy differs from independent prior check')
            hist=rc['terminal_zero_id_histories'][str(old['id'])]
            positive=[x for x in hist if 0<x['internal_energy']<1e-10]
            affected.append(dict(id=old['id'],
                terminal_mass_true=float(gas['MassTrue'][i]), terminal_dMass=float(gas['dMass'][i]),
                terminal_DtMass=float(gas['DtMass'][i]),
                limiter=limiter_probe(float(gas['InternalEnergy'][i]),float(gas['DtInternalEnergy'][i]),float(a['Timebase_interval'])),
                first_saved_positive_energy_below_1e_10=(positive[0] if positive else None),
                history_mass_range=[min(x['mass'] for x in hist),max(x['mass'] for x in hist)],
                caveat='The 1e-10 threshold is a descriptive locator, not an acceptance cutoff. ID histories are not material tracers.'))
        cases.append(dict(law=law, terminal_mass_update=metrics, affected=affected,
            final_time=case['time_code'], restart_sha256=[r['sha256'] for r in case['restarts']]))
    check(all(sha(SOURCE/f)==h for f,h in hashes.items()),'Native source changed during diagnostic')
    report=dict(status='source_defect_confirmed_causal_repair_test_pending',
        created_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(__file__),
        decoder_dependency_sha256=sha(ROOT/'diagnose_mfv_restart.py'),
        prior_diagnosis_sha256=sha(diagnosis_path),prior_review_sha256=sha(review_path),
        binary_sha256=sha(binary),native_source_commit=commit,native_source_hashes=hashes,
        native_files_equal_commit=True,compiler_check=dict(command=command,returncode=c.returncode,
            warning_lines=warning_lines,all_stderr_sha256=hashlib.sha256(c.stderr.encode()).hexdigest(),
            scope='Warning-only compilation to /dev/null, not a rebuilt solver or simulation.'),
        new_compiled_field_layouts=abi,cases=cases,
        interpretation='Uninitialized local dt_hydrostep_i is used for integrated MFV mass flux while '
            'local.dt_hydrostep_i is populated separately. Actual retained terminal mass/flux evidence '
            'is measured above. No single-source cause of every thermal anomaly is asserted without '
            'a prospective isolated correction test. MFM impact requires code-path review, not assumption.',
        native_simulations_started=0,raw_files_changed=0,accepted_full_controls=44)
    with args.out.open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(output=str(args.out),sha256=sha(args.out),
        warning=warning_lines,cases=[dict(law=x['law'],mass=x['terminal_mass_update'],affected=x['affected']) for x in cases]),indent=2))


if __name__=='__main__':
    main()
