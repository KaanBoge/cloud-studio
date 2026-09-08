"""Read retained MFV restart prefixes using the exact executable's DWARF ABI.

No solver execution, source edits, floor changes, output replacement or promotion.
The RNG/tree tail is explicitly NOT parsed or certified for restart execution.
Only final states can be checked against the retained terminal restart generation.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

import h5py
import numpy as np

ROOT = Path('/home/kaan/sensitivity_20260907/gizmo')
EXPECTED_BINARY = 'b7634f844d98ceef246d66e2243827f0c5774c9997b92bd8ffeedfdf940eed91'
FIELDS = {
    'global_data_all_processes': ['Time', 'TimeMax', 'TotNumPart', 'TotN_gas',
        'MinEgySpec', 'cf_a3inv', 'BoxSize', 'ComovingIntegrationOn'],
    'particle_data': ['Type', 'ID', 'ID_child_number', 'ID_generation', 'Pos', 'Mass', 'Vel'],
    'gas_cell_data': ['Density', 'MassTrue', 'ParticleVel', 'Pressure',
        'InternalEnergy', 'InternalEnergyPred', 'DtInternalEnergy'],
}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def number(text):
    check(bool(re.fullmatch(r'(?:0x[0-9a-fA-F]+|[0-9]+)', text)),
          'Unsupported nonconstant DWARF integer: ' + text)
    return int(text, 16 if text.startswith('0x') else 10)


def name_of(die):
    return die['attrs'].get('name', '').rsplit('): ', 1)[-1]


def parse_dwarf(text):
    """Parse readelf info DIE hierarchy; fail on unsupported selected types later."""
    dies, stack, current = {}, {}, None
    for line in text.splitlines():
        m = re.match(r'\s*<(\d+)><([0-9a-f]+)>: Abbrev Number: (\d+)(?: \((DW_TAG_\w+)\))?', line)
        if m:
            depth, offset, abbrev = int(m[1]), int(m[2], 16), int(m[3])
            stack = {k: v for k, v in stack.items() if k < depth}
            current = None
            if not abbrev:
                continue
            check(offset not in dies, 'Duplicate DIE offset')
            current = dict(tag=m[4], attrs={}, children=[], offset=offset)
            dies[offset] = current
            if depth - 1 in stack:
                stack[depth - 1]['children'].append(offset)
            stack[depth] = current
        elif current is not None:
            m = re.match(r'\s*<[0-9a-f]+>\s+DW_AT_(\w+)\s*:\s*(.*)', line)
            if m:
                current['attrs'][m[1]] = m[2].strip()
    check(bool(dies), 'No DWARF DIEs')
    return dies


def type_ref(die):
    raw = die['attrs']['type']
    check(bool(re.fullmatch(r'<0x[0-9a-f]+>', raw)), 'Unsupported DWARF type reference')
    return int(raw[3:-1], 16)


def dtype_for(dies, offset, seen=()):
    check(offset not in seen, 'Recursive DWARF type')
    d = dies[offset]
    if d['tag'] in ('DW_TAG_typedef', 'DW_TAG_const_type', 'DW_TAG_volatile_type'):
        return dtype_for(dies, type_ref(d), seen + (offset,))
    if d['tag'] == 'DW_TAG_base_type':
        encoding = d['attrs']['encoding']
        code = number(encoding.split()[0])
        kind = {4: 'f', 5: 'i', 6: 'i', 7: 'u', 8: 'u'}.get(code)
        check(kind is not None, 'Unsupported DWARF base encoding')
        return np.dtype('<' + kind + str(number(d['attrs']['byte_size'])))
    if d['tag'] == 'DW_TAG_array_type':
        base = dtype_for(dies, type_ref(d), seen + (offset,))
        shape = []
        for child in d['children']:
            sub = dies[child]
            check(sub['tag'] == 'DW_TAG_subrange_type', 'Unsupported array child')
            a = sub['attrs']
            check(number(a.get('lower_bound', '0')) == 0, 'Nonzero array lower bound')
            size = number(a['count']) if 'count' in a else number(a['upper_bound']) + 1
            check(size > 0, 'Invalid array count')
            shape.append(size)
        check(bool(shape), 'Missing array shape')
        return np.dtype((base, tuple(shape)))
    raise ValueError('Unsupported selected type ' + d['tag'])


def layouts(dies, requests=FIELDS):
    result, evidence = {}, {}
    for struct_name, wanted in requests.items():
        definitions = []
        for d in dies.values():
            if d['tag'] != 'DW_TAG_structure_type' or name_of(d) != struct_name or 'byte_size' not in d['attrs']:
                continue
            members = {name_of(dies[x]): dies[x] for x in d['children']
                       if dies[x]['tag'] == 'DW_TAG_member'}
            check(all(w in members for w in wanted), 'Incomplete struct definition ' + struct_name)
            formats, offsets = [], []
            size = number(d['attrs']['byte_size'])
            for w in wanted:
                m = members[w]
                check(not any('bit' in k for k in m['attrs']), 'Unsupported bitfield')
                dt = dtype_for(dies, type_ref(m))
                pos = number(m['attrs']['data_member_location'])
                check(pos + dt.itemsize <= size, 'Member extends beyond struct')
                formats.append(dt)
                offsets.append(pos)
            dt = np.dtype(dict(names=wanted, formats=formats, offsets=offsets, itemsize=size))
            definitions.append((d['offset'], dt))
        check(bool(definitions), 'Missing compiled struct ' + struct_name)
        check(all(x[1] == definitions[0][1] for x in definitions), 'Inconsistent compiled layouts')
        dt = definitions[0][1]
        result[struct_name] = dt
        evidence[struct_name] = dict(itemsize=dt.itemsize, matching_definitions=len(definitions),
            die_offsets=[hex(x[0]) for x in definitions], fields={
                w: dict(offset=dt.fields[w][1], dtype=str(dt.fields[w][0]),
                        bytes=dt.fields[w][0].itemsize) for w in wanted})
    return result, evidence


def take(blob, position, dtype, count):
    dtype = np.dtype(dtype)
    check(0 <= count <= 65536, 'Invalid restart record count')
    end = position + count * dtype.itemsize
    check(0 <= position <= end <= len(blob), 'Truncated restart prefix')
    return np.frombuffer(blob, dtype=dtype, count=count, offset=position).copy(), end


def read_prefix(blob, types):
    all_data, pos = take(blob, 0, types['global_data_all_processes'], 1)
    npart, pos = take(blob, pos, '<i4', 1)
    check(0 < int(npart[0]) <= 65536, 'Invalid NumPart')
    p, pos = take(blob, pos, types['particle_data'], int(npart[0]))
    ngas, pos = take(blob, pos, '<i4', 1)
    check(int(ngas[0]) == len(p), 'Not the expected all-gas restart')
    s, pos = take(blob, pos, types['gas_cell_data'], int(ngas[0]))
    check(pos < len(blob), 'Missing expected RNG/tree restart tail')
    return all_data[0], p, s, pos


def energy_classes(predicted, exported):
    predicted = np.asarray(predicted, dtype=np.float64)
    exported = np.asarray(exported)
    check(predicted.shape == exported.shape, 'Energy shape mismatch')
    check(exported.dtype == np.dtype('float32'), 'Expected native float32 energy')
    check(np.all(np.isfinite(predicted)) and np.all(np.isfinite(exported)), 'Nonfinite energy')
    with np.errstate(under='ignore'):
        cast = predicted.astype(np.float32)
    # A separate diagnostic model, NOT a changed acceptance tolerance:
    # the native executable's startup constructor enables MXCSR FTZ/DAZ.
    bits = cast.view(np.uint32).copy()
    subnormal = ((bits & 0x7f800000) == 0) & ((bits & 0x007fffff) != 0)
    bits[subnormal] &= np.uint32(0x80000000)
    ftz = bits.view(np.float32)
    return dict(native_nonpositive=int(np.count_nonzero(predicted <= 0)),
        exported_zero=int(np.count_nonzero(exported == 0)),
        positive_underflows=int(np.count_nonzero((predicted > 0) & (cast == 0) & (exported == 0))),
        serialization_exact=bool(np.array_equal(cast, exported)),
        flushed_subnormals=int(np.count_nonzero(subnormal & (exported == 0))),
        flush_to_zero_serialization_exact=bool(np.array_equal(ftz, exported)))


def diagnose_case(root, law, types, old_audit):
    folder = root / 'runs' / f'L3_mfv_{law}'
    old = next(c for c in old_audit['cases'] if c['law'] == law)
    result = json.loads((folder / 'result.json').read_text())
    check(result['binary_sha256'] == EXPECTED_BINARY, 'Wrong case executable')
    inputs = {}
    for name, key in [('params.txt', 'input_sha256'), ('ics.hdf5', 'ic_sha256')]:
        digest = sha(folder / name)
        check(digest == result[key] == old[key], 'Input provenance mismatch')
        inputs[name] = digest
    final = folder / 'output' / 'snapshot_100.hdf5'
    final_sha = sha(final)
    check(final_sha == old['frames'][-1]['sha256'], 'Final native snapshot changed')
    parts, cells, headers, provenance = [], [], [], []
    for rank in range(8):
        path = folder / 'output' / 'restartfiles' / f'restart.{rank}'
        before = sha(path)
        a, p, s, consumed = read_prefix(path.read_bytes(), types)
        check(sha(path) == before, 'Restart changed while reading')
        parts.append(p); cells.append(s); headers.append(a)
        provenance.append(dict(path=str(path), sha256=before, bytes=path.stat().st_size,
                               parsed_prefix_bytes=consumed, unparsed_tail_bytes=path.stat().st_size-consumed,
                               particles=len(p)))
    a = headers[0]
    check(all(all(h[n] == a[n] for n in a.dtype.names) for h in headers), 'Rank headers differ')
    check(int(a['TotNumPart']) == int(a['TotN_gas']) == 65536, 'Wrong global counts')
    check(int(a['ComovingIntegrationOn']) == 0 and float(a['cf_a3inv']) == 1, 'Unexpected cosmological conversion')
    check(float(a['MinEgySpec']) == 0 and float(a['BoxSize']) == 10, 'Unexpected floor or domain')
    p, s = np.concatenate(parts), np.concatenate(cells)
    order = np.argsort(p['ID']); p, s = p[order], s[order]
    check(np.array_equal(p['ID'], np.arange(1, 65537)), 'Missing/duplicate IDs')
    check(np.all(p['Type'] == 0), 'Unexpected particle type')
    with h5py.File(final, 'r') as f:
        g = f['PartType0']; order = np.argsort(g['ParticleIDs'][:])
        arrays = {k: v[:][order] for k, v in g.items()}
        time = float(f['Header'].attrs['Time'])
    check(time == float(a['Time']) == float(a['TimeMax']), 'Final times do not match')
    coords = p['Pos'].copy()
    check(np.all(np.isfinite(coords)) and np.max(np.abs(coords)) < 1e6, 'Invalid positions')
    # Reproduce the actual native repeated-add/subtract periodic output convention.
    for axis, width in enumerate((20., 10., 10.)):
        while np.any(coords[:, axis] < 0):
            coords[coords[:, axis] < 0, axis] += width
        while np.any(coords[:, axis] >= width):
            coords[coords[:, axis] >= width, axis] -= width
    expected = {'ParticleIDs': p['ID'], 'ParticleChildIDsNumber': p['ID_child_number'],
        'ParticleIDGenerationNumber': p['ID_generation'], 'Coordinates': coords,
        'Masses': p['Mass'], 'Velocities': p['Vel'], 'Density': s['Density'],
        'ParticleVelocities': s['ParticleVel'],
        'InternalEnergy': np.maximum(a['MinEgySpec'], s['InternalEnergyPred'])}
    matches = {}
    for name, values in expected.items():
        with np.errstate(under='ignore'):
            same = np.array_equal(values.astype(arrays[name].dtype), arrays[name])
        matches[name] = bool(same)
        if name != 'InternalEnergy':
            check(same, 'Restart to native snapshot serialization differs: ' + name)
    classification = energy_classes(s['InternalEnergyPred'], arrays['InternalEnergy'])
    check(classification['flush_to_zero_serialization_exact'],
          'Energy differs even under independently observed native FTZ convention')
    statistics = {}
    for name in FIELDS['gas_cell_data']:
        x = s[name]
        check(np.all(np.isfinite(x)), 'Nonfinite restart gas field: ' + name)
        statistics[name] = dict(min=float(np.min(x)), max=float(np.max(x)),
                               nonpositive=int(np.count_nonzero(x <= 0)))
    bad = np.flatnonzero(arrays['InternalEnergy'] == 0)
    affected = [dict(id=int(p['ID'][i]), exported_energy=float(arrays['InternalEnergy'][i]),
        predicted_energy=float(s['InternalEnergyPred'][i]), conserved_energy=float(s['InternalEnergy'][i]),
        pressure=float(s['Pressure'][i]), density=float(s['Density'][i]), mass=float(p['Mass'][i]),
        energy_derivative=float(s['DtInternalEnergy'][i])) for i in bad]
    check(sha(final) == final_sha, 'Native snapshot changed during read')
    return dict(law=law, time_code=time, t_over_tcc=time/result['physics']['t_cc'],
        input_hashes=inputs, snapshot=dict(path=str(final), sha256=final_sha), restarts=provenance,
        all_header={n: a[n].item() for n in a.dtype.names}, serialized_fields_exact=matches,
        classification=classification, gas_statistics=statistics, affected_particles=affected,
        limitation='Only final snapshot100 has contemporaneous retained restart proof. '
                   'SmoothingLength is not decoded; RNG/tree tail is not parsed. No restart-executability certification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check(not args.output.exists(), 'Do not overwrite an existing diagnosis')
    binary = args.root / 'GIZMO_mfv_pair'
    check(sha(binary) == EXPECTED_BINARY, 'Wrong executable')
    elf = binary.read_bytes()[:16]
    check(elf[:6] == b'\x7fELF\x02\x01', 'Expected ELF64 little endian')
    dwarf = subprocess.check_output(['readelf', '--debug-dump=info', str(binary)], text=True)
    fast_math = subprocess.check_output(['objdump', '-d', '--disassemble=set_fast_math', str(binary)], text=True)
    init_array = subprocess.check_output(['readelf', '-x', '.init_array', str(binary)], text=True)
    relocations = subprocess.check_output(['readelf', '-r', str(binary)], text=True)
    # This diagnostic deliberately targets one exact binary, not an arbitrary ABI.
    check('<set_fast_math>:' in fast_math and 'or     $0x8040,%eax' in fast_math
          and 'ldmxcsr' in fast_math, 'Native FTZ/DAZ startup evidence absent')
    check('40400000 00000000' in init_array
          and re.search(r'000000061988\s+\S+\s+R_X86_64_RELATIVE\s+4040', relocations),
          'FTZ/DAZ constructor is not in expected native init array')
    types, evidence = layouts(parse_dwarf(dwarf))
    old_path = args.root / 'mfv_pair_audit.json'
    old = json.loads(old_path.read_text())
    cases = [diagnose_case(args.root, law, types, old) for law in ('sharp13', 'tanh13')]
    source_root = Path('/home/kaan/codes/gizmo')
    report = dict(status='diagnostic_only_mfv_not_certified',
        script_sha256=sha(__file__), binary_sha256=sha(binary), audit_sha256=sha(old_path),
        readelf_info_sha256=hashlib.sha256(dwarf.encode()).hexdigest(), compiled_layouts=evidence,
        native_ftz_daz_evidence=dict(disassembly=fast_math, init_array=init_array,
            relative_relocation=[x for x in relocations.splitlines() if '000000061988' in x],
            interpretation='Constructor at 0x4040 ORs MXCSR with 0x8040 (FTZ and DAZ). '
                           'Its .init_array entry has the matching relative relocation.'),
        current_source_hashes={n: sha(source_root / n) for n in
            ('restart.c', 'allvars.h', 'io.c', 'predict.c', 'kicks.c', 'run.c', 'GIZMO_config.h')},
        source_caveat='Current source is explanatory evidence; exact ABI comes from the pinned executable DWARF and native-field equality.',
        smallest_positive_float32=float(np.nextafter(np.float32(0), np.float32(1))),
        smallest_normal_float32=float(np.finfo(np.float32).tiny),
        cases=cases, decision='No rerun or larger MFV control authorized by this diagnostic; '
            'export underflow, if confirmed, does not establish physically valid thermal evolution. '
            'No raw snapshot is repaired, replaced, retimed or promoted.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(output=str(args.output), sha256=sha(args.output),
        cases=[dict(law=c['law'], classification=c['classification'],
                    affected_particles=c['affected_particles']) for c in cases]), indent=2))


if __name__ == '__main__':
    main()
