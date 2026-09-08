"""Three predeclared short native force traces, never full production controls."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import psutil

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
TREE=ROOT/'force_order_native_v1'
PREP=ROOT/'force_order_prepare_v1'
OUT=ROOT/'force_order_runner_v1'
CASES=ROOT/'force_order_cases_v1'
CORE=ROOT/'force_trace_core_v1'
NAMES=('off_a','off_b','on')
PY='/home/kaan/venv/bin/python'
BINARY_SHA='789dd4625f9ef2f3ed32bd731be207b617d5b723e66ae4d6300846af8adb686b'
sys.path.insert(0,str(ROOT/'serial_observer_runner_v2'))
import serial_observer_run_v2 as common
sha,save=common.sha,common.save


def environment(base,name):
    if name not in NAMES:raise ValueError('Not a predeclared diagnostic')
    common.check_environment(base)
    result=dict(base)
    result.update(GASOLINE_CLOUD_INITIAL_OUTPUT='1' if name=='on' else '0',
                  GASOLINE_CLOUD_KEEP_CHECKPOINTS='1',GASOLINE_CLOUD_FORCE_TRACE='1',
                  OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result.pop('GASOLINE_CLOUD_SERIAL_AUDIT',None)
    return result


def check_pins(plan):
    for path,h in plan['pins'].items():
        if sha(path)!=h:raise ValueError('Frozen file changed '+path)


def prepare():
    if OUT.exists() or CASES.exists():raise FileExistsError('Preserve existing trace runner/cases')
    resources=common.resources()
    build=json.loads((PREP/'build_manifest.json').read_text())
    if build['status']!='native_trace_adapter_built_not_run' or build['binary_sha256']!=BINARY_SHA:
        raise ValueError('Wrong reviewed native trace build')
    pins={str(TREE/rel):h for rel,h in build['native_hashes'].items()}
    check_pins(dict(pins=pins))
    OUT.mkdir();CASES.mkdir()
    here=Path(__file__).resolve().parent
    for name in ('run_force_order.py','test_run_force_order.py','FORCE_ORDER_TRACE_DESIGN.md'):
        shutil.copyfile(here/name,OUT/name)
    shutil.copyfile(CORE/'force_trace_replay.py',OUT/'force_trace_replay.py')
    origin=ROOT/'longer_validation_2rank_v1/retained_on'
    design_path=ROOT/'instrumentation_v1/preparation.json'
    chi=float(json.loads(design_path.read_text())['chi'])
    if chi!=100.:raise ValueError('Not the fixed-chi sensitivity recipe')
    base_env=json.loads((origin/'native_environment.json').read_text())
    common.check_environment(base_env)
    text=common.input_six((origin/'run.param').read_text())
    for name in NAMES:
        case=CASES/name;case.mkdir()
        with (case/'run.param').open('x') as f:f.write(text)
        shutil.copyfile(origin/'ic.std',case/'ic.std')
        save(case/'native_environment.json',environment(base_env,name))
        for path in case.iterdir():pins[str(path)]=sha(path)
    audit={}
    with common.locks():
        common.subprocess_checked([PY,'-B','-m','unittest','-v','test_run_force_order'],
                                  OUT/'runner_tests.log',cwd=OUT,timeout=30)
        for symbol in ('SphPressureTermsSym','combSphPressureTerms'):
            log=OUT/(symbol+'.asm')
            common.subprocess_checked(['objdump','--no-show-raw-insn','-d','--disassemble='+symbol,
                                      str(TREE/'gasoline/gasoline')],log,timeout=30)
            mnemonics=re.findall(r'^\s*[0-9a-f]+:\s+(\S+)',log.read_text(),re.M)
            if not mnemonics or any(re.match(r'v?f(madd|msub|nmadd|nmsub)|f(add|sub|mul|div|ld|st)',m) for m in mnemonics):
                raise ValueError('Unreviewed fused/x87 force arithmetic')
            required=('addsd',) if symbol.startswith('comb') else ('addsd','subsd','mulsd')
            if any(m not in mnemonics for m in required):raise ValueError('Expected scalar-double path absent')
            audit[symbol]={m:mnemonics.count(m) for m in required}
    for path in list(OUT.iterdir())+[PREP/'build_manifest.json',PREP/'copy_manifest.json',
        origin/'run.param',origin/'ic.std',origin/'native_environment.json',
        Path(base_env['PKDGRAV_CHECKPOINT_FDL']),ROOT/'checkpoint_probe',
        ROOT/'read_only_divergence_v1/review_divergence.py',
        ROOT/'runner_instrumentation_v1/gasoline_controls.py',
        ROOT/'serial_observer_runner_v2/serial_observer_run_v2.py',design_path]:
        if path.is_file():pins[str(path)]=sha(path)
    plan=dict(status='frozen_three_case_force_trace_ready',pins=pins,binary_sha256=BINARY_SHA,
        cases=list(NAMES),chi=chi,chi_source=str(design_path),ranks=2,steps=6,seconds_cap_per_case=60,total_stage_bytes_cap=1024**3,
        per_case_trace_bytes_cap=128*1024**2,initial_resources=resources,compiled_arithmetic=audit,
        full_controls_added=0,old_field_gate_still_failed=True,
        limitations=['Instruction inspection supports scalar-double replay, not absence of instrumentation effects.',
                    'Trace covers selected force accumulators, not the full velocity kick or trajectory.'])
    save(OUT/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],compiled_arithmetic=audit),indent=2))


def stage_bytes():
    return sum(p.stat().st_size for root in (TREE,PREP,OUT,CASES) for p in root.rglob('*') if p.is_file())


def run_case(plan,name):
    case=CASES/name
    if (case/'started.json').exists():raise FileExistsError('Case already attempted')
    check_pins(plan);resources=common.resources()
    if stage_bytes()>plan['total_stage_bytes_cap']:raise RuntimeError('Whole stage retention cap')
    env=os.environ.copy();env.pop('GASOLINE_CLOUD_SERIAL_AUDIT',None)
    env.update(json.loads((case/'native_environment.json').read_text()))
    binary=TREE/'gasoline/gasoline'
    cmd=['nice','-n','19','mpirun','--bind-to','core','-np','2',str(binary),'run.param']
    samples=[];reason=None;stop_at=None;last_size_check=-1.
    with common.locks(),(case/'run.out').open('x') as log:
        start=time.monotonic()
        proc=subprocess.Popen(cmd,cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(case/'started.json',dict(pid=proc.pid,command=cmd,binary_sha256=BINARY_SHA,
            plan_sha256=sha(OUT/'plan.json'),resources=resources))
        while proc.poll() is None:
            elapsed=time.monotonic()-start;rss=0;cpu=0.
            try:
                for child in psutil.Process(proc.pid).children(recursive=True):
                    try:
                        if child.exe()==str(binary):
                            rss+=child.memory_info().rss;ct=child.cpu_times();cpu+=ct.user+ct.system
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            except psutil.NoSuchProcess:pass
            samples.append([elapsed,rss,cpu])
            if reason is None:
                try:
                    common.resources(preflight=False)
                    if elapsed-last_size_check>=1.:
                        last_size_check=elapsed
                        if stage_bytes()>plan['total_stage_bytes_cap']:raise RuntimeError('Whole stage retention cap')
                except Exception as exc:reason=repr(exc)
                if elapsed>60:reason='60 second native cap'
                if reason:
                    with (case/'STOP').open('x') as f:f.write('1\n')
                    stop_at=time.monotonic()
            if stop_at is not None and time.monotonic()-stop_at>10:
                if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.05)
        rc=proc.wait(timeout=5);elapsed=time.monotonic()-start
    rates=[(b[2]-a[2])/(b[0]-a[0]) for a,b in zip(samples,samples[1:])
           if a[1] and b[1] and b[2]>=a[2] and b[0]>a[0]]
    result=dict(exit_code=rc,wall_seconds=elapsed,guard=reason,samples=samples,ranks=2,gpu_used=False,
        peak_solver_rss_bytes=max((x[1] for x in samples),default=0),
        median_busy_cpu_workers=float(np.median(rates)) if rates else None)
    save(case/'native_result.json',result)
    if rc or reason:raise RuntimeError('Native trace stopped; retained '+name)
    return result


def validate_case(name,chi):
    case=CASES/name
    sys.path.insert(0,str(ROOT/'read_only_divergence_v1'))
    import review_divergence as reader
    sys.path.insert(0,str(OUT));import force_trace_replay as replay
    from yt.frontends.tipsy.api import TipsyDataset
    p=common.parameters((case/'run.param').read_text());terminal=0.
    for _ in range(6):terminal+=float(p['dDelta'])
    names=['state.000006'] if name!='on' else ['state.initial','state.000006']
    found={x.name for x in case.iterdir() if x.is_file() and
        (x.name=='state.initial' or (x.name.startswith('state.') and x.name[6:].isdigit()))}
    if found!=set(names):raise ValueError('Unexpected actual snapshot population')
    checkpoints=list(case.glob('state.step*.chk'))
    if len(checkpoints)!=1:raise ValueError('Expected one finalized step6 checkpoint')
    checkpoint=checkpoints[0]
    head=json.loads(subprocess.check_output([str(ROOT/'checkpoint_probe'),str(checkpoint)],text=True,timeout=15))
    if (head['valid'],head['version'],head['step'],head['count'],head['time'])!=(1,8,6,65536,terminal):
        raise ValueError('Finalized native checkpoint header mismatch')
    if checkpoint.stat().st_size!=head['particle_offset']+65536*120:raise ValueError('Checkpoint payload incomplete')
    states=[]
    for filename in names:
        path=case/filename;t,a=reader.tipsy(path)
        if t!=(0. if filename=='state.initial' else terminal) or len(a)!=65536:
            raise ValueError('Native snapshot time/count mismatch')
        if filename=='state.initial':
            sys.path.insert(0,str(ROOT/'runner_instrumentation_v1'));import gasoline_controls as g
            ic=g.read(case/'ic.std')[1]
            for field in ('pos','vel','mass','temp','metals'):
                if not np.array_equal(ic[field],a[field]):raise ValueError('Initial IC changed '+field)
        direct=[float(a['mass'].astype(float).sum()),float(a['mass'][a['rho']>chi/3].astype(float).sum())]
        ds=TipsyDataset(str(path),parameter_file=str(case/'run.param'),bounding_box=[[-10,10],[-5,5],[-5,5]],
            index_filename=str(OUT/(name+'_'+filename+'.index5')),kdtree_filename=str(OUT/(name+'_'+filename+'.kdtree')))
        ds._periodicity=(False,False,False);ad=ds.all_data()
        m=ad['Gas','Mass'].to_value('code_mass').astype(float)
        rho=ad['Gas','Density'].to_value('code_mass/code_length**3').astype(float)
        independent=[float(m.sum()),float(m[rho>chi/3].sum())]
        rel=[abs(x-y)/max(abs(x),1.) for x,y in zip(direct,independent)]
        if max(rel)>1e-12:raise ValueError('Independent native mass check failed')
        states.append(dict(path=str(path),sha256=sha(path),time_code=t,count=len(a),direct_mass=direct,
                           yt_mass=independent,relative_difference=rel))
    native=dict(states=states,checkpoint=dict(path=str(checkpoint),sha256=sha(checkpoint),header=head))
    save(case/'native_validation.json',native)
    paths=[case/('force.rank%02d.bin'%rank) for rank in (0,1)]
    if any(x.stat().st_size>replay.CAP for x in paths):raise ValueError('Native trace cap exceeded')
    trace=replay.validate_case([x.read_bytes() for x in paths])
    markers=re.findall(r'CLOUD_FORCE_TRACE_COMPLETE rank=(\d+) phases=(\d+) records=(\d+)',(case/'run.out').read_text())
    expected=[(str(x['rank']),str(len(x['phases'])),str(x['records'])) for x in trace['ranks']]
    if sorted(markers)!=expected:raise ValueError('Missing/duplicate trace finalization marker')
    trace['files']={str(x):sha(x) for x in paths}
    save(case/'trace_validation.json',trace)
    return dict(name=name,native=native,trace=trace)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    if args.prepare==args.run:raise ValueError('Choose exactly one stage')
    if args.prepare:prepare();return
    if any((OUT/x).exists() for x in ('report.json','failure.json','started.json')):
        raise FileExistsError('Do not repeat attempted native traces')
    plan=json.loads((OUT/'plan.json').read_text())
    if plan['status']!='frozen_three_case_force_trace_ready':raise ValueError('Not a reviewed frozen runner')
    check_pins(plan);save(OUT/'started.json',dict(plan_sha256=sha(OUT/'plan.json')))
    cases=[]
    try:
        for name in NAMES:
            result=run_case(plan,name);checked=validate_case(name,plan['chi']);checked['native_result']=result;cases.append(checked)
        check_pins(plan)
        original=json.loads((PREP/'copy_manifest.json').read_text())['original']
        for rel,h in original.items():
            if sha(ROOT/'native_retained'/rel)!=h:raise ValueError('Original native tree changed')
        report=dict(status='three_native_force_traces_recorded_and_replayed',cases=cases,
            native_states_added=sum(len(x['native']['states']) for x in cases),full_controls_added=0,
            accepted_study_total=46,old_field_gate_still_failed=True,
            causal_comparison_pending=True,plan_sha256=sha(OUT/'plan.json'))
        save(OUT/'report.json',report)
        print(json.dumps(dict(status=report['status'],native_states_added=report['native_states_added'],
            case_seconds=[x['native_result']['wall_seconds'] for x in cases],causal_comparison_pending=True),indent=2))
    except Exception as exc:
        save(OUT/'failure.json',dict(status='native_force_trace_stopped_needs_review',error=repr(exc),
            fully_validated_cases=[x['name'] for x in cases],full_controls_added=0))
        raise


if __name__=='__main__':main()
