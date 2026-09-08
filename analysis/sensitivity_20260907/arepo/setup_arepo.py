"""Pin the existing native Arepo binary and both real generator versions; no build."""
import fcntl,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/arepo')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/arepo')
NATIVE=Path('/home/kaan/codes/arepo')

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    if ROOT.exists():raise ValueError('Existing native study directory requires review')
    require_storage(storage_snapshot(NATIVE),GIB);ROOT.mkdir()
    source={'Arepo_pair':NATIVE/'Arepo_3d','generator_sharp.py':NATIVE/'runs/make_ic_cloud.py',
        'generator_historical.py':Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/arepo/runs/make_ic_cloud.py'),
        'Config.sh':NATIVE/'Config.sh','allvars.h':NATIVE/'src/main/allvars.h','native_init.c':NATIVE/'src/init/init.c',
        'native_io_fields.c':NATIVE/'src/io/io_fields.c','experiment.json':STAGED/'experiment.json'}
    for l in (3,4,5):source[f'param_L{l}.txt']=NATIVE/f'runs/AREPO3D_L{l}_chi100/param.txt'
    historical=source['generator_historical.py'].read_text()
    if 'f_v = 0.5 * (1.0 - np.tanh((r - args.rv_scale * R_cloud) / dr_edge))' not in historical:raise ValueError('Historical law absent')
    if 'f_v = (r <= args.rv_scale * R_cloud).astype(float)' not in source['generator_sharp.py'].read_text():raise ValueError('Corrected law absent')
    config=source['Config.sh'].read_text();active=[x.split('#')[0].strip() for x in config.splitlines() if x.split('#')[0].strip()]
    expected={'LONG_X=2.0','PASSIVE_SCALARS=1','REGULARIZE_MESH_CM_DRIFT','REGULARIZE_MESH_CM_DRIFT_USE_SOUNDSPEED',
        'REGULARIZE_MESH_FACE_ANGLE','TREE_BASED_TIMESTEPS','DOUBLEPRECISION=1','INPUT_IN_DOUBLEPRECISION',
        'OUTPUT_IN_DOUBLEPRECISION','OUTPUT_CENTER_OF_MASS','HAVE_HDF5','REFLECTIVE_Y=2','REFLECTIVE_Z=2'}
    if set(active)!=expected:raise ValueError('Unreviewed compile settings')
    if '#define GAMMA (5. / 3.)' not in source['allvars.h'].read_text():raise ValueError('Default Gamma changed')
    before={str(p):sha(p) for p in source.values()}
    for name,p in source.items():shutil.copy2(p,ROOT/name)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('Source changed while copying')
    report=dict(binary=str(ROOT/'Arepo_pair'),binary_sha256=sha(ROOT/'Arepo_pair'),compiled_anything=False,
        source_files_unchanged=before,pinned_files={name:sha(ROOT/name) for name in source},expected_config=sorted(expected),
        scope='Native Arepo_3d executable; only input velocity changes. Generated IC and native Voronoi states require separate verification.')
    (ROOT/'build.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
