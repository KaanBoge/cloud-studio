"""Recheck saved native outputs and exercise the corrected mass diagnostics."""
import json
import subprocess
import sys
from pathlib import Path
from check_snapshot import check
from run_params import parse_file
from grid_smokes import input_for

ROOT=Path('/home/kaan/ic_audit_20260907')
HERE=Path(__file__).resolve().parent
results=[]
for kind in ('athpp','apk','flash','flashx','enzo','athw'):
    for chi in (10,100,1000):
        run=ROOT/'grid_tests'/f'{kind}_chi{chi}'
        param,unused,center=input_for(kind,chi)
        pattern={'athpp':'*.athdf','apk':'*.phdf','flash':'*hdf5_chk_????',
                 'flashx':'*hdf5_chk_????','enzo':'DD????/CW_????','athw':'id0/*.vtk'}[kind]
        files=sorted(run.glob(pattern))
        result=check(str(files[0]),str(run/param),kind,center,(64,32,32))
        assert result['passed'],result
        results.append({'code':kind,'chi':chi,**result})
        (run/'verification_final.json').write_text(json.dumps(result,indent=2))
        out=run/'mass_diagnostics_v2.json'
        if not out.exists():
            subprocess.run([sys.executable,str(HERE/'diagnostics_v2.py'),'--params',str(run/param),
                            '--kind',kind,'--group','IC-audit-short-tests-not-science-production',
                            '--out',str(out),*map(str,files)],check=True,stdout=subprocess.DEVNULL)
        d=json.loads(out.read_text())
        assert d['series'][0]['dense_mass_over_initial_dense_mass']==1
        assert d['initial_grid']['finest_equivalent_dimensions']==[64,32,32]
        print(kind,chi,'native IC + mass diagnostic pass',flush=True)
for chi in (10,100,1000):
    run=ROOT/'ramses_rect_tests'/f'chi{chi}'
    out=run/'mass_diagnostics_v2.json'
    if not out.exists():
        subprocess.run([sys.executable,str(HERE/'diagnostics_v2.py'),'--params',str(run/'run.nml'),
                        '--kind','ramses','--group','IC-audit-short-tests-not-science-production',
                        '--out',str(out),*map(str,sorted(run.glob('output_?????')))],check=True,stdout=subprocess.DEVNULL)
    d=json.loads(out.read_text())
    assert d['initial_grid']['leaf_cells']==65536
    assert d['initial_grid']['finest_equivalent_dimensions']==[64,32,32]
    assert d['series'][0]['dense_mass_over_initial_dense_mass']==1
    print('ramses',chi,'all native cells + mass diagnostic pass',flush=True)
(ROOT/'final_checks.json').write_text(json.dumps(results,indent=2))
