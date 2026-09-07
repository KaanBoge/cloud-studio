"""Short native-solver 3D tests; all outputs retained in a separate audit directory."""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from check_snapshot import check

WORK = Path('/home/kaan/ic_audit_20260907')
AUDIT = Path(__file__).resolve().parent
VW = 2 * math.sqrt(5/3)


def set_flat(text, values):
    for key, value in values.items():
        expression = rf'(?im)^\s*{re.escape(key)}\s*=.*$'
        if re.search(expression, text):
            text = re.sub(expression, f'{key} = {value}', text)
        else:
            text += f'\n{key} = {value}\n'
    return text


def set_sections(text, changes):
    chunks = re.split(r'(?m)^\s*<([^>]+)>\s*$', text)
    present = set()
    for i in range(1, len(chunks), 2):
        name = chunks[i].strip()
        if name in changes:
            chunks[i+1] = '\n' + set_flat(chunks[i+1], changes[name]).strip() + '\n\n'
            present.add(name)
    out = chunks[0] + ''.join(f'<{chunks[i]}>\n{chunks[i+1]}' for i in range(1,len(chunks),2))
    for name in changes.keys() - present:
        out += f'\n<{name}>\n' + '\n'.join(f'{k} = {v}' for k,v in changes[name].items()) + '\n'
    return out


def input_for(kind, chi):
    if kind == 'athpp':
        original = Path('/home/kaan/codes/athenapp/runs/M3D_ATHPP_L5_chi10/athinput.cloud_wind').read_text()
        return 'athinput', set_sections(original, {'mesh': {'nx1':64,'nx2':32,'nx3':32},
            'meshblock': {'nx1':16,'nx2':16,'nx3':16}, 'time': {'nlim':2,'tlim':.001},
            'output1':{'dt':.001}, 'output2':{'dt':.001},
            'problem':{'drat':chi,'rv_scale':1.3,'Mach':2},'hydro':{'gamma':repr(5/3)}}), [0,0,0]
    if kind == 'apk':
        original = Path('/home/kaan/codes/athenapk/runs/APK2D_chi10_512/athinput.cloud_wind_apk').read_text()
        return 'athinput', set_sections(original, {'parthenon/mesh': {'nx1':32,'nx2':64,'nx3':32},
            'parthenon/meshblock': {'nx1':16,'nx2':16,'nx3':16}, 'parthenon/time': {'nlim':2,'tlim':.001},
            'parthenon/output0':{'dt':.001}, 'parthenon/output1':{'dt':.001},
            'problem/cloud':{'rho_cloud_cgs':chi,'rv_scale':1.3,'v_wind_cgs':repr(VW)}}), [0,0,0]
    if kind == 'enzo':
        original = Path('/home/kaan/codes/enzo/runs/CW3D_chi10_256/CloudWind.enzo').read_text()
        return 'CloudWind.enzo', set_flat(original, {'TopGridDimensions':'64 32 32','StopTime':.001,
            'StopCycle':2,'dtDataDump':.001,'CloudWindChi':chi,'CloudWindVelocity':repr(VW),'Gamma':repr(5/3)}), [0,0,0]
    if kind in ('flash','flashx'):
        path = '/home/kaan/CloudCrushing/A8/M3D_FLASH48_L6_chi10/flash.par' if kind == 'flash' else '/home/kaan/codes/flashx/runs/prod3d_l6_chi10/flash.par'
        original = Path(path).read_text()
        center = [.3,.5,.5] if kind == 'flash' else [0,0,0]
        return 'flash.par', set_flat(original, {'lrefine_min':2,'lrefine_max':2, 'Nblockx':2,'Nblocky':1,'Nblockz':1,
            'sim_rhoCloud':chi,'sim_windVel':repr(VW),'sim_rvScale':1.3,'gamma':repr(5/3),
            'tmax':.001,'nend':2,'plotfileIntervalTime':.001,'checkpointFileIntervalTime':.001,
            'run_comment':'"IC verification only, sharp velocity at 1.3 R"'}), center
    if kind == 'athw':
        original = Path('/home/kaan/CloudCrushing/A8/M3D_ATHW_L6_chi10/athinput').read_text()
        return 'athinput', set_sections(original, {'domain1':{'Nx1':64,'Nx2':32,'Nx3':32,'NGrid_x1':1,'NGrid_x2':1,'NGrid_x3':1},
            'time':{'nlim':2,'tlim':.001},'output1':{'dt':.001},'output2':{'dt':.001},
            'problem':{'drat':chi,'rv_scale':1.3,'Mach':2,'gamma':repr(5/3)}}), [0,0,0]
    raise ValueError(kind)


def run_one(kind, chi):
    run = WORK/'grid_tests'/f'{kind}_chi{chi}'
    if (run/'verification.json').exists():
        return json.loads((run/'verification.json').read_text())
    run.mkdir(parents=True, exist_ok=False)
    name, text, center = input_for(kind, chi)
    (run/name).write_text(text)
    binary = WORK/'bin'/kind
    command = ['mpirun','-np','1',str(binary)]
    if kind in ('apk','athpp','athw'):
        command += ['-i', name]
    elif kind == 'enzo':
        command += [name]
    with open(run/'run.log','x') as log:
        rc = subprocess.run(command,cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
    result = {'kind':kind,'chi':chi,'solver_returncode':rc,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
    patterns = {'athpp':'*.athdf','apk':'*.phdf','enzo':'DD0000/CW_0000', 'athw':'id0/*.vtk',
                'flash':'*hdf5_chk_0000','flashx':'*hdf5_chk_0000'}
    snapshots = sorted(run.glob(patterns[kind]))
    if rc != 0 or not snapshots:
        result.update(passed=False,error='Solver failed or initial output missing',log_tail=(run/'run.log').read_text(errors='replace')[-2200:])
    else:
        try:
            result.update(check(str(snapshots[0]),str(run/name),kind,center,(64,32,32)))
        except Exception as e:
            result.update(passed=False,error=str(e))
    (run/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('kinds',nargs='+')
    args=p.parse_args()
    results=[]
    for kind in args.kinds:
        for chi in (10,100,1000):
            result=run_one(kind,chi)
            results.append(result)
            print(json.dumps(result),flush=True)
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)
