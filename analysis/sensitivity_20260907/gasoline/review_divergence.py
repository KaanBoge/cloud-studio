"""Read-only first-saved-divergence and selected checkpoint-prefix investigation.

Uses retained native outputs only. Does not import or run any solver launcher.
No acceptance tolerance is changed, and no full science control is enabled.
"""
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

import numpy as np

ROOT = Path('/home/kaan/sensitivity_20260907/gasoline')
WORK = ROOT / 'longer_validation_2rank_v1'
OUT = ROOT / 'read_only_divergence_v1'
CASES = ('original_a', 'original_b', 'retained_off', 'retained_on')
AUDIT_SHA = '3329dc075b9873cd608aa7a0ff9533ed4215c65145cc573c92190b3a23d544ff'
REVIEW_SHA = 'cf3e6649b73a3254015f4ec4136f09ff9c29d2b4498860930de1e94b28759686'
HEADER = struct.Struct('>d6i')
GAS = np.dtype([('mass','>f4'), ('pos','>f4',3), ('vel','>f4',3),
                ('rho','>f4'), ('temp','>f4'), ('eps','>f4'),
                ('metals','>f4'), ('phi','>f4')])
CHECK = np.dtype(dict(names=['id','flags','mass','eps','pos','vel','u'],
    formats=['<i4','<i4','<f8','<f8',('<f8',3),('<f8',3),'<f8'],
    offsets=[0,4,8,16,24,48,72], itemsize=120))
CHECK_STRUCT = struct.Struct('<ii9d')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_hash(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError('Preserved file hash changed: '+str(path))
    return actual


def write_new(path, obj):
    with Path(path).open('x') as stream:
        json.dump(obj, stream, indent=2, allow_nan=False)


def params(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        line = line.split('#',1)[0].strip()
        if not line:
            continue
        key, value = [x.strip() for x in line.split('=',1)]
        if key in result:
            raise ValueError('Duplicate input '+key)
        result[key] = value
    return result


def temperature_factor(p):
    if p['bGasCooling'] != '0' or p['bGasAdiabatic'] != '1':
        raise ValueError('Unsupported thermodynamics')
    if 'dMsolUnit' in p or 'dKpcUnit' in p or p['bComove'] != '0':
        raise ValueError('Unsupported units/comoving convention')
    # Native duTFac for adiabatic output, not assumed Kelvin.
    return ((float(p['dConstGamma'])-1)*float(p['dMeanMolWeight'])
            /float(p['dGasConst']))


def order(ids, count):
    ids = np.asarray(ids)
    if ids.shape != (count,) or not np.array_equal(np.sort(ids),np.arange(count)):
        raise ValueError('Not a complete native ID permutation')
    return np.argsort(ids)


def tipsy(path):
    path = Path(path)
    with path.open('rb') as stream:
        raw = stream.read(32)
        if len(raw) != 32:
            raise ValueError('Truncated TIPSY header')
        time, n, dim, gas, dark, stars, pad = HEADER.unpack(raw)
        if n <= 0 or gas != n or dim != 3 or dark or stars or not np.isfinite(time):
            raise ValueError('Invalid all-gas TIPSY header')
        if path.stat().st_size != 32+48*n:
            raise ValueError('Incorrect TIPSY payload length')
        data = np.fromfile(stream, GAS, count=n)
    for name in GAS.names:
        if not np.isfinite(data[name]).all():
            raise ValueError('Nonfinite TIPSY '+name)
    for name in ('mass','rho','temp','eps'):
        if not (data[name] > 0).all():
            raise ValueError('Nonpositive TIPSY '+name)
    with Path(str(path)+'.iord').open() as stream:
        if int(stream.readline()) != n:
            raise ValueError('iOrder count mismatch')
        ids = np.loadtxt(stream, dtype=np.float64, ndmin=1)
    return time, data[order(ids,n)]


def prefix(path, offset, count):
    path = Path(path)
    if offset <= 0 or count <= 0 or path.stat().st_size != offset+120*count:
        raise ValueError('Checkpoint payload length mismatch')
    with path.open('rb') as stream:
        stream.seek(offset)
        data = np.fromfile(stream, CHECK, count=count)
    permutation = order(data['id'],count)
    for name in ('mass','eps','pos','vel','u'):
        if not np.isfinite(data[name]).all():
            raise ValueError('Nonfinite checkpoint '+name)
    for name in ('mass','eps','u'):
        if not (data[name] > 0).all():
            raise ValueError('Nonpositive checkpoint '+name)
    # Separate standard-library decoder: prefix fields only, never the tail.
    with path.open('rb') as stream:
        for index in sorted({0,count//2,count-1}):
            stream.seek(offset+120*index)
            row = CHECK_STRUCT.unpack(stream.read(CHECK_STRUCT.size))
            expected = [int(data['id'][index]), int(data['flags'][index]),
                float(data['mass'][index]), float(data['eps'][index]),
                *data['pos'][index].tolist(), *data['vel'][index].tolist(),
                float(data['u'][index])]
            if list(row) != expected:
                raise ValueError('Independent checkpoint prefix decoder mismatch')
    return data[permutation]


def difference(a, b, floor=None):
    a, b = np.asarray(a,dtype=np.float64), np.asarray(b,dtype=np.float64)
    if a.shape != b.shape or a.ndim not in (1,2):
        raise ValueError('Field shape mismatch')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Nonfinite comparison')
    d = np.abs(a-b)
    mask = a != b
    rows = np.flatnonzero(mask if a.ndim==1 else mask.any(axis=1))
    at = np.unravel_index(int(d.argmax()), d.shape)
    out = dict(unequal_components=int(mask.sum()), unequal_particles=len(rows),
        max_absolute=float(d[at]), first_particle_ids=rows[:8].tolist(),
        largest_difference=dict(particle_id=int(at[0]),
            component=int(at[1]) if a.ndim==2 else None,
            first=float(a[at]), second=float(b[at])),
        signed_zero_components=int(((a==0)&(b==0)&(np.signbit(a)!=np.signbit(b))).sum()))
    if floor is not None:
        bound = np.spacing(np.maximum(np.maximum(abs(a),abs(b)),floor).astype(np.float32)).astype(float)
        ratio = d/bound
        bad = ratio > 1
        badids = np.flatnonzero(bad if a.ndim==1 else bad.any(axis=1))
        out.update(max_declared_spacing_ratio=float(ratio.max()),
            exceeding_components=int(bad.sum()), exceeding_particle_ids=badids.tolist())
    return out


def check_export(cp, raw, factor):
    result = {}
    for name in ('mass','eps','pos','vel','u'):
        key = 'temp' if name=='u' else name
        values = cp[name]*factor if name=='u' else cp[name]
        result[key] = bool(np.array_equal(values.astype(np.float32),raw[key]))
    if not all(result.values()):
        raise ValueError('Checkpoint/TIPSY exact selected-field roundtrip failed '+str(result))
    return result


def main():
    if OUT.exists():
        raise FileExistsError('Preserve existing review '+str(OUT))
    audit_path = ROOT/'longer_2rank_audit_v1/report.json'
    review_path = ROOT/'longer_2rank_review_v1.json'
    checked_hash(audit_path,AUDIT_SHA); checked_hash(review_path,REVIEW_SHA)
    audit = json.loads(audit_path.read_text())
    prep = json.loads((WORK/'preparation.json').read_text())
    design = json.loads((ROOT/'instrumentation_v1/preparation.json').read_text())
    if audit['status'] != 'prospective_comparison_failed_needs_review':
        raise ValueError('Unexpected prior audit status')
    if tuple(x['name'] for x in prep['cases']) != CASES:
        raise ValueError('Unexpected diagnostic population')
    OUT.mkdir()
    here = Path(__file__).resolve().parent
    for name in ('review_divergence.py','test_review_divergence.py','DIVERGENCE_REVIEW_PLAN.md'):
        shutil.copyfile(here/name,OUT/name)
    report = dict(status='checking_read_only', original_gate_passed=False,
        full_controls_added=0, accepted_study_total=46, snapshots=[], comparisons=[],
        checkpoint_states=[], checkpoint_comparisons=[], first_saved_differences=[],
        pins={}, limitations=[
            'Earliest SAVED divergence is not necessarily the first differing integration operation.',
            'No new simulation or changed scientific tolerance; original failed gate remains failed.',
            'Checkpoint density/smoothing length and full integration state are not stored.',
            'Only selected initialized checkpoint prefix fields are decoded; unwritten tails ignored.',
            'Source mechanisms remain hypotheses, not controlled causal proof.',
            'Matching dense mass through1tcc does not certify full trajectory/output-hook equivalence.'])
    def pin(path, expected=None):
        path = Path(path)
        h = checked_hash(path,expected) if expected else sha(path)
        report['pins'][str(path)] = h
        return h
    try:
        for path in (audit_path,review_path,WORK/'preparation.json',
                     ROOT/'instrumentation_v1/preparation.json'):
            pin(path)
        for path in OUT.iterdir():
            pin(path)
        objects = [ROOT/'native/gasoline/pkd.o', ROOT/'native_retained/gasoline/pkd.o',
                   Path('/home/kaan/codes/gasoline/pkd.o')]
        if len({pin(path) for path in objects}) != 1:
            raise ValueError('Native checkpoint objects differ; ABI requires new review')
        binary = ROOT/'gasoline_original'
        disassembly = subprocess.check_output(['objdump','-d','-M','intel',
            '--disassemble=pkdWriteCheck',str(binary)],text=True,timeout=15)
        if not all(x in disassembly for x in ('mov    esi,0x78','[rsp+0x48]',
                                              '[rsp+0x8]','[rsp+0x30]','fwrite@plt')):
            raise ValueError('Reviewed native checkpoint writer signature changed')
        with (OUT/'pkdWriteCheck.disassembly.txt').open('x') as stream:
            stream.write(disassembly)
        pin(OUT/'pkdWriteCheck.disassembly.txt')
        for name in ('pkd.h','pkd.c','smooth.c','smoothfcn.c','SphPressureTerms.h','main.c','master.c'):
            pin(ROOT/'native_retained/gasoline'/name)
        pin(ROOT/'native_retained/mdl/mpi/mdl.c')
        pin(ROOT/'checkpoint_probe'); pin(ROOT/'checkpoint_probe.c')
        caseparams = {}
        for item in prep['cases']:
            folder = WORK/item['name']
            pin(item['binary'],item['binary_sha256'])
            pin(folder/'ic.std',item['ic_sha256'])
            pin(folder/'run.param',item['parameter_sha256'])
            caseparams[item['name']] = params(folder/'run.param')
        if any(p != caseparams[CASES[0]] for p in caseparams.values()):
            raise ValueError('Within-test input files differ')
        p = caseparams[CASES[0]]
        factor = temperature_factor(p)
        chi,gamma = float(design['chi']),float(p['dConstGamma'])
        floors = dict(rho=1.,temp=1/((gamma-1)*chi),vel=2*np.sqrt(gamma),pos=.3125)
        report['recipe'] = dict(parameters=p,chi=chi,mach=design['mach'],
            temperature_factor=factor,declared_field_floors=floors,
            checkpoint_prefix_itemsize=CHECK.itemsize,density_in_checkpoint=False)
        bystate = {(row['case'],Path(row['path']).name):row for row in audit['states']}
        first = {}
        for step in range(6,121,6):
            name = f'state.{step:06d}'
            states = {}
            times = []
            for case in CASES:
                row = bystate[(case,name)]
                path = Path(row['path'])
                if path != WORK/case/name:
                    raise ValueError('Unexpected preserved path')
                pin(path,row['sha256'])
                for side,record in row['sidecars'].items():
                    pin(path.parent/side,record['sha256'])
                t,a = tipsy(path)
                if t != row['time_code'] or len(a) != 65536:
                    raise ValueError('Unexpected native state')
                states[case] = a; times.append(t)
                report['snapshots'].append(dict(case=case,step=step,time_code=t,
                                               path=str(path),sha256=row['sha256']))
            if len(set(times)) != 1:
                raise ValueError('Native timestamps differ')
            for ca,cb in itertools.combinations(CASES,2):
                a,b = states[ca],states[cb]
                fields = {key:difference(a[key],b[key],floors.get(key)) for key in GAS.names}
                densea,denseb = a['rho']>chi/3,b['rho']>chi/3
                result = dict(first=ca,second=cb,step=step,time_code=times[0],fields=fields,
                    dense_membership_exact=bool(np.array_equal(densea,denseb)),
                    density_margin_to_threshold=float(min(abs(a['rho'].astype(float)-chi/3).min(),
                                                         abs(b['rho'].astype(float)-chi/3).min())))
                report['comparisons'].append(result)
                for key,value in fields.items():
                    tag = (ca,cb,key)
                    if value['unequal_components'] and tag not in first:
                        first[tag] = dict(first=ca,second=cb,field=key,step=step,
                                          time_code=times[0],details=value)
        report['first_saved_differences'] = list(first.values())
        checks = {}
        for case in CASES:
            checkpoint_manifest = WORK/case/'checkpoint_validation.json'
            pin(checkpoint_manifest)
            for row in json.loads(checkpoint_manifest.read_text()):
                path = Path(row['path']); head = row['header']
                if path.parent != WORK/case or head['step'] not in (60,120):
                    raise ValueError('Unexpected checkpoint')
                pin(path,row['sha256'])
                live = json.loads(subprocess.check_output([str(ROOT/'checkpoint_probe'),str(path)],
                                                          text=True,timeout=15))
                if live != head or head['valid']!=1 or head['version']!=8:
                    raise ValueError('Checkpoint header mismatch')
                cp = prefix(path,head['particle_offset'],head['count'])
                time,raw = tipsy(WORK/case/f"state.{head['step']:06d}")
                if time != head['time']:
                    raise ValueError('Checkpoint and output header times differ')
                matches = check_export(cp,raw,factor)
                report['checkpoint_states'].append(dict(case=case,path=str(path),header=head,
                    sha256=row['sha256'],float32_roundtrip_exact=matches,
                    independent_struct_spotchecks=3))
                checks[(case,head['step'])] = cp
        if len(checks) != 8:
            raise ValueError('Incomplete checkpoint population')
        for ca,cb in itertools.combinations(CASES,2):
            for step in (60,120):
                a,b = checks[(ca,step)],checks[(cb,step)]
                fields = {key:difference(a[key],b[key]) for key in ('mass','eps','pos','vel','u')}
                report['checkpoint_comparisons'].append(dict(first=ca,second=cb,step=step,
                                                             fields=fields))
        report['summary'] = dict(native_snapshots_located=len(report['snapshots']),
            native_checkpoints_decoded=len(report['checkpoint_states']),
            snapshot_pair_times=len(report['comparisons']),
            checkpoint_pair_times=len(report['checkpoint_comparisons']),
            failed_density_pair_times=sum(row['fields']['rho']['exceeding_components']>0
                                          for row in report['comparisons']),
            every_dense_membership_exact=all(row['dense_membership_exact'] for row in report['comparisons']))
        if report['summary']['failed_density_pair_times'] != 6:
            raise ValueError('Mismatch with preserved failed density criterion')
        for path,h in report['pins'].items():
            checked_hash(path,h)
        report['status'] = 'read_only_divergence_review_complete_scientific_hold_unchanged'
        serialized = json.dumps(report,indent=2,allow_nan=False).encode()
        if len(serialized) > 64*1024**2:
            raise ValueError('Read-only artifact budget exceeded')
        write_new(OUT/'report.json',report)
        print(json.dumps(dict(status=report['status'],**report['summary']),indent=2))
    except Exception as exc:
        report.update(status='read_only_review_failed',error=repr(exc))
        write_new(OUT/'partial_report.json',report)
        raise


if __name__ == '__main__':
    main()
