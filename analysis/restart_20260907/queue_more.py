"""Persistent manifest, one bounded pass through 18 corrected 3D jobs.

L3 runs first; prepared optimized L5/L6 cases remain held if storage is short.
Run again with --run after resolving resource holds. Never restarts partial data.
No deletion, repeated simulation, cooling, tracking or automatic publication.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import run_l4 as q

r = q.r
WORK = Path('/home/kaan/queued_20260907')
MANIFEST = WORK/'queue.json'


def definition(code, level, chi):
    p = q.profile_for(code, level)
    r.check_proof(p, chi)
    prefix = 'RESTART' if level == 3 else p.get('directory_prefix','OPT')
    target = r.ROOTS[code]/f'{prefix}_sharp13_20260907_L{level}_chi{chi}'
    text = r.input_for(code,level,chi,p['block'],p.get('hdf5_compression_level'))
    if level >= 5:
        r.validate_prepared(target,text,p)
    elif target.exists():
        raise RuntimeError('L3 target already exists; review before adding: '+str(target))
    disk, ram = r.budgets(p)
    return dict(id=f'{code}_L{level}_chi{chi}',code=code,level=level,chi=chi,
                directory=str(target),status='pending',
                binary_sha256=p['binary_sha256'],
                parameter_sha256=hashlib.sha256(text.encode()).hexdigest(),
                required_with_safety_gib=(disk+10*r.GIB)/r.GIB,
                ram_reservation_gib=ram/r.GIB, target_native_times=101)


def verify_unchanged(job):
    p = q.profile_for(job['code'],job['level'])
    r.check_proof(p,job['chi'])
    text = r.input_for(job['code'],job['level'],job['chi'],p['block'],p.get('hdf5_compression_level'))
    if p['binary_sha256'] != job['binary_sha256'] or hashlib.sha256(text.encode()).hexdigest()!=job['parameter_sha256']:
        raise RuntimeError('Queued binary/input changed; explicit review required')
    if job['level'] >= 5:
        r.validate_prepared(Path(job['directory']),text,p)
    elif Path(job['directory']).exists():
        raise RuntimeError('Unexpected existing output: '+job['directory'])
    return p


def prepare():
    WORK.mkdir(exist_ok=True)
    if MANIFEST.exists():
        raise RuntimeError('Queue already exists; not overwriting it')
    jobs = [definition(code,level,chi) for level in (3,5,6)
            for chi in (10,100,1000) for code in ('athpp','apk')]
    q.save(MANIFEST, dict(status='queued',created_at_unix=time.time(),jobs=jobs,
        notes=['L4 is already running separately; not duplicated.',
               'All cases Mach 2, nonradiative, fixed frame; corrected sharp velocity at 1.3 R.',
               'Native tracer definitions still differ; not a certified all-code comparison.',
               'L1/L2 and other-code launchers need additional validation before enabling.',
               'Storage-held jobs need a later --run after storage is resolved.']))
    print('QUEUED 18: 6 L3 and 12 prepared L5/L6; no existing runs overwritten.',flush=True)


def mark_job(job, status, **extra):
    job.update(status=status,updated_at_unix=time.time(),**extra)


def execute():
    with (WORK/'worker.lock').open('a') as worker:
        fcntl.flock(worker,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest = json.loads(MANIFEST.read_text())
        manifest.update(status='waiting_for_current_batch',pid=os.getpid())
        q.save(MANIFEST,manifest)
        # This separate worker waits without occupying a compute core.
        with (r.WORK/'production.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            fcntl.flock(lock,fcntl.LOCK_UN)
        old = json.loads((Path('/home/kaan/restart_20260907')/'batch.json').read_text())
        if old['status'] != 'finished_native_checks_passed':
            manifest.update(status='needs_review',error='Preceding L4 batch did not validate')
            q.save(MANIFEST,manifest)
            return
        q.WORK = WORK
        for job in manifest['jobs']:
            if job['status']=='completed': continue
            if job['status'] not in ('pending','held_resources'):
                manifest.update(status='needs_review',error='Partial or failed job must be reviewed: '+job['id'])
                q.save(MANIFEST,manifest)
                return
            try:
                p = verify_unchanged(job)
                storage = r.storage_snapshot(r.ROOTS[job['code']])
                try:
                    r.require_storage(storage,r.budgets(p)[0])
                except RuntimeError as error:
                    mark_job(job,'held_resources',reason=str(error),storage_preflight=storage)
                    q.save(MANIFEST,manifest)
                    continue
                manifest.update(status='running',current=job['id'])
                mark_job(job,'running'); q.save(MANIFEST,manifest)
                if job['level']==3:
                    with (r.WORK/'production.lock').open('a') as lock:
                        fcntl.flock(lock,fcntl.LOCK_EX)
                        result = q.run_case(job['code'],job['chi'],3)
                else:
                    with (WORK/(job['id']+'.launcher.log')).open('x') as log:
                        rc = subprocess.run([sys.executable,str(r.HERE/'run_optimized.py'),
                            '--code',job['code'],'--level',str(job['level']),'--chi',str(job['chi']),
                            '--resume-prepared','--run'],stdout=log,stderr=subprocess.STDOUT).returncode
                    target = Path(job['directory'])
                    native = json.loads((target/'provenance.json').read_text())
                    if native.get('returncode')!=0:
                        raise RuntimeError(f'Optimized launch/native failure (launcher rc={rc})')
                    # The older launcher flags actual step-time offsets for review.
                    # Validate all outputs without pretending those offsets are zero.
                    result = q.validate_fields(target,job['code'],native['physical_parameters']['t_cc'])
                    from check_snapshot import check
                    dims=[8*2**job['level'],4*2**job['level'],4*2**job['level']]
                    ic=check(str(target/result['native_time_rows'][0][1]),str(target/'athinput'),job['code'],[0,0,0],dims)
                    q.save(target/'queue_initial_conditions.json',ic)
                    if not ic['passed'] or not result['complete_outputs']:
                        raise RuntimeError('IC/output validation failed')
                    q.save(target/'queue_validation.json',result)
                mark_job(job,'completed',result=result)
                print('COMPLETED '+job['id'],flush=True)
            except Exception as error:
                mark_job(job,'needs_review',error=str(error))
                manifest.update(status='needs_review',error=str(error))
                q.save(MANIFEST,manifest)
                raise
            q.save(MANIFEST,manifest)
        held=sum(j['status']=='held_resources' for j in manifest['jobs'])
        manifest.update(status='held_resources' if held else 'completed',current=None,
                        completed=sum(j['status']=='completed' for j in manifest['jobs']),held=held)
        q.save(MANIFEST,manifest)
        print(f"QUEUE PASS: {manifest['completed']} completed; {held} held for resources",flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare',action='store_true')
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    if args.prepare: prepare()
    if args.run: execute()
    if not args.prepare and not args.run:
        print('Use --prepare once, then --run. No action taken.')
