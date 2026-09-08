"""Independent struct.unpack review and retained native scalar histories.

Uses the published exact-binary DWARF offsets but not the NumPy restart decoder.
Checks every particle's ID, mass, density and predictor-energy serialization.
Reads all 202 original snapshot hashes; no native file is edited or regenerated.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

import h5py
import numpy as np


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def output_energy(value):
    bits = struct.unpack('<I', struct.pack('<f', value))[0]
    if not (bits & 0x7f800000) and bits & 0x007fffff:
        bits &= 0x80000000
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('/home/kaan/sensitivity_20260907/gizmo'))
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    check(not args.output.exists(), 'Refuse to overwrite review')
    root = args.root
    diagnosis_path = root / 'mfv_restart_diagnosis_v1.json'
    d = json.loads(diagnosis_path.read_text())
    old_path = root / 'mfv_pair_audit.json'
    old = json.loads(old_path.read_text())
    check(sha(old_path) == d['audit_sha256'], 'Original audit changed')
    check(sha(root / 'GIZMO_mfv_pair') == d['binary_sha256'], 'Binary changed')
    check(sha(root / 'diagnose_mfv_restart.py') == d['script_sha256'], 'Decoder changed')
    abi = d['compiled_layouts']
    all_size, psize, ssize = [abi[n]['itemsize'] for n in
        ('global_data_all_processes', 'particle_data', 'gas_cell_data')]
    check((all_size, psize, ssize) == (15864, 288, 384), 'Unexpected exact-binary ABI')
    pf = abi['particle_data']['fields']; sf = abi['gas_cell_data']['fields']
    cases = []
    for case in d['cases']:
        law = case['law']; oc = next(c for c in old['cases'] if c['law'] == law)
        old_restarts = {r['path']: r for r in oc['restart_files']}
        snapshot = Path(case['snapshot']['path'])
        check(sha(snapshot) == case['snapshot']['sha256'], 'Final snapshot changed')
        with h5py.File(snapshot, 'r') as f:
            g = f['PartType0']; ids = g['ParticleIDs'][:]
            row_for_id = {int(pid): i for i, pid in enumerate(ids)}
            native = {n: g[n][:] for n in ('Masses', 'Density', 'InternalEnergy')}
        seen, affected, restarts = set(), [], []
        for restart in case['restarts']:
            path = Path(restart['path']); digest = sha(path)
            check(digest == restart['sha256'] == old_restarts[str(path)]['sha256'], 'Restart provenance changed')
            blob = path.read_bytes()
            npart = struct.unpack_from('<i', blob, all_size)[0]
            gas_count_offset = all_size + 4 + npart * psize
            ngas = struct.unpack_from('<i', blob, gas_count_offset)[0]
            check(npart == ngas == restart['particles'], 'Independent counts differ')
            gas_start = gas_count_offset + 4
            for i in range(npart):
                po, so = all_size + 4 + i * psize, gas_start + i * ssize
                pid = struct.unpack_from('<I', blob, po + pf['ID']['offset'])[0]
                check(pid in row_for_id and pid not in seen, 'Independent ID mismatch')
                seen.add(pid); k = row_for_id[pid]
                vals = {n: struct.unpack_from('<d', blob, so + sf[n]['offset'])[0]
                    for n in ('Density', 'Pressure', 'InternalEnergy', 'InternalEnergyPred')}
                mass = struct.unpack_from('<d', blob, po + pf['Mass']['offset'])[0]
                check(all(np.isfinite(v) and v > 0 for v in vals.values()), 'Nonpositive internal state')
                check(struct.unpack('<f', struct.pack('<f', mass))[0] == native['Masses'][k], 'Independent mass mismatch')
                check(struct.unpack('<f', struct.pack('<f', vals['Density']))[0] == native['Density'][k], 'Independent rho mismatch')
                check(output_energy(vals['InternalEnergyPred']) == native['InternalEnergy'][k], 'Independent FTZ serialization mismatch')
                if native['InternalEnergy'][k] == 0:
                    old_affected = next(x for x in case['affected_particles'] if x['id'] == pid)
                    check(vals['InternalEnergyPred'] == old_affected['predicted_energy']
                        and vals['InternalEnergy'] == old_affected['conserved_energy'], 'Decoder disagreement')
                    affected.append(dict(id=pid, **vals))
            check(sha(path) == digest, 'Restart changed during review')
            restarts.append(dict(path=str(path), sha256=digest))
        check(len(seen) == 65536, 'Incomplete final coverage')
        target_ids = sorted(x['id'] for x in affected)
        histories = {str(pid): [] for pid in target_ids}
        frames = []
        for row in oc['frames']:
            path = Path(row['snapshot']); digest = sha(path)
            check(digest == row['sha256'], 'Original raw snapshot hash changed')
            with h5py.File(path, 'r') as f:
                g = f['PartType0']; ids = g['ParticleIDs'][:]
                time = float(f['Header'].attrs['Time'])
                check(time == row['time_code'], 'Native time changed')
                # Preserve raw scalar values and native header times, not new frames.
                for pid in target_ids:
                    indexes = np.flatnonzero(ids == pid)
                    check(len(indexes) == 1, 'History ID missing or duplicated')
                    i = int(indexes[0])
                    histories[str(pid)].append(dict(time_code=time, t_over_tcc=row['t_over_tcc'],
                        density=float(g['Density'][i]), internal_energy=float(g['InternalEnergy'][i]),
                        mass=float(g['Masses'][i])))
            frames.append(dict(path=str(path), sha256=digest, time_code=time))
        check(len(frames) == 101, 'Unexpected retained cadence')
        cases.append(dict(law=law, independently_checked_final_particles=len(seen),
            checked_native_snapshots=frames, checked_restarts=restarts,
            affected_internal_state=sorted(affected, key=lambda x: x['id']),
            terminal_zero_id_histories=histories))
    review = dict(status='independent_read_only_review_pass_mfv_still_not_certified',
        created_utc=datetime.now(timezone.utc).isoformat(), script_sha256=sha(__file__),
        diagnosis_sha256=sha(diagnosis_path), method='struct.unpack, independent of NumPy structured restart decoder; '
            'ABI offsets from exact binary DWARF; all original 202 raw-state hashes and 16 restart hashes rechecked.',
        cases=cases, limits='This checks the final restart serialization, not the physical correctness of '
            'vanishing thermal energy, not intermediate conserved state, and not full restart executability. '
            'MFV remains excluded from accepted scientific controls. No new simulation or deletion.')
    with args.output.open('x') as f:
        json.dump(review, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(output=str(args.output), sha256=sha(args.output),
        native_snapshots=sum(len(c['checked_native_snapshots']) for c in cases),
        restart_files=sum(len(c['checked_restarts']) for c in cases),
        final_particles=sum(c['independently_checked_final_particles'] for c in cases)), indent=2))


if __name__ == '__main__':
    main()
