"""Native initial pairs and independent yt sums; no material tracer is inferred."""
import gc,json,re
from pathlib import Path
import numpy as np
import yt
from yt.frontends.gizmo.api import GizmoDataset
from yt.frontends.gadget.io import IOHandlerGadgetHDF5  # register Gizmo's shared HDF5 I/O handler
from smoke_gizmo import ROOT,sha,read,save,physics
yt.set_log_level(40)
BASE={'Coordinates':'float64','Density':'float32','InternalEnergy':'float32','Masses':'float32',
    'ParticleChildIDsNumber':'uint32','ParticleIDGenerationNumber':'uint32','ParticleIDs':'uint32','SmoothingLength':'float32','Velocities':'float32'}

def snapshots(folder):
    paths=[]
    for path in folder.glob('snapshot_*.hdf5'):
        if re.fullmatch(r'snapshot_\d+\.hdf5',path.name):paths.append(path)
        elif not re.fullmatch(r'snapshot_\d+\.hsml\.hdf5',path.name):raise ValueError('Unexpected snapshot-like file')
    return sorted(paths)

def native(path,p,variant):
    a,t=read(path);expected=dict(BASE)
    if variant=='mfv':expected['ParticleVelocities']='float32'
    if {k:str(v.dtype) for k,v in a.items()}!=expected:raise ValueError('Native fields/precision differ')
    for key in ('Masses','Density','InternalEnergy','SmoothingLength'):
        if np.any(a[key]<=0):raise ValueError('Nonpositive native field')
    pos=a['Coordinates'];bounds=np.array([p['domain_left'],p['domain_right']])
    if np.any(pos<bounds[0]-1e-6) or np.any(pos>bounds[1]+1e-6):raise ValueError('Native coordinates outside periodic box')
    return a,t

def sums(a,p):
    m=a['Masses'].astype(float);rho=a['Density'].astype(float)
    return dict(total_mass=float(m.sum()),dense_mass=float(m[rho>p['rho_wind']*p['chi']/3].sum()))

def timing_evidence(case,ic,original):
    # Native run.c kicks before the first save; io.c writes conserved, staggered
    # P.Vel. Do not pretend this array is the input velocity at header Time=0.
    # Require the isolated two-step-size recovery test for this exact binary/law.
    from audit_snapshot_timing import scaling_check
    path=ROOT/'snapshot_timing_audit_v2'/'report.json';report=json.loads(path.read_text())
    if report['status']!='passed':raise ValueError('Missing verified native output-timing evidence')
    cases=[r for r in report['diagnostics'] if (r['variant'],r['mode'])==(case['variant'],case['mode'])]
    cases=sorted(cases,key=lambda r:r['max_timestep'],reverse=True)
    if [r['max_timestep'] for r in cases]!=[1e-5,5e-6]:raise ValueError('Incomplete timestep-scaling pair')
    velocities=[]
    for row in cases:
        folder=Path(row['directory'])
        if row['returncode']!=0 or row['binary_sha256']!=case['binary_sha256'] or sha(folder/'params.txt')!=row['input_sha256'] or sha(folder/'ics.hdf5')!=row['ic_sha256']:
            raise ValueError('Timing-evidence provenance differs')
        dic,_=read(folder/'ics.hdf5')
        if set(dic)!=set(ic) or any(not np.array_equal(dic[k],ic[k]) for k in ic):raise ValueError('Timing test uses different ICs')
        d,t=native(Path(row['snapshots'][0]),case['physics'],case['variant'])
        if t!=0:raise ValueError('Timing test is not the initial output')
        for key in ('Coordinates','Masses','ParticleIDs','InternalEnergy','Density','SmoothingLength'):
            if not np.array_equal(d[key],original[key]):raise ValueError('Timing-test native baseline differs '+key)
        velocities.append(d['Velocities'])
    return dict(report_sha256=sha(path),checks=scaling_check(ic['Velocities'],*velocities),
        native_t0_velocity_max_offset=float(np.max(abs(original['Velocities'].astype(float)-ic['Velocities']))),
        interpretation='Native output velocity is staggered after the first half kick, not the input at header t=0. No native values are replaced. Velocity-at-header-time diagnostics are not validated by this mass study.')

def initial(case):
    p=case['physics'];folder=Path(case['directory']);ic,t0=read(folder/'ics.hdf5');d,t=native(snapshots(folder/'output')[0],p,case['variant'])
    if t!=0 or t0!=0:raise ValueError('Native initial time mismatch')
    for k in ('Coordinates','Masses','ParticleIDs','InternalEnergy'):
        if not np.array_equal(ic[k],d[k]):raise ValueError('Native initial recovery differs '+k)
    rho_lattice=ic['Masses'].astype(float)/(20/(8*2**case['level']))**3
    pressure=(p['gamma']-1)*d['Density'].astype(float)*d['InternalEnergy'].astype(float)
    return dict(native_density_vs_lattice_max_relative=float(np.max(abs(d['Density']-rho_lattice)/rho_lattice)),
        native_pressure_vs_uniform_max_absolute=float(np.max(abs(pressure-p['p_wind']))),native_fields_exactly_recovered=['Coordinates','Masses','ParticleIDs','InternalEnergy'],
        velocity_output_timing=timing_evidence(case,ic,d))

def pair(a,b):
    if a['variant']!=b['variant'] or a['level']!=b['level'] or a['input_sha256']!=b['input_sha256'] or a['binary_sha256']!=b['binary_sha256']:raise ValueError('Confounded pair')
    folders=[Path(c['directory']) for c in (a,b)];ics=[read(f/'ics.hdf5')[0] for f in folders]
    for key in ics[0]:
        if key!='Velocities' and not np.array_equal(ics[0][key],ics[1][key]):raise ValueError('Nonvelocity IC changed '+key)
    data=[native(snapshots(f/'output')[0],a['physics'],a['variant'])[0] for f in folders]
    for key in data[0]:
        if key not in ('Velocities','ParticleVelocities') and not np.array_equal(data[0][key],data[1][key]):raise ValueError('Other native initial field differs '+key)
    difference=float(np.max(abs(data[0]['Velocities']-data[1]['Velocities'])))
    if difference<1e-6:raise ValueError('Velocity did not change')
    return dict(native_nonvelocity_initial_fields_exact=True,ic_nonvelocity_fields_exact=True,velocity_difference=difference,
        native_initial_deviations=[initial(c) for c in (a,b)])

def yt_check(path,p,variant):
    before=sha(path);a,t=native(path,p,variant);target=sums(a,p)
    ds=GizmoDataset(str(path),bounding_box=np.array([p['domain_left'],p['domain_right']]).T);ad=ds.all_data()
    m=ad['PartType0','Masses'].to_value('code_mass').astype(float);rho=ad['PartType0','Density'].to_value('code_density').astype(float)
    if len(m)!=len(a['Masses']) or abs(ds.current_time.to_value('code_time')-t)>1e-12:raise ValueError('yt particle/time coverage differs')
    measured=dict(total_mass=float(m.sum()),dense_mass=float(m[rho>p['rho_wind']*p['chi']/3].sum()))
    errors={k:abs(measured[k]-v)/max(abs(v),1e-12) for k,v in target.items()}
    if max(errors.values())>1e-11 or sha(path)!=before:raise ValueError('Independent sum/input hash failed')
    del ad,ds,a;gc.collect();return errors

def main():
    batch=json.loads((ROOT/'smoke_batch.json').read_text());cases={(c['variant'],c['mode']):c for c in batch['finished']}
    if batch['status']!='collected_pending_pair_validation' or set(cases)!={(v,m) for v in ('mfm','mfv') for m in (0,1)}:raise ValueError('Four smokes required')
    pairs=[];checks=[]
    for variant in ('mfm','mfv'):
        pairs.append(dict(variant=variant,checks=pair(cases[variant,0],cases[variant,1])))
        for mode in (0,1):
            c=cases[variant,mode]
            for path in snapshots(Path(c['directory'])/'output'):checks.append(dict(snapshot=str(path),relative_errors=yt_check(path,c['physics'],variant)))
    record=dict(status='passed',pairs=pairs,independent_checks=checks,reader='Explicit yt GizmoDataset, native fields, float64 aggregation, rectangular box',
        smoke_sha256=sha(ROOT/'smoke_batch.json'),script_sha256=sha(__file__),
        caveats=['All boundaries periodic; not identical to grid inflow/outflow.','Native density/pressure deviations reported, not erased.',
            'Native Velocities are staggered after a kick, including header t=0. Two-step-size native recovery is verified; velocity-at-header-time analysis still requires explicit treatment.',
            'ID-selected mass is not passive material tracing for MFV; no tracer retention is claimed.'])
    save(ROOT/'verification.json',record);print(json.dumps(record,indent=2))

if __name__=='__main__':main()
