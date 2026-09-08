"""Read-only native-file compression probe; writes only a new small report.

Scope: two already closed current L5 snapshots and two retained L4 terminal
snapshots. No simulations, rewrites, deletions, repacking or archive replacement.
Test plan: compress all file bytes with standard gzip levels 1 and 6, stream
decompress, require exact byte comparison, complete gzip stream and stable source
stat. Inspect HDF5 datasets read-only. Ratios do not certify whole-run savings,
native restart behavior or a production archiving workflow.
"""
import hashlib
import json
import time
import zlib
from pathlib import Path

import h5py

ROOT = Path('/mnt/c/Users/kaanb/CloudCrushing/storage_inventory_20260909')
CURRENT = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/enzo_L5_velocity_pair_v1/full/sharp13')
OLD = Path('/home/kaan/sensitivity_20260907/enzo/runs_v2')
SAMPLES = [
    ('L5_initial', CURRENT / 'DD0000'),
    ('L5_early_tcc_0.25', CURRENT / 'DD0005'),
    ('L4_sharp_terminal', OLD / 'L4_chi100_sharp13/DD0101'),
    ('L4_historical_terminal', OLD / 'L4_chi100_tanh13/DD0101'),
]


def signature(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def inspect_hdf(path):
    fields = []
    if not ('.cpu' in path.name or path.name.endswith('.hdf')):
        return fields
    with h5py.File(path, 'r') as h:
        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                fields.append(dict(name=name, shape=obj.shape, dtype=str(obj.dtype),
                    logical_bytes=obj.nbytes, stored_bytes=obj.id.get_storage_size(),
                    compression=obj.compression, shuffle=obj.shuffle))
        h.visititems(visit)
    return fields


def gzip_check(path, level):
    before = signature(path)
    encoder = zlib.compressobj(level, zlib.DEFLATED, 31)
    decoder = zlib.decompressobj(31)
    digest = hashlib.sha256()
    compressed_bytes = 0
    # SYNC_FLUSH at 8 MiB boundaries bounds the verification memory. This adds
    # slight overhead relative to an uninterrupted whole-file gzip stream.
    start = time.perf_counter()
    with path.open('rb') as source:
        while block := source.read(8 * 1024**2):
            digest.update(block)
            packed = encoder.compress(block) + encoder.flush(zlib.Z_SYNC_FLUSH)
            compressed_bytes += len(packed)
            restored = decoder.decompress(packed)
            if restored != block:
                raise ValueError(f'Byte mismatch: {path}, gzip{level}')
        packed = encoder.flush(zlib.Z_FINISH)
        compressed_bytes += len(packed)
        if decoder.decompress(packed) + decoder.flush() != b'' or not decoder.eof:
            raise ValueError('Incomplete gzip stream')
    if signature(path) != before:
        raise ValueError(f'Source changed during probe: {path}')
    return dict(gzip_level=level, bytes=compressed_bytes,
        seconds_compress_decompress_read=time.perf_counter()-start,
        byte_exact=True, source_sha256=digest.hexdigest())


def main():
    output = ROOT / ('compression_probe_' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')
    if output.exists():
        raise FileExistsError(output)
    report = dict(scope='read-only compression feasibility, not applied', samples=[],
        limitations=['Four snapshots only; L5 sample is early and L4 terminal is lower resolution.',
          'Wall times include read, compression and round-trip verification under live solver load.',
          'Whole-file gzip archives need extraction before native readers/restarts; not certified here.',
          'No research file changed or deleted. Conservative live admission budget unchanged.'])
    for label, folder in SAMPLES:
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        files = sorted(p for p in folder.iterdir() if p.is_file())
        if not files or any(p.is_symlink() for p in files):
            raise ValueError('Missing files or symlink')
        sample = dict(label=label, path=str(folder), files=[], original_bytes=0,
            gzip1_bytes=0, gzip6_bytes=0)
        for path in files:
            before = signature(path)
            fields = inspect_hdf(path)
            probes = [gzip_check(path, level) for level in (1, 6)]
            if probes[0]['source_sha256'] != probes[1]['source_sha256'] or signature(path) != before:
                raise ValueError(f'Source changed: {path}')
            sample['files'].append(dict(name=path.name, bytes=before[2], fields=fields, probes=probes))
            sample['original_bytes'] += before[2]
            for p in probes:
                sample[f"gzip{p['gzip_level']}_bytes"] += p['bytes']
        report['samples'].append(sample)
        print(json.dumps({k:v for k,v in sample.items() if k != 'files'}), flush=True)
    with output.open('x') as target:
        json.dump(report, target, indent=2)
    print(json.dumps(dict(report=str(output), all_bytes_roundtrip_exact=True)), flush=True)


if __name__ == '__main__':
    main()
