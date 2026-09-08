"""Isolated copies of real native binaries, configuration and actual IC writers."""
import fcntl,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/gizmo')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/gizmo')
NATIVE=Path('/home/kaan/codes/gizmo')

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    if ROOT.exists():raise ValueError('Existing setup requires review')
    require_storage(storage_snapshot(NATIVE),GIB)
    sources={'generator_sharp.py':NATIVE/'scripts/make_cloudwind_ic.py',
        'generator_historical.py':Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/gizmo/scripts/make_cloudwind_ic.py'),
        'experiment.json':STAGED/'experiment.json','native_io.c':NATIVE/'io.c','native_begrun.c':NATIVE/'begrun.c'}
    expected={}
    for variant,method in (('mfm','MASS'),('mfv','VOLUME')):
        sources[f'GIZMO_{variant}_pair']=NATIVE/f'GIZMO_{variant.upper()}_3D_PER'
        sources[f'Config_{variant}.sh']=NATIVE/f'Config_{variant.upper()}_3D_periodic.sh'
        expected[variant]=[f'HYDRO_MESHLESS_FINITE_{method}','BOX_PERIODIC','BOX_LONG_X=2','SELFGRAVITY_OFF','EOS_GAMMA=(5.0/3.0)']
        active=[x.split('#')[0].strip() for x in sources[f'Config_{variant}.sh'].read_text().splitlines() if x.split('#')[0].strip()]
        if active!=expected[variant]:raise ValueError('Unexpected native flags')
        for level in (3,4,5):sources[f'params_{variant}_L{level}.txt']=NATIVE/f'runs/GZ_L{level}_chi100_{variant}/params.txt'
    if 'f_v = (r <= rv_scale * 1.0).astype(float)' not in sources['generator_sharp.py'].read_text():raise ValueError('Sharp law missing')
    if 'f_v = 0.5 * (1.0 - np.tanh((r - rv_scale * 1.0) / 0.1))' not in sources['generator_historical.py'].read_text():raise ValueError('Historical law missing')
    before={str(p):sha(p) for p in sources.values()};ROOT.mkdir()
    for name,path in sources.items():shutil.copy2(path,ROOT/name)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('Canonical file changed while copying')
    report=dict(compiled_anything=False,source_files_unchanged=before,pinned_files={n:sha(ROOT/n) for n in sources},expected_config=expected,
        scope='Native binaries and actual writers pinned; not a validated evolved pair until smoke checks pass. Native solver source evidence stays local.')
    (ROOT/'build.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
