"""Independent reader and native initial/evolved validation; never edits raw fields."""
import json,sys
from pathlib import Path
import numpy as np
from yt.frontends.gadget.data_structures import GadgetHDF5Dataset
from yt.frontends.gadget.io import IOHandlerGadgetHDF5
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,NATIVE,read,sha,save,metadata,dependencies,native_summary,parameters,check_ic

def paired_nonvelocity(a,b):
    if set(a)!=set(b):raise ValueError('Native pair schemas differ')
    for key in a:
        if key!='Velocities' and not np.array_equal(a[key],b[key]):raise ValueError('Nonvelocity pair differs: '+key)

def initial_checks(a,ic,p):
    if not np.array_equal(a['ParticleIDs'],ic['ParticleIDs']):raise ValueError('Native IDs changed')
    errors={}
    for key in ('Coordinates','Masses','InternalEnergy','Velocities'):
        expected=ic[key].astype(a[key].dtype)
        bound=4*np.finfo(a[key].dtype).eps*max(float(np.max(abs(expected))),1e-12)
        error=float(np.max(abs(a[key].astype(float)-expected.astype(float))))
        if error>bound:raise ValueError(f'Native initial {key} differs: {error} > {bound}')
        errors[key]=dict(max_absolute_error=error,storage_roundoff_bound=bound)
    nominal=ic['Masses']/(20/64)**3
    return dict(native_vs_ic=errors,native_density_vs_lattice_max_relative=float(np.max(abs(a['Density']/nominal-1))),
        native_pressure_vs_uniform_max_absolute=float(np.max(abs(a['Pressure'].astype(float)-1))),
        scope='Initial header t=0 only. Evolved velocity synchronization needs separate review before time-specific velocity diagnostics.')

def independent(path,p):
    digest=sha(path)
    ds=GadgetHDF5Dataset(str(path),unit_base={'length':(1,'cm'),'mass':(1,'g'),'velocity':(1,'cm/s')},bounding_box=np.array([[0,20],[0,10],[0,10]],float))
    data=ds.all_data();mass=np.asarray(data['PartType0','Masses'].to_value('code_mass'),dtype=float)
    rho=np.asarray(data['PartType0','Density'].to_value('code_density'),dtype=float)
    ids=np.asarray(data['PartType0','ParticleIDs'])
    values=dict(total_mass=float(mass.sum()),dense_mass=float(mass[rho>p['chi']*p['rho_wind']/3].sum()),tagged_mass=float(mass[ids>=p['cloud_id_start']].sum()))
    if ds.cosmological_simulation or len(mass)!=65536 or sha(path)!=digest:raise ValueError('Independent reader altered scope/count/raw')
    if not np.allclose(ds.domain_right_edge.to_value('code_length'),p['box'],rtol=0,atol=1e-12):raise ValueError('Independent domain mismatch')
    return values,float(ds.current_time.to_value('code_time'))

def main():
    dest=ROOT/'verification.json'
    if dest.exists():raise ValueError('Completed validation must not be overwritten')
    build=dependencies();batch=json.loads((ROOT/'smoke_batch.json').read_text());p=metadata()
    if batch['status']!='collected_pending_independent_validation' or [c['mode'] for c in batch['finished']]!=[0,1]:raise ValueError('Incomplete native pair')
    cases=batch['finished'];initial=[];ics=[];result=[]
    if cases[0]['input_sha256']!=cases[1]['input_sha256']:raise ValueError('Paired numerical inputs differ')
    for case in cases:
        folder=Path(case['directory']);ic,t=read(folder/'ics.hdf5');check_ic(ic,3,case['mode'],p);ics.append(ic)
        if sha(folder/'ics.hdf5')!=case['ic_sha256'] or sha(folder/'params.txt')!=case['input_sha256']:raise ValueError('Input hash mismatch')
        rows=[]
        for recorded in case['outputs']:
            path=Path(recorded['snapshot']);a,row=native_summary(path,p)
            if row!=recorded:raise ValueError('Native output ledger changed')
            values,t=independent(path,p)
            if abs(t-row['time_code'])>1e-12:raise ValueError('Independent time mismatch')
            errors={key:abs(value-row[key])/max(abs(row[key]),1e-12) for key,value in values.items()}
            if max(errors.values())>1e-11:raise ValueError('Independent mass sums differ')
            rows.append(dict(**row,independent_relative_errors=errors))
            if row['time_code']==0:initial.append(a)
        if len(rows)!=2 or [r['time_code'] for r in rows]!=[0,.1]:raise ValueError('Review extra/missing times without filtering')
        result.append(dict(mode=case['mode'],initial=initial_checks(initial[-1],ic,p),outputs=rows))
    paired_nonvelocity(ics[0],ics[1]);paired_nonvelocity(initial[0],initial[1])
    legacy=NATIVE/'runs/G4_3D_L3_chi100/ics_L3_chi100.hdf5';old,_=read(legacy)
    if any(not np.array_equal(old[key],ics[1][key]) for key in old) or set(old)!=set(ics[1]):raise ValueError('Archived law does not reproduce historical ladder IC')
    report=dict(status='passed_L3_initial_and_short_evolved_mass_checks',full_science_controls_completed=0,code='Gadget-4 SPH',level=3,
        physics=p,cases=result,original_ladder_ic_sha256=sha(legacy),historical_IC_arrays_exactly_reproduced=True,
        nonvelocity_IC_and_native_initial_fields_exact=True,build_sha256=sha(ROOT/'build.json'),smoke_batch_sha256=sha(ROOT/'smoke_batch.json'),
        checker_sha256=sha(__file__),native_output_count=4,all_raw_retained=True,
        caveats=['Existing mean-mass and periodic smoothing-length seed patch retained in both controls; not pristine upstream binary.',
            'Fully periodic boundaries and kernel pressure/density deviations retained; not a matched grid-code wind tunnel.',
            'ID-tagged in-box mass in a periodic box does not prove no boundary crossing. No passive scalar field is added.',
            'Initial t=0 velocity matches IC at native precision; evolved snapshot velocity synchronization is not certified.',
            'These are two0.1-code-time smokes, not101-snapshot full science controls or a validated higher-level queue.'])
    save(dest,report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
