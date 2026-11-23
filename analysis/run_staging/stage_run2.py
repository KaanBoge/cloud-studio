"""Stage Cloud Studio display products for ONE finished run with ALL of its saved states, in the layout of the
data contract of 2026-11-22 (one folder per run, every file of the run under one base address).

Extended copy of studio_pipeline/stage_run.py (that file is left unchanged). Read only on the run folders and on
the site checkouts. Writes only into --out (default D:\\CloudStudio-runs-staging\\<id>) and into the notes folder
(cache of the column density maps, so the films can be remade without reading the run again).

Output folder, exactly:
  edge.png, face.png                sprite sheets, one 128 px row per saved state (256 / 128 px wide)
  poster-edge.jpg, poster-face.jpg  the saved state closest to 2.5 t_cc, nothing drawn over it
  film-edge.mp4, film-face.mp4      1920 x 1080, H.264 yuv420p, 60 fps; film time runs linearly with simulation time
                                    (0.25 t_cc per second); every saved state is shown unblended on the frame of its
                                    true time, the frames in between cross fade between the two neighbouring states;
                                    text drawn after the cross fade
  3d/index.json, 3d/fNNN.bin        meshes in the site format (two surfaces at 0.15 and 0.6 of the initial cloud
                                    density, Gaussian 0.8 cells, marching cubes step 2), one per saved state
  entry.json, entry3d.json          catalog entries (no "base"; it is added when publishing)
  stage_report.json                 what was read, checks, sizes, wall time

Kinds:
  ramses  RAMSES output_NNNNN folders, reader lifted unchanged from analysis_20261122/n128_ramses/reduce.py
  flash   FLASH 4.8 and Flash-X checkpoint files (leaf blocks placed by bounding box; only "dens" is read)
  gadget4, arepo, gizmo   HDF5 PartType0; masses binned onto the level 5 lattice for display (as stage_run.py)
  --reuse <old stage folder> --reuse-id <old id>: take sprites, meshes and the per snapshot mass series of a run
  staged on 2026-11-22 by stage_run.py, after re reading three snapshots and showing that sprite rows and mesh
  files come out byte identical.

Phases: --phase read (read every snapshot once: maps, meshes, masses -> cache), --phase products (checks against
the reference reductions, sprites, posters, films, entries, report), --phase all.
"""
import argparse, ast, glob, gzip, hashlib, json, math, os, re, resource, shutil, struct, subprocess, sys, time, zlib
from pathlib import Path
import numpy as np, h5py
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
from PIL import Image, ImageDraw, ImageFont

REPO = Path('/mnt/d/CloudStudio-refresh-20261110')            # published site code (level with main), read only
A = Path('/mnt/d/CloudCrushing/run_simple/analysis_20261122')
NOTES = A / 'studio_impl' / 'stage_other'
STAGE_ROOT = Path('/mnt/d/CloudStudio-runs-staging')
FONTS = '/mnt/c/Windows/Fonts/'

ap = argparse.ArgumentParser()
ap.add_argument('--kind', required=True, choices=['ramses', 'flash', 'gadget4', 'arepo', 'gizmo'])
ap.add_argument('--run', required=True, help='folder holding the snapshots')
ap.add_argument('--id', required=True)
ap.add_argument('--label', required=True)
ap.add_argument('--code', required=True)
ap.add_argument('--group', default='')
ap.add_argument('--boundary', required=True)
ap.add_argument('--note', required=True)
ap.add_argument('--ref', required=True, choices=['ramses', 'flash', 'flashx', 'gadget4', 'arepo', 'mfm', 'mfv'])
ap.add_argument('--chi', type=float, default=100)
ap.add_argument('--mach', type=float, default=2)
ap.add_argument('--level', type=int, default=5)
ap.add_argument('--phase', default='all', choices=['read', 'products', 'all'])
ap.add_argument('--out', default='')
ap.add_argument('--cache', default='')
ap.add_argument('--limit', type=int, default=0, help='testing only: first N snapshots (products then skip the 101 state checks)')
ap.add_argument('--reuse', default='')
ap.add_argument('--reuse-id', default='')
ap.add_argument('--crf', type=int, default=18)
a = ap.parse_args()

OUT = Path(a.out) if a.out else STAGE_ROOT / a.id
CACHE = Path(a.cache) if a.cache else NOTES / 'cache' / (a.id + '.npz')
if not a.limit:
    assert OUT.resolve().parent == STAGE_ROOT.resolve() and OUT.name == a.id, 'a full run goes to the staging folder'
N = {3: 32, 4: 64, 5: 128, 6: 256}[a.level]
assert a.level == 5 or a.kind not in ('gadget4', 'arepo', 'gizmo'), 'particle runs are binned onto the level 5 lattice'
DX = 10 / N                                                    # cell size in cloud radii
CHI = a.chi
GAMMA = 5 / 3
VW = a.mach * math.sqrt(GAMMA)                                 # wind speed for rho_w = 1, P_w = 1
TCC = math.sqrt(CHI) / VW                                      # t_cc for R = 1
MESH_STEP = 4 if a.level == 6 else 2
PERIODIC_SMOOTH = a.kind in ('gadget4', 'arepo', 'gizmo')      # display smoothing wraps, as for the site's GIZMO runs


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lift(path, names):
    src = Path(path).read_text(encoding='utf-8'); out = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            out[node.name] = ast.get_source_segment(src, node)
    missing = set(names) - set(out)
    assert not missing, (path, missing)
    return out


# --- the site's own PNG writer and mesh encoder, lifted unchanged -------------------------------------------------
SITE_SRC = {'recent_gallery_export.py': sha(REPO / 'analysis/recent_gallery_export.py'),
            'recent_3d_export.py': sha(REPO / 'analysis/recent_3d_export.py'),
            'assets/recent/catalog.json': sha(REPO / 'assets/recent/catalog.json')}
ns = dict(np=np, DX=DX, struct=struct, gzip=gzip, zlib=zlib, gaussian_filter=gaussian_filter, marching_cubes=marching_cubes)
src = {**lift(REPO / 'analysis/recent_gallery_export.py', {'png'}), **lift(REPO / 'analysis/recent_3d_export.py', {'encode'})}
for code in src.values():
    exec(code, ns)
png = ns['png']
assert 'step_size=2' in src['encode']
ns0 = dict(ns); exec(src['encode'].replace('step_size=2', 'step_size=%d' % MESH_STEP), ns0); encode = ns0['encode']
ns1 = dict(ns); exec(src['encode'].replace('step_size=2', 'step_size=1'), ns1); encode_step1 = ns1['encode']
fallbacks = []


def safe_encode(rho, record=True, index=None):
    """Retry at full resolution when the stepped sampling finds no surface, then write an empty frame (the viewer
    accepts zero shells), so that no saved time is dropped. Every use is recorded in the report."""
    for k, enc in enumerate((encode, encode_step1)):
        try:
            out = enc(rho, CHI, PERIODIC_SMOOTH)
            if k and record: fallbacks.append(dict(index=index, action='full resolution retry'))
            return out
        except RuntimeError:
            continue
    if record: fallbacks.append(dict(index=index, action='empty frame'))
    return gzip.compress(struct.pack('<B', 0), compresslevel=6, mtime=0), 0, 0


LUT = np.array(json.loads((REPO / 'assets/recent/catalog.json').read_text())['colormap'])
assert LUT.shape == (256, 3)


def color(x):
    """Same mapping as recent_gallery_export.color: log column density 0.008 to 5 -> magma, rows flipped (y up)."""
    idx = np.floor(np.clip((np.log10(np.maximum(x, 1e-30)) - np.log10(.008)) / (np.log10(5) - np.log10(.008)), 0, 1) * 255).astype(int)
    return np.round(LUT[idx] * 255).astype('uint8')[::-1]


def to_sprite(col):
    if N == 128: return col
    if N < 128:
        f = 128 // N; return np.repeat(np.repeat(col, f, axis=0), f, axis=1)
    f = N // 128; h, w = col.shape
    return col.reshape(h // f, f, w // f, f).mean(axis=(1, 3))


# --- readers ---------------------------------------------------------------------------------------------------------
RAMSES_SRC = A / 'n128_ramses/reduce.py'
if a.kind == 'ramses':
    rns = dict(np=np, os=os, glob=glob, hashlib=hashlib, re=re)
    for code in lift(RAMSES_SRC, ['Records', 'read_file', 'read_output', 'read_info', 'list_outputs']).values():
        exec(code, rns)


def snapshot_list():
    run = Path(a.run)
    if a.kind == 'ramses':
        outs = rns['list_outputs'](str(run))                      # numbered 1..N without gaps, else it raises
        return [Path(o) for o in outs]
    if a.kind == 'flash':
        return [Path(p) for p in sorted(glob.glob(str(run / '*_hdf5_chk_[0-9][0-9][0-9][0-9]')))]
    if a.kind == 'gadget4' or a.kind == 'gizmo':
        return sorted(run.glob('snapshot_[0-9][0-9][0-9].hdf5'))
    return sorted(run.glob('snap_[0-9][0-9][0-9].hdf5'))


def scal(ds):
    out = {}
    for row in ds[...]:
        name = row[0].decode(errors='replace').strip(); val = row[1]
        if isinstance(val, bytes): val = val.decode(errors='replace').strip()
        elif isinstance(val, np.generic): val = val.item()
        out[name] = val
    return out


def read_ramses(folder):
    meta, f = rns['read_output'](str(folder), want_hash=False)   # checks that leaf cells tile the box exactly once
    assert meta['grid'] == [2 * N, N, N], meta['grid']
    assert abs(meta['cell_size'] - DX) < 1e-12, meta['cell_size']
    assert not any(x['all_zero'] for x in meta['files']), 'zero filled file in ' + str(folder)
    rho = np.ascontiguousarray(f['rho'].transpose(2, 1, 0))      # reader order [x, y, z] -> [z, y, x]
    del f
    files = [dict(name=x['name'], bytes=x['bytes']) for x in meta['files']]
    t = float(meta['time'])
    return dict(rho=rho, t_code=t, t_tcc=t / TCC, total=float(rho.sum()) * DX ** 3, dense=float(rho[rho > CHI / 3].sum()) * DX ** 3,
                files=files, extra=dict(ncpu=meta['ncpu'], nstep_coarse=meta['nstep_coarse']))


def read_flash(fn):
    with h5py.File(fn, 'r') as f:
        rs, isc = scal(f['real scalars']), scal(f['integer scalars'])
        rp = scal(f['real runtime parameters'])
        nxb, nyb, nzb = int(isc['nxb']), int(isc['nyb']), int(isc['nzb'])
        ntype = f['node type'][...]; rlev = f['refine level'][...]
        bb = f['bounding box'][...].astype(np.float64)
        nb = int(ntype.shape[0]); leaf = np.nonzero(ntype == 1)[0]
        assert np.unique(rlev[leaf]).size == 1, 'leaf blocks on more than one level'
        dom_lo = np.array([rp['xmin'], rp['ymin'], rp['zmin']], dtype=np.float64)
        dom_hi = np.array([rp['xmax'], rp['ymax'], rp['zmax']], dtype=np.float64)
        R = float(rp['sim_rcloud']); rho_w = float(rp['sim_rhoambient']); vw = float(rp['sim_windvel'])
        chi = float(rp['sim_rhocloud']) / rho_w
        assert chi == CHI, chi
        assert abs(vw / (a.mach * math.sqrt(float(rp['gamma']) * float(rp['sim_pambient']) / rho_w)) - 1) < 1e-12, vw
        ctr = np.array([rp['sim_xctr'], rp['sim_yctr'], rp['sim_zctr']], dtype=np.float64)
        assert np.allclose((ctr - dom_lo) / R, [3, 5, 5], atol=1e-9) and np.allclose((dom_hi - dom_lo) / R, [20, 10, 10], atol=1e-9), (ctr, dom_lo, dom_hi, R)
        lo, hi = bb[leaf, :, 0], bb[leaf, :, 1]
        bsize = hi - lo
        assert np.allclose(bsize, bsize[0], rtol=1e-5, atol=0), 'leaf blocks of different size'
        nblk = np.rint((dom_hi - dom_lo) / bsize[0]).astype(int)
        n1, n2, n3 = int(nblk[0] * nxb), int(nblk[1] * nyb), int(nblk[2] * nzb)
        assert (n1, n2, n3) == (2 * N, N, N), (n1, n2, n3)
        d = (dom_hi - dom_lo) / np.array([n1, n2, n3])
        assert np.allclose(d / R, DX, rtol=1e-12), d
        pos = (lo - dom_lo) / d
        i0 = np.rint(pos).astype(int)
        assert float(np.abs(pos - i0).max()) < 1e-2, 'leaf blocks off the cell lattice'
        filled = np.zeros((n3, n2, n1), dtype=np.int16)
        for (i, j, k) in i0:
            filled[k:k + nzb, j:j + nyb, i:i + nxb] += 1
        assert int(filled.min()) == 1 and int(filled.max()) == 1, 'leaf blocks overlap or leave holes'
        del filled
        src_ = f['dens'][...]
        assert src_.shape == (nb, nzb, nyb, nxb), src_.shape
        rho = np.empty((n3, n2, n1), dtype=np.float64)
        for b, (i, j, k) in zip(leaf, i0):
            rho[k:k + nzb, j:j + nyb, i:i + nxb] = src_[b]
        del src_
        t = float(rs['time'])
    dV = float(d[0] * d[1] * d[2]); munit = rho_w * R ** 3
    tcc = math.sqrt(chi) * R / vw
    assert abs(tcc / R - TCC) < 1e-12 * TCC
    total = float(rho.sum()) * dV / munit; dense = float(rho[rho > CHI / 3 * rho_w].sum()) * dV / munit
    if rho_w != 1.0: rho = rho / rho_w
    return dict(rho=rho, t_code=t, t_tcc=t / tcc, total=total, dense=dense, files=[dict(name=Path(fn).name, bytes=os.path.getsize(fn))],
                extra=dict(R_code=R, nstep=int(isc['nstep']), n_leaf=int(leaf.size)))


def read_particles(p):
    with h5py.File(p, 'r') as h:
        g = h['PartType0']; t = float(h['Header'].attrs['Time'])
        pos = g['Coordinates'][:]; m = g['Masses'][:].astype('float64'); d = g['Density'][:]
    assert np.isfinite(pos).all() and np.isfinite(m).all() and m.min() > 0
    assert pos.min() >= 0 and pos[:, 0].max() <= 20 and pos[:, 1:].max() <= 10, 'particle outside the 20 x 10 x 10 box'
    ix = np.floor(pos.astype('float64') / DX).astype(np.int64); ix %= np.array([2 * N, N, N])
    flat = (ix[:, 2] * N + ix[:, 1]) * (2 * N) + ix[:, 0]
    grid = np.bincount(flat, weights=m, minlength=2 * N ** 3).reshape(N, N, 2 * N) / DX ** 3
    total = float(m.sum()); dense = float(m[d > CHI / 3].sum())
    assert abs(grid.sum() * DX ** 3 - total) <= 1e-9 * total
    return dict(rho=grid, t_code=t, t_tcc=t / TCC, total=total, dense=dense, files=[dict(name=Path(p).name, bytes=os.path.getsize(p))],
                extra=dict(n=int(len(m)), empty_lattice_cells=int((grid == 0).sum())))


READ = dict(ramses=read_ramses, flash=read_flash, gadget4=read_particles, arepo=read_particles, gizmo=read_particles)[a.kind]


def maps(rho):
    col_e = rho.sum(axis=0) * DX / CHI; col_f = rho.sum(axis=2) * DX / CHI       # [y, x] edge-on, [z, y] face-on
    return col_e, col_f


# --- references ------------------------------------------------------------------------------------------------------
def load_ref(kind):
    if kind == 'ramses':
        p = A / 'n128_ramses/series.json'
        s = next(x for x in json.loads(p.read_text())['series'] if int(x['level']) == 5)
        r = dict(t_code=s['time_code'], t_tcc=s['times_tcc'], total=s['total_mass'], dense=s['M_d'], fd=s['f_d'])
    elif kind in ('flash', 'flashx'):
        p = A / 'n128_flash/series.json'
        s = next(x for x in json.loads(p.read_text())['runs'] if x['code'] == kind and int(x['level']) == 5)
        r = dict(t_code=s['time_code'], t_tcc=s['times_tcc'], total=s['total_mass'], dense=s['M_d'], fd=s['f_d'])
    elif kind == 'gadget4':
        p = A / 'gadget4/series.json'
        s = json.loads(p.read_text())['levels']['L5']
        r = dict(t_code=s['time'], t_tcc=s['time_tcc'], total=s['total_mass'], dense=s['M_d'], fd=s['f_d'])
    elif kind == 'arepo':
        p = A / 'arepo/series.json'
        s = json.loads(p.read_text())['runs']['L5']
        r = dict(t_code=s['time'], t_tcc=s['t_over_tcc'], total=s['M_total'], dense=s['M_dense'], fd=s['f_dense'])
    else:
        p = Path('/mnt/d/CloudCrushing/meeting_20261010_v1/paper_revision_20261122_v4/plot_series.json')
        s = next(x for x in json.loads(p.read_text()) if x['code'] == kind and int(x['level']) == 5)
        r = dict(t_tcc=s['times'], fd=s['dense'])
    r = {k: [float(v) for v in vals] for k, vals in r.items()}
    return r, dict(file=str(p), sha256=sha(p))


def compare(mine, ref):
    """Largest differences per quantity; relative for masses and code times, absolute for t/t_cc and f_d."""
    out = {}
    for k in ref:
        if k not in mine: continue
        x = np.array(mine[k], dtype=np.float64); y = np.array(ref[k], dtype=np.float64)
        if len(x) != len(y):
            out[k] = dict(error='length %d against %d' % (len(x), len(y))); continue
        ad = np.abs(x - y)
        rel = ad / np.maximum(np.abs(y), 1e-300)
        out[k] = dict(n=int(len(x)), exact=bool((x == y).all()), n_exact=int((x == y).sum()), max_abs=float(ad.max()),
                      max_rel=float(rel[np.abs(y) > 0].max()) if (np.abs(y) > 0).any() else 0.0, at_index=int(ad.argmax()))
    return out


TOL = dict(t_code=('max_rel', 1e-14), t_tcc=('max_abs', 1e-12), total=('max_rel', 1e-10), dense=('max_rel', 1e-10), fd=('max_abs', 1e-10))


# --- phase 1: read every snapshot once -------------------------------------------------------------------------------
def phase_read():
    t0 = time.perf_counter()
    files = snapshot_list()
    if a.limit: files = files[:a.limit]
    assert files, 'no snapshots found'
    mesh_dir = OUT / '3d'; mesh_dir.mkdir(parents=True, exist_ok=True)
    rows = dict(col_e=[], col_f=[], rgb_e=[], rgb_f=[], t_code=[], t_tcc=[], total=[], dense=[], tris=[], shells=[], mesh_bytes=[], mesh_sha=[])
    read_log = []
    for i, f in enumerate(files):
        s = time.perf_counter(); r = READ(f); dt_read = time.perf_counter() - s
        rho = r['rho']
        assert rho.shape == (N, N, 2 * N) and np.isfinite(rho).all() and rho.min() >= 0, (rho.shape, float(rho.min()))
        if a.kind in ('ramses', 'flash'): assert rho.min() > 0
        ce, cf = maps(rho)
        assert abs(ce.sum() * DX ** 2 * CHI - r['total']) <= 1e-10 * r['total'] and abs(cf.sum() * DX ** 2 * CHI - r['total']) <= 1e-10 * r['total']
        s = time.perf_counter(); blob, ntri, nsh = safe_encode(rho, index=i); dt_mesh = time.perf_counter() - s
        p = mesh_dir / ('f%03d.bin' % i); p.write_bytes(blob)
        rows['col_e'].append(ce.astype(np.float32)); rows['col_f'].append(cf.astype(np.float32))
        rows['rgb_e'].append(color(to_sprite(ce))); rows['rgb_f'].append(color(to_sprite(cf)))
        for k in ('t_code', 't_tcc', 'total', 'dense'): rows[k].append(r[k])
        rows['tris'].append(ntri); rows['shells'].append(nsh); rows['mesh_bytes'].append(len(blob)); rows['mesh_sha'].append(hashlib.sha256(blob).hexdigest())
        read_log.append(dict(index=i, path=str(f), files=r['files'], t_code=r['t_code'], t_tcc=r['t_tcc'], read_s=round(dt_read, 2), mesh_s=round(dt_mesh, 2), **r['extra']))
        del rho, r
        if i % 10 == 0 or i == len(files) - 1:
            print('%s %3d/%d t=%.4f t_cc dense=%.4f read %.1f s mesh %.1f s elapsed %.0f s' % (a.id, i + 1, len(files), rows['t_tcc'][-1], rows['dense'][-1] / rows['dense'][0], dt_read, dt_mesh, time.perf_counter() - t0), flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_name(CACHE.stem + '.tmp.npz')
    np.savez(tmp, col_e=np.stack(rows['col_e']), col_f=np.stack(rows['col_f']), rgb_e=np.stack(rows['rgb_e']), rgb_f=np.stack(rows['rgb_f']),
             t_code=np.array(rows['t_code']), t_tcc=np.array(rows['t_tcc']), total=np.array(rows['total']), dense=np.array(rows['dense']),
             tris=np.array(rows['tris']), shells=np.array(rows['shells']))
    os.replace(tmp, CACHE)
    meta = dict(source='read', run=a.run, kind=a.kind, n_snapshots=len(files), read_log=read_log, mesh_bytes=rows['mesh_bytes'], mesh_sha256=rows['mesh_sha'],
                encoder_fallbacks=fallbacks, read_wall_seconds=round(time.perf_counter() - t0, 1),
                read_seconds_total=round(sum(x['read_s'] for x in read_log), 1), mesh_seconds_total=round(sum(x['mesh_s'] for x in read_log), 1),
                max_rss_MB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024), site_sources_sha256=SITE_SRC,
                ramses_reader_sha256=sha(RAMSES_SRC) if a.kind == 'ramses' else None)
    CACHE.with_suffix('.json').write_text(json.dumps(meta, indent=1))
    print('read done', a.id, len(files), 'snapshots', meta['read_wall_seconds'], 's', flush=True)


# --- reuse of a run staged on 2026-11-22 -----------------------------------------------------------------------------
def phase_reuse():
    t0 = time.perf_counter()
    old = Path(a.reuse); oid = a.reuse_id
    orep = json.loads((old / 'stage_report.json').read_text())
    assert orep['args']['run'].rstrip('/') == str(Path(a.run).parent).rstrip('/') or orep['args']['run'].rstrip('/') == a.run.rstrip('/'), (orep['args']['run'], a.run)
    ser = orep['series']
    se = np.asarray(Image.open(old / 'recent' / (oid + '-edge.png')).convert('RGB')); sf = np.asarray(Image.open(old / 'recent' / (oid + '-face.png')).convert('RGB'))
    n = len(ser['t_over_tcc'])
    assert se.shape == (128 * n, 256, 3) and sf.shape == (128 * n, 128, 3), (se.shape, sf.shape)
    rgb_e = se.reshape(n, 128, 256, 3); rgb_f = sf.reshape(n, 128, 128, 3)
    oidx = json.loads((old / 'recent3d' / ('new_' + oid) / 'index.json').read_text())
    assert oidx['frames'] == ['f%03d.bin' % i for i in range(n)] and oidx['times'] == ser['t_over_tcc']
    mesh_dir = OUT / '3d'; mesh_dir.mkdir(parents=True, exist_ok=True)
    mesh_bytes, mesh_sha = [], []
    for i in range(n):
        src_ = old / 'recent3d' / ('new_' + oid) / ('f%03d.bin' % i); b = src_.read_bytes()
        dst = mesh_dir / ('f%03d.bin' % i); dst.write_bytes(b)
        assert dst.read_bytes() == b
        mesh_bytes.append(len(b)); mesh_sha.append(hashlib.sha256(b).hexdigest())
    # proof: re read three snapshots with this script's reader and compare byte for byte
    files = snapshot_list(); assert len(files) == n
    proof = []
    for i in (0, n // 2, n - 1):
        r = READ(files[i]); ce, cf = maps(r['rho'])
        e_rows = color(to_sprite(ce)); f_rows = color(to_sprite(cf))
        blob, ntri, nsh = safe_encode(r['rho'], record=False)
        pr = dict(index=i, file=files[i].name, t_tcc=r['t_tcc'], edge_row_identical=bool(np.array_equal(e_rows, rgb_e[i])),
                  face_row_identical=bool(np.array_equal(f_rows, rgb_f[i])), mesh_identical=(blob == (mesh_dir / ('f%03d.bin' % i)).read_bytes()),
                  tris=ntri, tris_old=oidx['tris'][i], time_identical=(r['t_tcc'] == ser['t_over_tcc'][i]),
                  total_identical=(r['total'] == ser['total_mass'][i]), dense_identical=(r['dense'] == ser['dense_mass'][i]),
                  edge_pixels_differing=int((e_rows != rgb_e[i]).any(axis=-1).sum()), face_pixels_differing=int((f_rows != rgb_f[i]).any(axis=-1).sum()))
        proof.append(pr); print('proof', pr, flush=True)
        del r
    ok = all(p['edge_row_identical'] and p['face_row_identical'] and p['mesh_identical'] and p['time_identical'] and p['total_identical'] and p['dense_identical'] for p in proof)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_name(CACHE.stem + '.tmp.npz')
    np.savez(tmp, rgb_e=rgb_e, rgb_f=rgb_f, t_tcc=np.array(ser['t_over_tcc']), total=np.array(ser['total_mass']), dense=np.array(ser['dense_mass']),
             tris=np.array(oidx['tris']), shells=np.array(oidx['shell_counts']))
    os.replace(tmp, CACHE)
    meta = dict(source='reuse', run=a.run, kind=a.kind, n_snapshots=n, reused_from=str(old), reused_id=oid,
                reused_files_sha256={'edge': sha(old / 'recent' / (oid + '-edge.png')), 'face': sha(old / 'recent' / (oid + '-face.png')),
                                     'stage_report': sha(old / 'stage_report.json'), 'index': sha(old / 'recent3d' / ('new_' + oid) / 'index.json')},
                old_stage_args=orep['args'], old_encoder_fallbacks=orep.get('encoder_fallbacks', 'not recorded (first version stops on a failure)'),
                proof=proof, proof_all_identical=ok, mesh_bytes=mesh_bytes, mesh_sha256=mesh_sha,
                read_log=[dict(index=i, path=str(p), files=[dict(name=p.name, bytes=os.path.getsize(p))], t_tcc=ser['t_over_tcc'][i],
                               read_now=i in [q['index'] for q in proof]) for i, p in enumerate(files)],
                encoder_fallbacks=[], read_wall_seconds=round(time.perf_counter() - t0, 1), site_sources_sha256=SITE_SRC,
                max_rss_MB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))
    CACHE.with_suffix('.json').write_text(json.dumps(meta, indent=1))
    assert ok, 'the earlier staging does not reproduce: restage this run'
    print('reuse done', a.id, n, 'states, proof identical', flush=True)


# --- phase 2: products -----------------------------------------------------------------------------------------------
BG = (11, 16, 23)            # site background #0b1017
INK = (236, 241, 245)        # --text
MUTED = (155, 170, 185)      # --muted
ACCENT = (229, 186, 131)     # --accent
LINE = (38, 50, 63)          # --line
W, H = 1920, 1080
FPS = 60
FRAMES_PER_TCC = 240         # 0.25 t_cc per second of film
HOLD_START, HOLD_END = 30, 60


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def film_layout(view):
    size = (1536, 768) if view == 'edge' else (768, 768)
    return size, ((W - size[0]) // 2, 156)


def background(view, title):
    size, (x0, y0) = film_layout(view)
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    L, Rt = 192, 1728
    d.text((L, 92), title, font=font('seguisb.ttf', 42), fill=INK, anchor='ls')
    d.text((L, 132), 'Mach 2 \u00b7 ' + ('Edge-on, wind from left to right' if view == 'edge' else 'Face-on, looking along the wind axis'),
           font=font('segoeui.ttf', 24), fill=MUTED, anchor='ls')
    d.rectangle((x0 - 1, y0 - 1, x0 + size[0], y0 + size[1]), outline=LINE, width=1)
    # colour bar with its unit
    d.text((L, 968), 'Column density of all gas, in units of initial cloud density \u00d7 cloud radius, log scale',
           font=font('segoeui.ttf', 22), fill=MUTED, anchor='ls')
    bw, by0, by1 = 768, 984, 1000
    lo, hi = math.log10(.008), math.log10(5)
    for k in range(bw):
        c = LUT[min(255, int(k / bw * 256))]
        d.line((L + k, by0, L + k, by1 - 1), fill=tuple(int(round(v * 255)) for v in c))
    def xat(v): return L + (math.log10(v) - lo) / (hi - lo) * bw
    small = font('segoeui.ttf', 20)
    for v, txt, anchor in ((.008, '0.008', 'ls'), (.1, '0.1', 'ms'), (1, '1', 'ms'), (5, '5', 'rs')):
        x = xat(v); xi = int(round(x)) if anchor == 'ms' else (L if anchor == 'ls' else L + bw - 1)
        d.line((xi, by1, xi, by1 + 6), fill=MUTED)
        d.text((x if anchor == 'ms' else (L if anchor == 'ls' else L + bw), 1028), txt, font=small, fill=MUTED, anchor=anchor)
    d.text((Rt, 1028), 'Cloud Studio', font=font('georgiai.ttf', 28), fill=ACCENT, anchor='rs')
    return np.asarray(img).copy()


class Readout:
    """'t = 1.25 t' with a subscript 'cc', right aligned at x = 1728, baseline 92; Segoe UI Bold digits are tabular."""
    def __init__(self):
        self.big = font('segoeuib.ttf', 44); self.sub = font('segoeuib.ttf', 27)
        w_main = self.big.getlength('t = 0.00 t'); w_sub = self.sub.getlength('cc')
        self.w = int(math.ceil(w_main + 2 + w_sub)) + 4; self.h = 70
        self.x = 1728 - self.w; self.y = 92 - 52
        self.cache = {}
        assert len({self.big.getlength(c) for c in '0123456789'}) == 1, 'digits are not tabular'

    def patch(self, s):
        if s not in self.cache:
            img = Image.new('RGB', (self.w, self.h), BG); d = ImageDraw.Draw(img)
            main = 't = %s t' % s
            w_main = self.big.getlength(main); w_sub = self.sub.getlength('cc')
            x = self.w - 2 - w_sub - 2 - w_main
            d.text((x, 52), main, font=self.big, fill=ACCENT, anchor='ls')
            d.text((x + w_main + 2, 62), 'cc', font=self.sub, fill=ACCENT, anchor='ls')
            self.cache[s] = np.asarray(img).copy()
        return self.cache[s]


def schedule(times):
    f = [int(round(t * FRAMES_PER_TCC)) for t in times]
    assert f[0] == 0 and all(b > c for b, c in zip(f[1:], f[:-1])), 'two saved states fall on one film frame'
    out = [(0, 0.0, times[0])] * HOLD_START
    for i in range(len(times) - 1):
        for k in range(f[i], f[i + 1]):
            w = (k - f[i]) / (f[i + 1] - f[i])
            out.append((i, w, times[i] + w * (times[i + 1] - times[i])))
    out += [(len(times) - 1, 0.0, times[-1])] * (1 + HOLD_END)
    return out, f


def ffprobe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_read_packets,color_space,color_transfer,color_primaries,color_range:format=duration,size',
                        '-of', 'json', str(p)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    return dict(codec=s['codec_name'], profile=s.get('profile'), pix_fmt=s['pix_fmt'], width=s['width'], height=s['height'], r_frame_rate=s['r_frame_rate'],
                avg_frame_rate=s['avg_frame_rate'], frames=int(s['nb_read_packets']), color_space=s.get('color_space'), color_range=s.get('color_range'),
                duration=float(j['format']['duration']), bytes=int(j['format']['size']))


def make_film(rgb, times, view, title, dest, crf):
    size, (x0, y0) = film_layout(view)
    big = np.stack([np.asarray(Image.fromarray(r).resize(size, Image.Resampling.LANCZOS)) for r in rgb])
    bg = background(view, title); ro = Readout()
    sched, fidx = schedule(times)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', 'pipe:0', '-an',
           '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-profile:v', 'high', '-g', '60', '-threads', '4',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
           '-movflags', '+faststart', str(dest)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for (i, w, t) in sched:
            pic = big[i] if w == 0 else (big[i].astype(np.float32) * (1 - w) + big[i + 1].astype(np.float32) * w + .5).astype(np.uint8)
            fr = bg.copy(); fr[y0:y0 + size[1], x0:x0 + size[0]] = pic
            pt = ro.patch('%.2f' % t); fr[ro.y:ro.y + ro.h, ro.x:ro.x + ro.w] = pt
            p.stdin.write(fr.tobytes())
        p.stdin.close()
        assert p.wait() == 0, 'encoder failed'
    finally:
        if p.poll() is None: p.kill()
    return len(sched), fidx


def decode_mesh(b):
    """Parse one mesh file of the site format and check counts and positions."""
    raw = gzip.decompress(b); o = 0
    ns_ = raw[0]; o = 1; tri = 0; levels = []
    for _ in range(ns_):
        level, opac, r_, g_, b_, lx, ly, lz, hx, hy, hz, nv, nt = struct.unpack_from('<ff3f3f3fII', raw, o); o += struct.calcsize('<ff3f3f3fII')
        q = np.frombuffer(raw, dtype='<u2', count=3 * nv, offset=o); o += 6 * nv
        f = np.frombuffer(raw, dtype='<u4', count=3 * nt, offset=o); o += 12 * nt
        assert nv > 0 and nt > 0 and int(f.max()) < nv
        assert lx >= -3 - 1e-6 and ly >= -5 - 1e-6 and lz >= -5 - 1e-6 and hx <= 17 + 1e-6 and hy <= 5 + 1e-6 and hz <= 5 + 1e-6
        tri += nt; levels.append(round(level, 4))
    assert o == len(raw), 'trailing bytes'
    return ns_, tri, levels


def not_zero_filled(p):
    b = Path(p).read_bytes()
    return len(b) > 0 and b.count(0) != len(b)


def phase_products():
    t0 = time.perf_counter()
    meta = json.loads(CACHE.with_suffix('.json').read_text())
    z = np.load(CACHE)
    rgb_e, rgb_f = z['rgb_e'], z['rgb_f']
    times = [float(x) for x in z['t_tcc']]; total = [float(x) for x in z['total']]; dense = [float(x) for x in z['dense']]
    tris = [int(x) for x in z['tris']]; shells = [int(x) for x in z['shells']]
    n = len(times)
    checks = {}
    # times
    checks['times'] = dict(n=n, first=times[0], last=times[-1], strictly_increasing=all(b > c for b, c in zip(times[1:], times[:-1])),
                           min_step=min(b - c for b, c in zip(times[1:], times[:-1])), max_step=max(b - c for b, c in zip(times[1:], times[:-1])))
    assert times[0] == 0 and checks['times']['strictly_increasing']
    if not a.limit:
        assert n == 101 and abs(times[-1] - 5) < 0.01, checks['times']
    # reference reductions
    ref, ref_src = load_ref(a.ref)
    mine = dict(t_tcc=times, total=total, dense=dense, fd=[d / dense[0] for d in dense])
    if 't_code' in z.files: mine['t_code'] = [float(x) for x in z['t_code']]
    if a.limit: ref = {k: v[:n] for k, v in ref.items()}
    cmp_ = compare(mine, ref)
    verdict = {}
    for k, c in cmp_.items():
        what, tol = TOL[k]
        verdict[k] = 'error' not in c and c[what] <= tol
    checks['reference'] = dict(source=ref_src, comparison=cmp_, tolerance={k: TOL[k] for k in cmp_}, pass_=verdict, all_pass=all(verdict.values()))
    if a.ref in ('mfm', 'mfv'):
        checks['reference']['note'] = 'the reference holds t/t_cc and the dense fraction only; total mass is checked for constancy below'
    checks['total_mass_drift'] = dict(first=total[0], last=total[-1], max_rel_change=max(abs(x / total[0] - 1) for x in total))
    print(json.dumps(checks['reference'], indent=1), flush=True)
    if not checks['reference']['all_pass']:
        (NOTES / 'failed').mkdir(exist_ok=True)
        (NOTES / 'failed' / (a.id + '_reference_mismatch.json')).write_text(json.dumps(checks, indent=1))
        raise SystemExit('REFERENCE MISMATCH for %s: products not written' % a.id)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / '3d').mkdir(exist_ok=True)
    # meshes present, decodable, matching the recorded counts
    mesh_files = sorted((OUT / '3d').glob('f*.bin'))
    assert [p.name for p in mesh_files] == ['f%03d.bin' % i for i in range(n)], 'mesh files do not match the states'
    mchk = []
    for i, p in enumerate(mesh_files):
        b = p.read_bytes(); assert hashlib.sha256(b).hexdigest() == meta['mesh_sha256'][i], 'mesh changed on disk: ' + p.name
        ns_, tri, lv = decode_mesh(b); assert ns_ == shells[i] and tri == tris[i], (p.name, ns_, tri)
        mchk.append(lv)
    checks['meshes'] = dict(n=len(mesh_files), decoded=True, shell_levels_seen=sorted({x for lv in mchk for x in lv}), empty_frames=sum(1 for s in shells if s == 0),
                            bytes_total=sum(meta['mesh_bytes']), bytes_min=min(meta['mesh_bytes']), bytes_median=sorted(meta['mesh_bytes'])[n // 2], bytes_max=max(meta['mesh_bytes']),
                            triangles_max=max(tris), encoder_fallbacks=meta['encoder_fallbacks'])
    # sprites
    png(OUT / 'edge.png', np.concatenate(list(rgb_e), axis=0)); png(OUT / 'face.png', np.concatenate(list(rgb_f), axis=0))
    for v, arr, wpx in (('edge', rgb_e, 256), ('face', rgb_f, 128)):
        back = np.asarray(Image.open(OUT / (v + '.png')).convert('RGB'))
        assert back.shape == (128 * n, wpx, 3) and np.array_equal(back, np.concatenate(list(arr), axis=0)), v + ' sprite does not read back'
    # posters: saved state closest to 2.5 t_cc, picture only
    ip = int(np.argmin([abs(t - 2.5) for t in times]))
    Image.fromarray(rgb_e[ip]).resize((768, 384), Image.Resampling.LANCZOS).save(OUT / 'poster-edge.jpg', quality=92)
    Image.fromarray(rgb_f[ip]).resize((384, 384), Image.Resampling.LANCZOS).save(OUT / 'poster-face.jpg', quality=92)
    checks['posters'] = dict(state_index=ip, t_tcc=times[ip])
    # films
    films = {}
    for view, rgb in (('edge', rgb_e), ('face', rgb_f)):
        s = time.perf_counter(); crf = a.crf
        while True:
            dest = OUT / ('film-%s.mp4' % view)
            nfr, fidx = make_film(rgb, times, view, a.label, dest, crf)
            pr = ffprobe(dest)
            if pr['bytes'] < 25 * 1024 * 1024 or crf >= 30: break
            crf += 2
        assert pr['codec'] == 'h264' and pr['pix_fmt'] == 'yuv420p' and (pr['width'], pr['height']) == (W, H) and pr['r_frame_rate'] == '60/1' and pr['frames'] == nfr, pr
        assert pr['bytes'] < 25 * 1024 * 1024, pr
        films[view] = dict(crf=crf, frames_written=nfr, seconds_to_make=round(time.perf_counter() - s, 1), state_frames=fidx, **pr)
        print('film', view, films[view]['bytes'], 'bytes', nfr, 'frames', films[view]['seconds_to_make'], 's', flush=True)
    checks['films'] = dict(films, timing=dict(fps=FPS, frames_per_tcc=FRAMES_PER_TCC, hold_start_frames=HOLD_START, hold_end_frames=HOLD_END,
                                              readout='t = %.2f t_cc, the time interpolated linearly between the two neighbouring saved states'))
    # entries
    fd = [d / dense[0] for d in dense]
    entry = dict(id=a.id, label=a.label, code=a.code, chi=int(CHI) if CHI == int(CHI) else CHI, mach=int(a.mach) if a.mach == int(a.mach) else a.mach,
                 n=N, level=a.level, cells=2 * N ** 3, frames=[dict(time=t, nominal=round(t * 20) / 20) for t in times], views=['edge', 'face'],
                 note=a.note, status='Complete run')
    if a.group: entry['group'] = a.group
    entry.update(boundary=a.boundary, cooling='none', times=times, dense=fd, extent=[-3, 17, -5, 5], image_shape=[128, 256], color_range=[.008, 5])
    entry3d = dict(label=a.label, code=a.code, chi=entry['chi'], lvl=a.level, frames=n, note=a.note, projection_id=a.id)
    index = dict(schema_version=2, frames=['f%03d.bin' % i for i in range(n)], times=times, tris=tris, shell_counts=shells, display=entry3d,
                 visualization=dict(field='total gas density / initial cloud density', grid=[2 * N, N, N], gaussian_sigma_native_cells=.8,
                                    mesh_step_native_cells=MESH_STEP, position_bits=16,
                                    particle_deposition='cell mass / cell volume' if a.kind in ('gadget4', 'arepo', 'gizmo') else None, temporal_interpolation=False),
                 diagnostics=dict(schema_version=2, series=[dict(t_over_tcc=t, dense_mass_over_initial_dense_mass=d) for t, d in zip(times, fd)]))
    (OUT / 'entry.json').write_text(json.dumps(entry, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (OUT / 'entry3d.json').write_text(json.dumps(entry3d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (OUT / '3d' / 'index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for p in ('entry.json', 'entry3d.json', '3d/index.json'):
        json.loads((OUT / p).read_text(encoding='utf-8'))
    # text rules on everything a visitor can read
    visible = [a.label, a.note, a.code, a.boundary, entry['status']]
    bad = [s for s in visible if re.search('\u2014|\u2013|--| - ', s)]
    checks['text'] = dict(visible_strings=visible, dash_punctuation_found=bad)
    assert not bad, bad
    # folder holds exactly the contract files, none zero filled
    want = {'edge.png', 'face.png', 'poster-edge.jpg', 'poster-face.jpg', 'film-edge.mp4', 'film-face.mp4', 'entry.json', 'entry3d.json', 'stage_report.json',
            '3d/index.json', *('3d/f%03d.bin' % i for i in range(n))}
    have = {str(p.relative_to(OUT)).replace('\\', '/') for p in OUT.rglob('*') if p.is_file()}
    extra = sorted(have - want); missing = sorted(want - have - {'stage_report.json'})
    assert not extra and not missing, (extra, missing)
    zero = [p for p in sorted(have) if not not_zero_filled(OUT / p)]
    assert not zero, zero
    checks['folder'] = dict(files=len(have) + (0 if 'stage_report.json' in have else 1), extra=extra, missing=missing, zero_filled=zero)
    sizes = {p: (OUT / p).stat().st_size for p in ('edge.png', 'face.png', 'poster-edge.jpg', 'poster-face.jpg', 'film-edge.mp4', 'film-face.mp4', 'entry.json', 'entry3d.json', '3d/index.json')}
    sizes['3d_meshes_total'] = sum(meta['mesh_bytes']); sizes['folder_total_without_report'] = sum((OUT / p).stat().st_size for p in have if p != 'stage_report.json')
    rep = dict(id=a.id, label=a.label, code=a.code, kind=a.kind, level=a.level, chi=CHI, mach=a.mach, t_cc_code_units_R1=TCC,
               args=vars(a), read=dict(folder=a.run, source=meta['source'], n_snapshots=meta['n_snapshots'], snapshots=meta['read_log'],
                                       reused_from=meta.get('reused_from'), reused_files_sha256=meta.get('reused_files_sha256'), old_stage_args=meta.get('old_stage_args'),
                                       reuse_proof=meta.get('proof'), reuse_proof_all_identical=meta.get('proof_all_identical'),
                                       wall_seconds=meta['read_wall_seconds'], read_seconds=meta.get('read_seconds_total'), mesh_seconds=meta.get('mesh_seconds_total'),
                                       max_rss_MB=meta['max_rss_MB'], ramses_reader_sha256=meta.get('ramses_reader_sha256')),
               site_sources_sha256=meta['site_sources_sha256'], checks=checks, sizes=sizes,
               series=dict(t_over_tcc=times, total_mass=total, dense_mass=dense, t_code=mine.get('t_code')),
               products_wall_seconds=round(time.perf_counter() - t0, 1), products_max_rss_MB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
               written=time.strftime('%Y-%m-%d %H:%M:%S'))
    (OUT / 'stage_report.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')
    json.loads((OUT / 'stage_report.json').read_text(encoding='utf-8')); assert not_zero_filled(OUT / 'stage_report.json')
    print('products done', a.id, json.dumps(sizes), flush=True)


if __name__ == '__main__':
    if a.phase in ('read', 'all'):
        if a.reuse: phase_reuse()
        else: phase_read()
    if a.phase in ('products', 'all'):
        phase_products()
