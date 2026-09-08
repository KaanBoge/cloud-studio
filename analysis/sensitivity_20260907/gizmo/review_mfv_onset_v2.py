"""Read-only correction of an erroneous 29-bit clock assumption; no native runs."""
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

import h5py
import numpy as np

ROOT=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
sys.path.insert(0,str(ROOT/'onset_runner_v1'))
import mfv_onset as onset
import diagnose_mfv_restart as decoder

HERE=Path(__file__).resolve().parent
sha,check,save_new=onset.sha,onset.check,onset.save_new
BASE_REPORT='d1da6d9d1e5b356fb1dd10e8f34931f316e51529a4865a72442f5757dd7a1d76'
PLAN='52c8ecbea186266d336652bcd0ad4d465de3b2a0a8a19b13880f126e027998ce'


def json_safe(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [json_safe(v) for v in value]
    return value


def clock_schedule(p):
    begin,end,dt,first=[float(p[k]) for k in ['TimeBegin','TimeMax','TimeBetSnapshot','TimeOfFirstSnapshot']]
    check(begin==first==0 and end>0 and dt>0 and float(p['ComovingIntegrationOn'])==0,'Unsupported source schedule')
    tick=(end-begin)/(1<<60);times=[];t=first
    while t<=end:
        check(len(times)<104,'Too many native times')
        times.append(begin+int((t-begin)/tick)*tick);t+=dt
    if times[-1]!=end:times.append(end)
    return times,tick


def verify_clock(times,p):
    expected,tick=clock_schedule(p);tol=2*tick+8*np.finfo(float).eps*float(p['TimeMax'])
    check(len(expected)<=len(times)<=104 and all(math.isfinite(t) for t in times),'Incomplete native schedule')
    check(all(b>=a for a,b in zip(times,times[1:])) and times[0]==0 and abs(times[-1]-float(p['TimeMax']))<=tol,'Native time order/endpoints')
    cursor=0;offsets=[]
    for target in expected:
        while cursor<len(times) and times[cursor]<target-tol:cursor+=1
        check(cursor<len(times) and abs(times[cursor]-target)<=tol,'Missing source-scheduled time')
        offsets.append(abs(times[cursor]-target));cursor+=1
    return dict(bits=60,expected_count=len(expected),actual_count=len(times),tick_code=tick,tolerance_code=tol,max_schedule_offset=max(offsets))


def main():
    check(HERE==ROOT/'onset_review_v2','Use new frozen review directory')
    target=HERE/'report.json';check(not target.exists(),'Completed review exists')
    check(sha(onset.PACKAGE/'plan.json')==PLAN and sha(onset.DEST/'validation.json')==BASE_REPORT,'Changed prior evidence')
    plan=json.loads((onset.PACKAGE/'plan.json').read_text())
    for name,digest in plan['files'].items():check(sha(onset.PACKAGE/name)==digest,'Frozen onset helper changed')
    check(sha(onset.BINARY)==onset.EXPECTED_BINARY,'Wrong repaired binary')
    for name,digest in onset.PINNED_SOURCE.items():check(sha(ROOT/'repaired'/name)==digest,'Native clock source changed')
    header=(ROOT/'repaired/allvars.h').read_text()
    check('#if !defined(LONG_INTEGER_TIME)\n#define LONG_INTEGER_TIME' in header,'Native long-time default not present')
    check('#define  TIMEBINS        60' in header,'Native 60-bit branch absent')
    with (HERE/'tests.log').open('x') as stream:
        subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_onset_clock_v2'],cwd=HERE,
                       stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
    original=json.loads((onset.DEST/'validation.json').read_text())
    check(original['failures']==['Terminal check: Restart endpoint/clock mismatch'],'Unexpected earlier validation failure')
    p,physics,tcc=onset.inputs();raw_checks=[];energy_min=[];times=[]
    for row in original['outputs']:
        path=Path(row['path']);check(sha(path)==row['sha256'],'Native raw changed')
        check(not row['errors'] and max(row['independent_relative_errors'])<1e-11,'Incomplete earlier field/reader check')
        with h5py.File(path,'r') as h:
            time_code=float(h['Header'].attrs['Time']);g=h['PartType0'];m=g['Masses'][:].astype(float);rho=g['Density'][:].astype(float);u=g['InternalEnergy'][:]
            check(all(np.isfinite(v[:]).all() for v in g.values()),'Native nonfinite field')
            check((m>0).all() and (rho>0).all() and (u>0).all() and (g['SmoothingLength'][:]>0).all(),'Native nonpositive field')
        check(time_code==row['time_code'] and float(m.sum())==row['total_mass'] and float(m[rho>physics['chi']*physics['rho_wind']/3].sum())==row['dense_mass'],'Direct raw sums/time differ')
        check(float(min(u))==row['energy_quantiles'][0],'Stored energy minimum differs')
        check(sha(path)==row['sha256'],'Raw changed during review')
        times.append(time_code);energy_min.append(float(min(u)));raw_checks.append(dict(path=str(path),sha256=row['sha256']))
    clock=verify_clock(times,p);oldtimes=[]
    for path in sorted((onset.OLD/'output').glob('snapshot_*.hdf5')):
        with h5py.File(path,'r') as h:oldtimes.append(float(h['Header'].attrs['Time']))
    oldclock=verify_clock(oldtimes,p)
    request={**onset.ABI,'global_data_all_processes':onset.ABI['global_data_all_processes']+['Ti_Current']}
    types,abi=decoder.layouts(decoder.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(onset.BINARY)],text=True)),request)
    check(types['global_data_all_processes'].fields['Ti_Current'][0].itemsize==8,'Native clock ABI is not 64-bit integer')
    parts=[];cells=[];headers=[];files=[];explicit=[]
    for rank in range(8):
        path=onset.DEST/'output/restartfiles'/f'restart.{rank}';digest=sha(path);blob=path.read_bytes();h,a,b,used=decoder.read_prefix(blob,types)
        parts.append(a);cells.append(b);headers.append(h)
        start=types['global_data_all_processes'].itemsize+4+len(a)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(b)))
        check(sha(path)==digest,'Restart changed');files.append(dict(path=str(path),sha256=digest,bytes=len(blob),parsed_prefix_bytes=used))
    h=headers[0];check(all(all(x[k]==h[k] for k in h.dtype.names) for x in headers),'Terminal rank headers differ')
    particles=np.concatenate(parts);gas=np.concatenate(cells);order=np.argsort(particles['ID']);particles,gas=particles[order],gas[order]
    ic,_=onset.short.read_arrays(onset.OLD/'ics.hdf5',False)
    check(np.array_equal(particles['ID'],ic['ParticleIDs']) and (particles['Type']==0).all(),'Native ID/type coverage')
    check(float(h['Time'])==float(h['TimeMax'])==float(p['TimeMax']) and float(h['TimeBegin'])==0,'Wrong terminal time')
    check(float(h['Timebase_interval'])==clock['tick_code'] and int(h['Ti_Current'])==1<<60,'Native clock differs from source')
    check(int(h['TotNumPart'])==int(h['TotN_gas'])==65536 and float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and int(h['ComovingIntegrationOn'])==0,'Native terminal recipe')
    check(all(np.isfinite(gas[k]).all() for k in gas.dtype.names),'Nonfinite terminal gas')
    check(all(np.isfinite(particles[k]).all() for k in particles.dtype.names),'Nonfinite terminal particle')
    check(all((gas[k]>0).all() for k in ['MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred']),'Nonpositive terminal fields')
    account=onset.mass_account(ic['Masses'],gas['MassTrue'],gas['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'],'Independent struct mass differs')
    check(account['passes'] and account['response_detected'],'Original prospective mass gate failed')
    check(all(original['checks']['initial_nonvelocity_exact'].values()),'Initial nonvelocity mismatch')
    terminal_fields={k:dict(minimum=float(min(gas[k])),maximum=float(max(gas[k]))) for k in ['InternalEnergy','InternalEnergyPred','Pressure']}
    report=dict(status='passed_onset_diagnostic_not_full_pair',original_report_sha256=BASE_REPORT,plan_sha256=PLAN,
       correction='Read-only source-derived 60-bit clock audit; original 29-bit checker error retained. No rerun, field or tolerance relaxation.',
       clock=clock,original_headers_clock_check=oldclock,native_terminal_clock=int(h['Ti_Current']),mass_account=account,
       initial_nonvelocity_exact=original['checks']['initial_nonvelocity_exact'],terminal_fields=terminal_fields,
       native_frames=len(times),minimum_stored_energy_all_times=min(energy_min),minimum_stored_energy_final=energy_min[-1],
       native_frames_at_or_after_old_onset=sum(t/tcc>=3.95-1e-12 for t in times),all_raw_hashes=raw_checks,terminal_restarts=files,
       selected_abi=abi,resources=original['resources'],script_sha256=sha(__file__),tests_log_sha256=sha(HERE/'tests.log'),
       protocol_sha256=sha(HERE/'MFV_ONSET_CLOCK_REVIEW.md'),accepted_full_controls=44,completed_full_controls_added=0,
       limitations=['Only one historical-law repaired L3 diagnostic, not a paired result or resolution study.',
                   'Engineering conservation gate is not an arbitrary-flux error theorem or physical accuracy bound.',
                   'No simultaneous velocity, cross-code boundary/pressure, cooling or tracking certification.'])
    report=json_safe(report)
    save_new(target,report)
    print(json.dumps({k:report[k] for k in ['status','native_frames','minimum_stored_energy_all_times','minimum_stored_energy_final','mass_account']}))
    print('report_sha256='+sha(target))


if __name__=='__main__':main()
