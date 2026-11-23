"""Stage the Cloud Studio display files of one finished grid code run, with ALL its saved states.

Extended copy of studio_pipeline/stage_run.py (2026-11-22). Read only on the run folders.
Writes the work copy under <notes>/work/<id>/, a display cache under <notes>/cache/, and at the end
moves the finished folder to D:/CloudStudio-runs-staging/<id>/ (data contract of 2026-11-22):

  edge.png, face.png                 sprite sheets, one 128 px row per saved state
  poster-edge.jpg, poster-face.jpg   the state nearest 2.5 t_cc, picture only
  film-edge.mp4, film-face.mp4       1920 x 1080, H.264 yuv420p, 60 fps; every saved state shown at its own
                                     time, the frames in between cross fade between the two neighbouring states
  3d/index.json, 3d/fNNN.bin         two density surfaces (0.15 and 0.6 of the initial cloud density)
  entry.json, entry3d.json           catalog entries (no "base"; it is added at publish time)
  stage_report.json                  what was read, the checks and their results, sizes, wall time

Kinds and readers (display orientation everywhere: rho[z, y, x], wind along +x, box -3..17, -5..5, -5..5):
  athpp  Athena++ HDF5 (one file per state; LogicalLocations tile the root grid; coverage checked)
  apk    AthenaPK Parthenon HDF5 (wind along native x2; turned by a proper rotation: x = x2, y = -x1, z = x3)
  athw   Athena 4.2 legacy VTK, one file per MPI rank (reader lifted unchanged from n128_athena/reduce.py)
  enzo   Enzo HDF5, one root grid in cpu0000 (hierarchy file checked; time from the parameter file)
  enzoe  Enzo-E HDF5, one block per file (ghost zones removed; coverage checked)

Every state is checked against an independent reduction made on 2026-11-22 while it is read; a run that
does not agree stops before anything is moved to the staging folder.

  python stage_grid.py --id athpp-100-l5 --phase all        (read, film, finish)
  python stage_grid.py --id athpp-100-l5 --phase film       (films and posters again from the cache)
"""
import argparse, ast, glob, gzip, hashlib, importlib.util, json, math, os, re, resource, shutil, struct, subprocess, sys, time, zlib
from pathlib import Path
for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(k, '2')
import numpy as np, h5py
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
from PIL import Image, ImageDraw, ImageFont

NOTES = Path('/mnt/d/CloudCrushing/run_simple/analysis_20261122/studio_impl/stage_grid')
STAGING = Path('/mnt/d/CloudStudio-runs-staging')
REPO = Path('/mnt/d/CloudStudio-refresh-20261110')          # published site checkout, read only (colour table, encoder, PNG writer)
A22 = Path('/mnt/d/CloudCrushing/run_simple/analysis_20261122')
NR = '/mnt/d/CloudCrushing/native_runs'
DSENS = NR + '/sensitivity_20260907'
SENS = '/home/user/sensitivity_20260907'
PLOT_SERIES = Path('/mnt/d/CloudCrushing/meeting_20261010_v1/paper_revision_20261122_v4/plot_series.json')
FONT = '/mnt/c/Windows/Fonts/segoeui.ttf'
FONT_SB = '/mnt/c/Windows/Fonts/seguisb.ttf'
GAMMA = 5 / 3
VW = 2 * math.sqrt(GAMMA)                                    # Mach 2, rho_wind = 1, P_wind = 1

OPEN = 'The wind enters through the left face and leaves through the others'
P3 = 'All six faces are periodic, so gas leaving on the right comes back on the left'
PX = 'The box is periodic along the wind and open on its four side faces'
RUNS = {
    'athpp-100-l5': dict(kind='athpp', code='Athena++', chi=100, level=5, group='twelve', boundary='inflow and outflow', mode='nearest',
                         folder=DSENS + '/resource_pool_v3/athpp_L5_full_0', ref=('controls', 'open_L5'), lead=OPEN),
    'apk-100-l5': dict(kind='apk', code='AthenaPK', chi=100, level=5, group='twelve', boundary='inflow and outflow', mode='nearest',
                       folder=DSENS + '/athena_L5_velocity_pairs_v1/apk/full/sharp13', ref=('n128_athena', 'apk_L5'), lead=OPEN),
    'athw-100-l5': dict(kind='athw', code='Athena 4.2', chi=100, level=5, group='twelve', boundary='inflow and outflow', mode='nearest',
                        folder=SENS + '/athw/runs/L5_chi100_sharp13', ref=('n128_athena', 'athw_L5'), lead=OPEN),
    'enzo-100-l5': dict(kind='enzo', code='Enzo', chi=100, level=5, group='twelve', boundary='inflow and outflow', mode='nearest',
                        folder=DSENS + '/enzo_L5_velocity_pair_v1/full/sharp13', ref=('plot_series', 'enzo'), lead=OPEN),
    'enzoe-100-l5': dict(kind='enzoe', code='Enzo-E', chi=100, level=5, group='twelve', boundary='inflow and outflow', mode='nearest',
                         folder=DSENS + '/enzoe_L5_velocity_pair_resume_v1/enzoe_L5_full_0', ref=('plot_series', 'enzoe'), lead=OPEN),
    'athpp-10-l6': dict(kind='athpp', code='Athena++', chi=10, level=6, group=None, boundary='inflow and outflow', mode='nearest',
                        files_from=str(A22 / 'studio_pipeline/athpp_L6_chi10_filelist.txt'), ref=('hst', None), lead=OPEN),
}
for L in (3, 4, 5):
    RUNS['athpp-100-p3-l%d' % L] = dict(kind='athpp', code='Athena++', chi=100, level=L, group='boundary', boundary='periodic on all faces',
                                        mode='wrap', folder='%s/athpp_L%d_chi100_sharp13_periodic_p3' % (NR, L), ref=('controls', 'p3_L%d' % L), lead=P3)
    RUNS['athpp-100-px-l%d' % L] = dict(kind='athpp', code='Athena++', chi=100, level=L, group='boundary', boundary='periodic along the wind',
                                        mode=('nearest', 'nearest', 'wrap'), folder='%s/athpp_L%d_chi100_sharp13_periodic_px' % (NR, L),
                                        ref=('controls', 'px_L%d' % L), lead=PX)

ap = argparse.ArgumentParser()
ap.add_argument('--id', required=True, choices=sorted(RUNS))
ap.add_argument('--phase', default='all', choices=['all', 'read', 'film', 'finish', 'look'])
ap.add_argument('--limit', type=int, default=0, help='test only: stop after this many states (nothing is moved to the staging folder)')
ap.add_argument('--work', default=str(NOTES / 'work'))
a = ap.parse_args()
RUN = dict(RUNS[a.id]); RID = a.id
CHI = RUN['chi']; LEVEL = RUN['level']; CODE = RUN['code']
N = {3: 32, 4: 64, 5: 128, 6: 256}[LEVEL]
DX = 10 / N
TCC = math.sqrt(CHI) / VW
THRESH = CHI / 3
MESH_STEP = 4 if LEVEL == 6 else 2
LABEL = '%s · χ %d · level %d' % (CODE, CHI, LEVEL) + (' · ' + RUN['boundary'] if RUN['group'] == 'boundary' else '')
WORK = Path(a.work) / RID
CACHE = NOTES / 'cache'
FINAL = STAGING / RID
CACHE_FILE = CACHE / (RID + ('_test%d' % a.limit if a.limit else '') + '.npz')

def log(*x):
    print(time.strftime('%H:%M:%S'), RID, *x, flush=True)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()

def lsum(x):
    return float(np.sum(x, dtype=np.longdouble))

def not_zero_filled(p):
    """The PC has corrupted fresh files into zeros before: a written file must be non empty and must not hold
    a 4 KiB page of zeros at its start, middle or end (none of the formats written here has one there)."""
    n = os.path.getsize(p)
    if n == 0: return False
    with open(p, 'rb') as fh:
        for off in sorted({0, max(0, n // 2 - 2048), max(0, n - 4096)}):
            fh.seek(off); b = fh.read(4096)
            if b and not any(b): return False
    return True

def write_bytes(p, data):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    with open(tmp, 'wb') as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, p)
    assert os.path.getsize(p) == len(data) and not_zero_filled(p), ('write check failed', str(p))

def write_json(p, obj, compact=True):
    write_bytes(p, json.dumps(obj, ensure_ascii=False, separators=(',', ':') if compact else None, indent=None if compact else 1).encode('utf-8'))

# ------------------------------------------------------------------ site functions, lifted unchanged from the published checkout
def lift(path, names):
    src = Path(path).read_text(encoding='utf-8'); out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out[node.name] = ast.get_source_segment(src, node)
    return out
_src = {**lift(REPO / 'analysis/recent_gallery_export.py', {'png'}), **lift(REPO / 'analysis/recent_3d_export.py', {'encode'})}
_ns = dict(np=np, DX=DX, struct=struct, gzip=gzip, zlib=zlib, gaussian_filter=gaussian_filter, marching_cubes=marching_cubes)
exec(_src['png'], _ns); png_site = _ns['png']
_enc = _src['encode']
assert "step_size=2" in _enc and "mode='wrap' if periodic else 'nearest'" in _enc
_enc = _enc.replace("mode='wrap' if periodic else 'nearest'", 'mode=periodic')     # the third argument now carries the filter mode per axis
ENCODERS = []
for step in ([MESH_STEP, 1] if MESH_STEP != 1 else [1]):
    ns = dict(_ns); exec(_enc.replace('step_size=2', 'step_size=%d' % step), ns); ENCODERS.append((step, ns['encode']))
LUT = np.array(json.loads((REPO / 'assets/recent/catalog.json').read_text(encoding='utf-8'))['colormap'])
assert LUT.shape == (256, 3)

def color(x):
    """Same mapping as the site's recent runs: log10 of column density / (rho_cloud,0 R), 0.008 to 5, magma; rows flipped so +y is up."""
    idx = np.floor(np.clip((np.log10(np.maximum(x, 1e-30)) - np.log10(.008)) / (np.log10(5) - np.log10(.008)), 0, 1) * 255).astype(int)
    return np.round(LUT[idx] * 255).astype('uint8')[::-1]

def to_sprite(col):
    """Native column density map -> the 128 px row geometry of the compare page."""
    if N == 128: return col
    if N < 128:
        f = 128 // N; return np.repeat(np.repeat(col, f, axis=0), f, axis=1)
    f = N // 128; h, w = col.shape
    return col.reshape(h // f, f, w // f, f).mean(axis=(1, 3))

# ------------------------------------------------------------------ readers
def file_list():
    k = RUN['kind']
    if RUN.get('files_from'):
        files = [l.strip() for l in Path(RUN['files_from']).read_text().splitlines() if l.strip()]
        return [(os.path.basename(f), [f]) for f in files], dict(list_file=RUN['files_from'], folders=sorted({os.path.dirname(f) for f in files}))
    d = RUN['folder']
    if k == 'athpp':
        files = sorted(glob.glob(d + '/*.out2.*.athdf'))
        return [(os.path.basename(f), [f]) for f in files], dict(folder=d)
    if k == 'apk':
        files = sorted(glob.glob(d + '/parthenon.prim.*.phdf'))      # 00000 .. 00099 and final; ordered by stored time below
        return [(os.path.basename(f), [f]) for f in files], dict(folder=d)
    if k == 'athw':
        snaps, inv = N128.athw_snapshots(d)
        return snaps, dict(folder=d, inventory=inv)
    if k == 'enzo':
        dumps = sorted(n for n in os.listdir(d) if re.fullmatch(r'DD\d{4}', n))
        # DD0101 is a second dump of the final state, written at the stop time 4.6e-7 t_cc after DD0100: use each state once
        assert dumps[-1] == 'DD0101' and len(dumps) == 102, dumps[-3:]
        return [(n, [d + '/' + n]) for n in dumps[:101]], dict(folder=d, skipped=['DD0101'])
    if k == 'enzoe':
        fs = glob.glob(d + '/ic-*-p*.h5')
        counts = sorted({int(re.search(r'ic-(\d+)-p', f).group(1)) for f in fs})
        procs = sorted({int(re.search(r'-p(\d+)\.h5$', f).group(1)) for f in fs})
        assert counts == list(range(101)) and procs == list(range(8)) and len(fs) == 808, (len(fs), counts[:2], procs)
        return [('ic-%03d' % c, ['%s/ic-%03d-p%02d.h5' % (d, c, p) for p in procs]) for c in counts], dict(folder=d)
    raise ValueError(k)

def check_box(lo, hi, n):
    assert np.allclose(lo, [-3, -5, -5], atol=1e-12) and np.allclose(hi, [17, 5, 5], atol=1e-12), ('box', lo, hi)
    assert list(n) == [2 * N, N, N], ('grid', n)

def read_athpp(files, want_vel):
    with h5py.File(files[0], 'r') as h:
        nx, ny, nz = [int(v) for v in h.attrs['RootGridSize']]
        x1, x2, x3 = [[float(v) for v in h.attrs[k][:2]] for k in ('RootGridX1', 'RootGridX2', 'RootGridX3')]
        check_box([x1[0], x2[0], x3[0]], [x1[1], x2[1], x3[1]], [nx, ny, nz])
        names = [v.decode() for v in h.attrs['VariableNames']]
        ds = h['prim']; bz, by, bx = ds.shape[2:]
        assert ds.shape[0] == len(names) and [int(v) for v in h.attrs['MeshBlockSize']] == [bx, by, bz]
        assert int(h.attrs['MaxLevel']) == 0
        ll = h['LogicalLocations'][:]
        assert ll.shape[0] * bx * by * bz == nx * ny * nz
        t = float(h.attrs['Time'])
        fields = {'rho': names.index('rho')}
        if want_vel: fields.update(vx=names.index('vel1'), vy=names.index('vel2'), vz=names.index('vel3'))
        out = {}
        cover = np.zeros((nz, ny, nx), dtype=np.int8)
        for key, vi in fields.items():
            arr = ds[vi]                                             # one contiguous read of the variable
            g = np.empty((nz, ny, nx))
            for n, (x, y, z) in enumerate(ll):
                g[z * bz:(z + 1) * bz, y * by:(y + 1) * by, x * bx:(x + 1) * bx] = arr[n]
                if key == 'rho': cover[z * bz:(z + 1) * bz, y * by:(y + 1) * by, x * bx:(x + 1) * bx] += 1
            out[key] = g; del arr
        assert cover.min() == 1 and cover.max() == 1, 'mesh blocks do not cover the grid exactly once'
        # cell centres stored in the file must be the uniform lattice of the box
        x1v = h['x1v'][:]; x2v = h['x2v'][:]; x3v = h['x3v'][:]
        err = max(float(np.abs(x1v[n] - (-3 + (ll[n, 0] * bx + np.arange(bx) + .5) * DX)).max()) for n in range(len(ll)))
        err = max(err, max(float(np.abs(x2v[n] - (-5 + (ll[n, 1] * by + np.arange(by) + .5) * DX)).max()) for n in range(len(ll))))
        err = max(err, max(float(np.abs(x3v[n] - (-5 + (ll[n, 2] * bz + np.arange(bz) + .5) * DX)).max()) for n in range(len(ll))))
        assert err < 1e-9, ('cell centres', err)
    return out, t, dict(centre_error=err)

def read_apk(files, want_vel):
    with h5py.File(files[0], 'r') as h:
        info = h['Info'].attrs
        names = [x.decode() if isinstance(x, bytes) else str(x) for x in info['ComponentNames']]
        n1, n2, n3 = [int(x) for x in info['RootGridSize']]
        m1, m2, m3 = [int(x) for x in info['MeshBlockSize']]
        dom = [float(x) for x in info['RootGridDomain']]
        assert int(info['IncludesGhost']) == 0 and int(info['MaxLevel']) == 0
        # native x1 transverse [-5, 5], x2 along the wind [-3, 17], x3 transverse [-5, 5]
        assert dom[0:2] == [-5, 5] and dom[3:5] == [-3, 17] and dom[6:8] == [-5, 5], dom
        assert (n1, n2, n3) == (N, 2 * N, N), (n1, n2, n3)
        t = float(info['Time'])
        ll = h['LogicalLocations'][...]
        nb = ll.shape[0]; assert nb * m1 * m2 * m3 == n1 * n2 * n3
        prim = h['prim']; assert prim.shape == (nb, len(names), m3, m2, m1)
        fields = {'rho': 'prim_density'}
        if want_vel: fields.update(v1='prim_velocity_1', v2='prim_velocity_2', v3='prim_velocity_3')
        nat = {}
        cover = np.zeros((n3, n2, n1), dtype=np.int8)
        for key, cname in fields.items():
            data = prim[:, names.index(cname)]
            g = np.empty((n3, n2, n1))
            for b in range(nb):
                i0, j0, k0 = int(ll[b, 0]) * m1, int(ll[b, 1]) * m2, int(ll[b, 2]) * m3
                g[k0:k0 + m3, j0:j0 + m2, i0:i0 + m1] = data[b]
                if key == 'rho': cover[k0:k0 + m3, j0:j0 + m2, i0:i0 + m1] += 1
            nat[key] = g; del data
        assert cover.min() == 1 and cover.max() == 1, 'mesh blocks do not cover the grid exactly once'
        dx = [(dom[1] - dom[0]) / n1, (dom[4] - dom[3]) / n2, (dom[7] - dom[6]) / n3]
        assert np.allclose(dx, DX, rtol=0, atol=1e-15)
        vl = [h['VolumeLocations/x'][...], h['VolumeLocations/y'][...], h['VolumeLocations/z'][...]]
        lo = [dom[0], dom[3], dom[6]]; mb = [m1, m2, m3]; err = 0.0
        for ax in range(3):
            for b in range(nb):
                exp = lo[ax] + (int(ll[b, ax]) * mb[ax] + np.arange(mb[ax]) + 0.5) * DX
                err = max(err, float(np.abs(vl[ax][b] - exp).max()))
        assert err < 1e-9, ('cell centres', err)
    # native [x3, x2, x1] -> display [z, y, x] with x = x2, y = -x1, z = x3 (a rotation by 90 degrees about x3)
    turn = lambda g: np.ascontiguousarray(np.transpose(g, (0, 2, 1))[:, ::-1, :])
    out = {'rho': turn(nat.pop('rho'))}
    if want_vel:
        out['vx'] = turn(nat['v2']); out['vy'] = -turn(nat['v1']); out['vz'] = turn(nat['v3'])
    return out, t, dict(centre_error=err)

def read_athw(files, want_vel):
    d = N128.athw_read(files)
    check_box(d['lo'], d['hi'], d['n'])
    assert np.allclose(d['dx'], DX, rtol=0, atol=1e-6)
    out = {'rho': d['rho']}
    if want_vel: out.update(vx=d['vel'][0], vy=d['vel'][1], vz=d['vel'][2])
    return out, d['time'], dict(time_text=d['time_text'], zero_run=d['zero_run'], nfiles=d['nfiles'])

def parse_enzo_hierarchy(path):
    grids = []; cur = None
    for line in open(path):
        m = re.match(r'^Grid = (\d+)', line)
        if m: cur = dict(id=int(m.group(1))); grids.append(cur); continue
        if cur is None: continue
        m = re.match(r'^(GridDimension|GridStartIndex|GridEndIndex|GridLeftEdge|GridRightEdge|Time|BaryonFileName|NumberOfBaryonFields)\s*=\s*(.*)$', line.strip())
        if m: cur[m.group(1)] = m.group(2).strip()
    return grids

def read_enzo(files, want_vel):
    d = files[0]; n = os.path.basename(d)[2:]
    par = '%s/CW_%s' % (d, n)
    t = None
    for line in open(par):
        if line.startswith('InitialTime'): t = float(line.split('=')[1])
    grids = parse_enzo_hierarchy(par + '.hierarchy')
    assert len(grids) == 1, ('grids', len(grids))
    g = grids[0]
    si = [int(v) for v in g['GridStartIndex'].split()]; ei = [int(v) for v in g['GridEndIndex'].split()]
    check_box([float(v) for v in g['GridLeftEdge'].split()], [float(v) for v in g['GridRightEdge'].split()], [e - s + 1 for s, e in zip(si, ei)])
    assert abs(float(g['Time']) - t) <= 1e-12 * max(1, t), ('hierarchy time', g['Time'], t)
    assert g['BaryonFileName'].endswith('CW_%s.cpu0000' % n)
    fields = {'rho': 'Density'}
    if want_vel: fields.update(vx='x-velocity', vy='y-velocity', vz='z-velocity')
    out = {}
    with h5py.File(par + '.cpu0000', 'r') as h:
        grp = h['Grid%08d' % g['id']]
        for key, name in fields.items():
            arr = grp[name][...]
            assert arr.shape == (N, N, 2 * N), arr.shape                     # stored [z, y, x] without ghost zones
            out[key] = arr.astype(np.float64)
    return out, t, dict(parameter_file=os.path.basename(par))

def read_enzoe(files, want_vel):
    fields = {'rho': 'field_density'}
    if want_vel: fields.update(vx='field_velocity_x', vy='field_velocity_y', vz='field_velocity_z')
    out = {k: np.zeros((N, N, 2 * N)) for k in fields}
    cover = np.zeros((N, N, 2 * N), dtype=np.uint8); times = set()
    for p in files:
        with h5py.File(p, 'r') as h:
            times.add(float(h.attrs['time'][0]))
            assert list(h.attrs['lower']) == [-3, -5, -5] and list(h.attrs['upper']) == [17, 5, 5]
            for grp in h.values():
                lo = np.rint((grp.attrs['lower'] - np.array([-3., -5., -5.])) / DX).astype(int)
                s0 = grp.attrs['enzo_GridStartIndex']; e0 = grp.attrs['enzo_GridEndIndex'] + 1
                assert np.allclose(grp.attrs['enzo_CellWidth'], DX)
                assert abs(float(grp.attrs['time'][0]) - min(times)) == 0
                for key, name in fields.items():
                    r = grp[name][s0[2]:e0[2], s0[1]:e0[1], s0[0]:e0[0]]       # stored [z, y, x] with ghost zones
                    sl = (slice(lo[2], lo[2] + r.shape[0]), slice(lo[1], lo[1] + r.shape[1]), slice(lo[0], lo[0] + r.shape[2]))
                    assert np.allclose(np.array(grp.attrs['upper']) - np.array(grp.attrs['lower']), np.array(r.shape[::-1]) * DX)
                    out[key][sl] = r
                    if key == 'rho': cover[sl] += 1
    assert len(times) == 1, times
    assert cover.min() == 1 and cover.max() == 1, 'blocks do not cover the grid exactly once'
    return out, times.pop(), dict(nfiles=len(files))

READERS = dict(athpp=read_athpp, apk=read_apk, athw=read_athw, enzo=read_enzo, enzoe=read_enzoe)

N128 = None
if RUN['kind'] in ('athw',):
    spec = importlib.util.spec_from_file_location('n128_reduce', str(A22 / 'n128_athena/reduce.py'))
    N128 = importlib.util.module_from_spec(spec); spec.loader.exec_module(N128)

# ------------------------------------------------------------------ reference series (independent reductions of 2026-11-22)
def load_reference():
    kind, key = RUN['ref']
    if kind == 'controls':
        p = A22 / 'athpp_controls/series.json'; r = json.loads(p.read_text())['runs'][key]; s = r['series']
        assert r['meta']['folder'].rstrip('/') == RUN['folder'].rstrip('/'), (r['meta']['folder'], RUN['folder'])
        return dict(file=str(p), sha256=sha256_file(p), run=key, names=s['file'], time=s['time'], mass=s['mass'], dense=s['dense_mass'],
                    y_asym=s['y_asym'], z_asym=s['z_asym'])
    if kind == 'n128_athena':
        p = A22 / 'n128_athena/series.json'; r = json.loads(p.read_text())['runs'][key]
        assert r['folder'].rstrip('/') == RUN['folder'].rstrip('/'), (r['folder'], RUN['folder'])
        return dict(file=str(p), sha256=sha256_file(p), run=key, names=r['snapshot'], time=r['time_code'], mass=r['total_mass'], dense=r['M_d'])
    if kind == 'plot_series':
        p = PLOT_SERIES; e = [x for x in json.loads(p.read_text()) if x['code'] == key and x['level'] == 5]
        assert len(e) == 1; e = e[0]
        return dict(file=str(p), sha256=sha256_file(p), run='%s level 5' % key, source=e.get('source'), t_tcc=e['times'], f_d=e['dense'])
    if kind == 'hst':
        rows = {}
        for d in sorted({os.path.dirname(l.strip()) for l in Path(RUN['files_from']).read_text().splitlines() if l.strip()}):
            h = glob.glob(d + '/*.hst'); assert len(h) == 1
            arr = np.loadtxt(h[0]); rows[d] = arr
        return dict(file='history files of the three folders', hst={d: dict(file=glob.glob(d + '/*.hst')[0], rows=int(v.shape[0])) for d, v in rows.items()}, arrays=rows)
    raise ValueError(kind)

# ------------------------------------------------------------------ phase 1: read every state once
def safe_encode(rho, fallbacks, i):
    for k, (step, enc) in enumerate(ENCODERS):
        try:
            out = enc(rho, CHI, RUN['mode'])
            if k: fallbacks.append(dict(state=i, used_step=step))
            return out
        except RuntimeError:
            continue
    fallbacks.append(dict(state=i, used_step=None, empty=True))
    return gzip.compress(struct.pack('<B', 0), compresslevel=6, mtime=0), 0, 0

def decode_mesh(blob):
    raw = gzip.decompress(blob); n = raw[0]; pos = 1; tris = 0
    for _ in range(n):
        level, op, r, g, b, lx, ly, lz, hx, hy, hz, nv, nt = struct.unpack_from('<ff3f3f3fII', raw, pos); pos += struct.calcsize('<ff3f3f3fII')
        v = np.frombuffer(raw, '<u2', 3 * nv, pos); pos += 6 * nv
        f = np.frombuffer(raw, '<u4', 3 * nt, pos); pos += 12 * nt
        assert nt == 0 or int(f.max()) < nv
        assert -3 - 1e-4 <= lx <= hx <= 17 + 1e-4 and -5 - 1e-4 <= ly <= hy <= 5 + 1e-4 and -5 - 1e-4 <= lz <= hz <= 5 + 1e-4
        assert abs(level - .15) < 1e-6 or abs(level - .6) < 1e-6
        tris += nt
    assert pos == len(raw)
    return n, tris

def phase_read():
    t0 = time.perf_counter()
    snaps, where = file_list()
    ref = load_reference()
    if WORK.exists(): shutil.rmtree(WORK)
    (WORK / '3d').mkdir(parents=True)
    CACHE.mkdir(exist_ok=True)
    reader = READERS[RUN['kind']]
    rows = []; edge_rows = []; face_rows = []; col_e_all = []; col_f_all = []; fallbacks = []; read_s = mesh_s = 0.0
    order_check = []
    if RUN['kind'] == 'apk':
        # order the AthenaPK files by their stored time (the last one is named "final")
        tt = []
        for name, files in snaps:
            with h5py.File(files[0], 'r') as h: tt.append(float(h['Info'].attrs['Time']))
        order = sorted(range(len(snaps)), key=lambda i: tt[i])
        order_check = dict(name_order_equals_time_order=order == list(range(len(snaps))))
        snaps = [snaps[i] for i in order]
    if RUN['kind'] == 'athw':
        assert len(snaps) == 101
    assert len(snaps) == 101, ('states', len(snaps))
    if a.limit: snaps = snaps[:a.limit]
    vel_check = None
    for i, (name, files) in enumerate(snaps):
        s = time.perf_counter()
        fld, t, extra = reader(files, i == 0)
        rho = fld['rho']; read_s += time.perf_counter() - s
        assert rho.shape == (N, N, 2 * N), rho.shape
        fin = bool(np.isfinite(rho).all()); pos = bool(rho.min() > 0)
        assert fin and pos, ('finite and positive', name)
        if i == 0:
            wind = rho < 1.5
            vel_check = dict(median_vx_over_vw=float(np.median(fld['vx'][wind]) / VW), median_vy_over_vw=float(np.median(fld['vy'][wind]) / VW),
                             median_vz_over_vw=float(np.median(fld['vz'][wind]) / VW), max_rho=float(rho.max()), min_rho=float(rho.min()),
                             max_density_at_centre=bool(np.unravel_index(np.argmax(rho), rho.shape)[2] in (int(3 / DX) - 1, int(3 / DX))))
            assert abs(vel_check['median_vx_over_vw'] - 1) < 1e-6 and abs(vel_check['median_vy_over_vw']) < 1e-6 and abs(vel_check['median_vz_over_vw']) < 1e-6, vel_check
            assert abs(vel_check['max_rho'] / CHI - 1) < 1e-3 and vel_check['max_density_at_centre'], vel_check
            del fld
        mass = lsum(rho) * DX ** 3
        dense_mask = rho > THRESH
        dense = lsum(rho[dense_mask]) * DX ** 3
        y_asym = float(np.abs(rho - rho[:, ::-1, :]).max()); z_asym = float(np.abs(rho - rho[::-1, :, :]).max())
        col_e = rho.sum(axis=0) * DX / CHI; col_f = rho.sum(axis=2) * DX / CHI
        assert abs(col_e.sum() * DX ** 2 * CHI / mass - 1) < 1e-10 and abs(col_f.sum() * DX ** 2 * CHI / mass - 1) < 1e-10
        edge_rows.append(color(to_sprite(col_e))); face_rows.append(color(to_sprite(col_f)))
        col_e_all.append(col_e.astype(np.float32)); col_f_all.append(col_f.astype(np.float32))
        s = time.perf_counter()
        blob, ntri, nsh = safe_encode(rho, fallbacks, i)
        dn, dt_ = decode_mesh(blob); assert (dn, dt_) == (nsh, ntri)
        write_bytes(WORK / '3d' / ('f%03d.bin' % i), blob)
        mesh_s += time.perf_counter() - s
        del rho, dense_mask
        row = dict(state=i, name=name, files=[os.path.relpath(f, where.get('folder', '/')) if where.get('folder') else f for f in files],
                   time_code=t, t_tcc=t / TCC, total_mass=mass, dense_mass=dense, y_asym=y_asym, z_asym=z_asym,
                   mesh_bytes=len(blob), triangles=ntri, shells=nsh, **{k: v for k, v in extra.items() if v is not None})
        check_state(ref, i, row)
        rows.append(row)
        if i % 10 == 0 or i == len(snaps) - 1:
            log('state %3d/%d  t = %.4f t_cc  M = %.6f  f_d = %.5f  mesh %d KB  read %.0f s  mesh %.0f s' % (
                i + 1, len(snaps), row['t_tcc'], mass, dense / rows[0]['dense_mass'], len(blob) // 1024, read_s, mesh_s))
    times = [r['t_tcc'] for r in rows]
    assert abs(times[0]) < 1e-12 and all(b > c for b, c in zip(times[1:], times[:-1])), 'times must start at 0 and increase'
    if not a.limit:
        assert len(rows) == 101 and abs(times[-1] - 5) < 2e-6, (len(rows), times[-1])
    fd = [r['dense_mass'] / rows[0]['dense_mass'] for r in rows]
    summary = summarize_checks(ref, rows)
    np.savez(CACHE_FILE, col_edge=np.stack(col_e_all), col_face=np.stack(col_f_all), times=np.array(times))
    assert not_zero_filled(CACHE_FILE)
    # sprite sheets
    for view, rr, w in (('edge', edge_rows, 256), ('face', face_rows, 128)):
        sheet = np.concatenate(rr, axis=0); assert sheet.shape == (128 * len(rr), w, 3)
        p = WORK / (view + '.png'); png_site(p, sheet)
        assert not_zero_filled(p)
        with Image.open(p) as im: assert im.size == (w, 128 * len(rr)) and im.mode == 'RGB'
    final_pct = round(100 * fd[-1])
    note = '%s, and by t = 5 t_cc the gas denser than a third of the initial cloud keeps %d percent of its starting mass.' % (RUN['lead'], final_pct)
    entry = dict(id=RID, label=LABEL, code=CODE, chi=CHI, mach=2, n=N, level=LEVEL, cells=2 * N ** 3,
                 frames=[dict(time=t, nominal=round(t * 20) / 20) for t in times], views=['edge', 'face'], note=note, status='Complete run')
    if RUN['group']: entry['group'] = RUN['group']
    entry.update(boundary=RUN['boundary'], cooling='none', times=times, dense=fd, extent=[-3, 17, -5, 5], image_shape=[128, 256], color_range=[.008, 5])
    write_json(WORK / 'entry.json', entry)
    e3 = dict(label=LABEL, code=CODE, chi=CHI, lvl=LEVEL, frames=len(rows), note=note, projection_id=RID)
    write_json(WORK / 'entry3d.json', e3)
    index = dict(schema_version=2, frames=['f%03d.bin' % i for i in range(len(rows))], times=times, tris=[r['triangles'] for r in rows],
                 shell_counts=[r['shells'] for r in rows], display=e3,
                 visualization=dict(field='total gas density / initial cloud density', grid=[2 * N, N, N], gaussian_sigma_native_cells=.8,
                                    mesh_step_native_cells=MESH_STEP, position_bits=16, particle_deposition=None, temporal_interpolation=False),
                 diagnostics=dict(schema_version=2, series=[dict(t_over_tcc=t, dense_mass_over_initial_dense_mass=d) for t, d in zip(times, fd)]))
    write_json(WORK / '3d' / 'index.json', index)
    mesh_bytes = [r['mesh_bytes'] for r in rows]
    rep = dict(id=RID, label=LABEL, code=CODE, chi=CHI, level=LEVEL, n=N, cells=2 * N ** 3, dx=DX, t_cc_code_units=TCC, dense_threshold=THRESH,
               boundary=RUN['boundary'], group=RUN['group'], kind=RUN['kind'], read_from=where, states=len(rows),
               limited_test=bool(a.limit), axis_and_initial_state_check=vel_check, order_check=order_check,
               reference=dict({k: v for k, v in ref.items() if k not in ('names', 'time', 'mass', 'dense', 'y_asym', 'z_asym', 't_tcc', 'f_d', 'arrays')}),
               checks=summary, mesh=dict(step=MESH_STEP, filter_mode=RUN['mode'], fallbacks=fallbacks, total_bytes=sum(mesh_bytes), min=min(mesh_bytes),
                                         median=sorted(mesh_bytes)[len(mesh_bytes) // 2], max=max(mesh_bytes), triangles_max=max(r['triangles'] for r in rows)),
               dense_fraction_final=fd[-1], note=note,
               stages=dict(read_seconds=round(read_s, 1), mesh_seconds=round(mesh_s, 1), read_phase_wall_seconds=round(time.perf_counter() - t0, 1)),
               max_rss_MB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
               states_table=rows,
               stage_script=dict(path=str(Path(__file__).resolve()), sha256=sha256_file(__file__)),
               lifted=dict(encoder=str(REPO / 'analysis/recent_3d_export.py'), png=str(REPO / 'analysis/recent_gallery_export.py'),
                           colour_table=str(REPO / 'assets/recent/catalog.json')))
    if N128 is not None: rep['lifted']['athena42_reader'] = dict(path=str(A22 / 'n128_athena/reduce.py'), sha256=sha256_file(A22 / 'n128_athena/reduce.py'))
    write_json(WORK / 'stage_report.json', rep, compact=False)
    log('read phase done: %d states, %.0f s; checks %s' % (len(rows), time.perf_counter() - t0, json.dumps(summary['verdict'])))

def rel(a_, b_):
    return abs(a_ - b_) / max(abs(b_), 1e-300)

def check_state(ref, i, row):
    """Stop the run at the first state that disagrees with the independent reduction."""
    if 'mass' in ref:
        assert os.path.basename(row['name']) == os.path.basename(ref['names'][i]), ('file name', row['name'], ref['names'][i])
        assert row['time_code'] == ref['time'][i] or rel(row['time_code'], ref['time'][i]) < 1e-12, ('time', row['time_code'], ref['time'][i])
        assert rel(row['total_mass'], ref['mass'][i]) < 1e-12, ('total mass', i, row['total_mass'], ref['mass'][i])
        assert rel(row['dense_mass'], ref['dense'][i]) < 1e-12, ('dense mass', i, row['dense_mass'], ref['dense'][i])
        if 'y_asym' in ref:
            assert row['y_asym'] == ref['y_asym'][i] and row['z_asym'] == ref['z_asym'][i], ('mirror', i)
    if 't_tcc' in ref:
        assert abs(row['t_tcc'] - ref['t_tcc'][i]) < 1e-9, ('time', i, row['t_tcc'], ref['t_tcc'][i])
    if RUN['kind'] == 'athpp':
        assert row['y_asym'] == 0 and row['z_asym'] == 0, ('Athena++ keeps exact mirror symmetry in y and z', i, row['y_asym'], row['z_asym'])
    if 'hst' in ref:
        d = os.path.dirname(row['files'][0]); arr = ref['arrays'][d]
        k = int(np.argmin(np.abs(arr[:, 0] - row['time_code'])))
        row['hst_time'] = float(arr[k, 0]); row['hst_mass'] = float(arr[k, 2])
        assert abs(arr[k, 0] - row['time_code']) <= 1e-5 * max(1, row['time_code']), ('history time', row['time_code'], arr[k, 0])
        assert rel(row['total_mass'], arr[k, 2]) < 1e-5, ('history mass (6 digits)', row['total_mass'], arr[k, 2])

def summarize_checks(ref, rows):
    out = dict(states=len(rows), finite_and_positive=True, times_from_files=True)
    out['t_tcc_first_last'] = [rows[0]['t_tcc'], rows[-1]['t_tcc']]
    out['largest_step_tcc'] = max(b['t_tcc'] - c['t_tcc'] for b, c in zip(rows[1:], rows[:-1]))
    out['smallest_step_tcc'] = min(b['t_tcc'] - c['t_tcc'] for b, c in zip(rows[1:], rows[:-1]))
    out['max_mirror_difference_y'] = max(r['y_asym'] for r in rows); out['max_mirror_difference_z'] = max(r['z_asym'] for r in rows)
    m = [r['total_mass'] for r in rows]
    out['total_mass_first_last_min_max'] = [m[0], m[-1], min(m), max(m)]
    fd = [r['dense_mass'] / rows[0]['dense_mass'] for r in rows]
    v = {}
    if 'mass' in ref:
        n = len(rows)
        v['reference'] = '%s, run %s' % (ref['file'], ref['run'])
        v['file_names_equal'] = all(os.path.basename(r['name']) == os.path.basename(ref['names'][i]) for i, r in enumerate(rows))
        v['max_rel_diff_time'] = max(rel(r['time_code'], ref['time'][i]) for i, r in enumerate(rows[1:], 1)) if n > 1 else 0
        v['max_rel_diff_total_mass'] = max(rel(r['total_mass'], ref['mass'][i]) for i, r in enumerate(rows))
        v['max_rel_diff_dense_mass'] = max(rel(r['dense_mass'], ref['dense'][i]) for i, r in enumerate(rows))
        v['max_abs_diff_total_mass'] = max(abs(r['total_mass'] - ref['mass'][i]) for i, r in enumerate(rows))
        v['max_abs_diff_dense_mass'] = max(abs(r['dense_mass'] - ref['dense'][i]) for i, r in enumerate(rows))
        if 'y_asym' in ref: v['mirror_values_equal'] = all(r['y_asym'] == ref['y_asym'][i] and r['z_asym'] == ref['z_asym'][i] for i, r in enumerate(rows))
        v['reference_states'] = len(ref['names'])
        v['pass'] = v['file_names_equal'] and v['max_rel_diff_total_mass'] < 1e-12 and v['max_rel_diff_dense_mass'] < 1e-12
    if 't_tcc' in ref:
        v['reference'] = '%s, entry %s (%s)' % (ref['file'], ref['run'], ref.get('source'))
        v['reference_states'] = len(ref['t_tcc'])
        v['max_abs_diff_t_tcc'] = max(abs(r['t_tcc'] - ref['t_tcc'][i]) for i, r in enumerate(rows))
        v['max_abs_diff_dense_fraction'] = max(abs(fd[i] - ref['f_d'][i]) for i in range(len(rows)))
        v['max_rel_diff_dense_fraction'] = max(rel(fd[i], ref['f_d'][i]) for i in range(len(rows)))
        if len(ref['t_tcc']) > len(rows) and not a.limit:
            v['reference_states_not_used'] = [dict(t_tcc=ref['t_tcc'][i], dense_fraction=ref['f_d'][i]) for i in range(len(rows), len(ref['t_tcc']))]
        # same initial state as the Athena++ open run (identical initial conditions up to round off)
        o = json.loads((A22 / 'athpp_controls/series.json').read_text())['runs']['open_L5']['series']
        v['initial_total_mass_vs_athpp_open_L5_rel'] = rel(rows[0]['total_mass'], o['mass'][0])
        v['initial_dense_mass_vs_athpp_open_L5_rel'] = rel(rows[0]['dense_mass'], o['dense_mass'][0])
        v['pass'] = v['max_abs_diff_t_tcc'] < 1e-9 and v['max_rel_diff_dense_fraction'] < 1e-9
    if 'hst' in ref:
        v['reference'] = 'mass column of the Athena++ history file in the folder of each snapshot (printed with 6 significant digits)'
        v['max_rel_diff_total_mass_vs_history'] = max(rel(r['total_mass'], r['hst_mass']) for r in rows)
        v['max_abs_diff_time_vs_history'] = max(abs(r['time_code'] - r['hst_time']) for r in rows)
        dm = np.diff(m); d2 = np.abs(np.diff(dm)) if len(m) > 2 else np.zeros(1)
        v['mass_change_per_step_min_max'] = [float(dm.min()), float(dm.max())]
        v['largest_second_difference_of_total_mass'] = float(d2.max())
        joins = [i for i in range(1, len(rows)) if os.path.dirname(rows[i]['files'][0]) != os.path.dirname(rows[i - 1]['files'][0])]
        v['piece_joins_at_state'] = joins
        # d2[k] uses states k, k+1, k+2: the two values that straddle a join at state j are d2[j-2] and d2[j-1]
        v['second_difference_at_joins'] = {str(j): [float(d2[k]) for k in (j - 2, j - 1) if 0 <= k < len(d2)] for j in joins}
        v['second_difference_median'] = float(np.median(d2))
        v['pass'] = v['max_rel_diff_total_mass_vs_history'] < 1e-5 and out['max_mirror_difference_y'] == 0 and out['max_mirror_difference_z'] == 0
    if RUN['kind'] == 'athpp':
        v['exact_mirror_symmetry_y_z'] = out['max_mirror_difference_y'] == 0 and out['max_mirror_difference_z'] == 0
        v['pass'] = v.get('pass', True) and v['exact_mirror_symmetry_y_z']
    out['verdict'] = v
    out['dense_fraction_final'] = fd[-1]
    assert v.get('pass'), ('check failed', v)
    return out

# ------------------------------------------------------------------ phase 2: posters and films from the cache
W, H = 1920, 1080
BG = (11, 16, 23); TEXT = (236, 241, 245); MUTED = (155, 170, 185); ACCENT = (229, 186, 131)
FPS = 60; SPAN = 1200; HOLD = 60                                 # 20 s for 0 to 5 t_cc, then the last state held 1 s

def font(n, semibold=False):
    return ImageFont.truetype(FONT_SB if semibold else FONT, n)

def big_image(rgb, size):
    factor = size[0] / rgb.shape[1]
    resample = Image.Resampling.NEAREST if factor >= 12 else Image.Resampling.LANCZOS   # levels 3 and 4 show their cells
    return np.asarray(Image.fromarray(rgb).resize(size, resample), dtype=np.float32)

def film_background(view, size, ox, oy):
    bg = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(bg)
    d.text((72, 40), LABEL, font=font(38, True), fill=TEXT)
    sub = 'Mach 2 · edge-on view · wind from left to right' if view == 'edge' else 'Mach 2 · face-on view · looking along the wind'
    d.text((72, 96), sub, font=font(24), fill=MUTED)
    d.rectangle((ox - 1, oy - 1, ox + size[0], oy + size[1]), outline=(38, 50, 63))
    # colour bar with its unit
    d.text((72, 952), 'Column density of all gas', font=font(24), fill=TEXT)
    d.text((72, 988), 'in units of initial cloud density × cloud radius, log scale from 0.008 to 5', font=font(20), fill=MUTED)
    x0, x1, y0, y1 = 1336, 1848, 958, 980
    for n, c in enumerate(LUT): d.rectangle((x0 + 2 * n, y0, x0 + 2 * n + 1, y1), fill=tuple(int(round(v * 255)) for v in c))
    f = font(18)
    for v, s in ((.01, '0.01'), (.1, '0.1'), (1, '1'), (5, '5')):
        x = x0 + (math.log10(v) - math.log10(.008)) / (math.log10(5) - math.log10(.008)) * (x1 - x0)
        d.line((x, y1, x, y1 + 6), fill=MUTED, width=2)
        wdt = f.getlength(s); xt = min(max(x - wdt / 2, x0), x1 - wdt)
        d.text((xt, y1 + 9), s, font=f, fill=MUTED)
    cs = 'Cloud Studio'; fc = font(18, True)
    d.text((W - 72 - fc.getlength(cs), 1036), cs, font=fc, fill=(120, 134, 150))
    return bg

def readout(draw, t):
    fa = font(40); fs = font(26)
    widest = fa.getlength('t = 0.00 t') + fs.getlength('cc')
    x = W - 72 - widest; y = 40
    main = 't = %.2f t' % t
    draw.text((x, y), main, font=fa, fill=ACCENT)
    draw.text((x + fa.getlength(main) + 1, y + 24), 'cc', font=fs, fill=ACCENT)

def phase_film():
    t0 = time.perf_counter()
    c = np.load(CACHE_FILE); times = [float(v) for v in c['times']]
    rep = json.loads((WORK / 'stage_report.json').read_text(encoding='utf-8'))
    nstate = len(times)
    kpos = [int(round(t / times[-1] * SPAN)) for t in times]
    assert kpos[0] == 0 and kpos[-1] == SPAN and all(b > c_ for b, c_ in zip(kpos[1:], kpos[:-1])), 'film positions must increase'
    ip = int(np.argmin([abs(t - 2.5) for t in times]))
    films = {}
    for view, key, size in (('edge', 'col_edge', (1536, 768)), ('face', 'col_face', (768, 768))):
        s = time.perf_counter()
        cols = c[key]; ox, oy = (W - size[0]) // 2, 150
        rgb = lambda i: color(cols[i].astype(np.float64))
        # poster: the state nearest 2.5 t_cc, picture only
        pimg = Image.fromarray(rgb(ip)).resize((768, 384) if view == 'edge' else (384, 384),
                                               Image.Resampling.NEAREST if N <= 64 else Image.Resampling.LANCZOS)
        pp = WORK / ('poster-%s.jpg' % view); pimg.save(pp, quality=92); assert not_zero_filled(pp)
        bg = film_background(view, size, ox, oy)
        dest = WORK / ('film-%s.mp4' % view); tmp = dest.with_name(dest.name + '.tmp.mp4')
        crf = 18
        while True:
            cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', 'pipe:0',
                   '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-threads', '4', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                   '-movflags', '+faststart', str(tmp)]
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            nframes = 0
            def put(img, t):
                nonlocal nframes
                fr = bg.copy(); fr.paste(Image.fromarray(np.clip(img + .5, 0, 255).astype('uint8')), (ox, oy))
                readout(ImageDraw.Draw(fr), t)                                   # text drawn after the cross fade
                p.stdin.write(fr.tobytes()); nframes += 1
            cur = big_image(rgb(0), size)
            for i in range(nstate - 1):
                nxt = big_image(rgb(i + 1), size)
                span = kpos[i + 1] - kpos[i]
                for k in range(span):
                    w = k / span
                    put(cur if k == 0 else cur * (1 - w) + nxt * w, times[i] * (1 - w) + times[i + 1] * w)
                cur = nxt
            for k in range(HOLD + 1): put(cur, times[-1])
            p.stdin.close(); assert p.wait() == 0
            if os.path.getsize(tmp) < 25 * 1000 * 1000: break
            crf += 2; log('film over 25 MB, crf ->', crf)
        os.replace(tmp, dest); assert not_zero_filled(dest)
        films[view] = dict(bytes=os.path.getsize(dest), frames=nframes, crf=crf, seconds=round(time.perf_counter() - s, 1),
                           duration_s=nframes / FPS, upscale='nearest' if size[0] / cols.shape[2] >= 12 else 'lanczos')
        log('film %s: %d frames, %.1f MB, %.0f s' % (view, nframes, os.path.getsize(dest) / 1e6, time.perf_counter() - s))
    rep['film'] = dict(fps=FPS, frames_for_0_to_end=SPAN, hold_frames_at_end=HOLD, state_frame_positions=kpos, poster_state=ip,
                       poster_time_tcc=times[ip], text_font=FONT, label=LABEL, views=films, wall_seconds=round(time.perf_counter() - t0, 1),
                       method='every saved state shown unblended at frame round(t / t_end x 1200); frames in between are linear cross fades of the two '
                              'neighbouring states (colour mapped first), with the time readout interpolated linearly between their times')
    write_json(WORK / 'stage_report.json', rep, compact=False)

# ------------------------------------------------------------------ phase 3: verify every file, look frames, move to the staging folder
EXPECTED = ['edge.png', 'face.png', 'poster-edge.jpg', 'poster-face.jpg', 'film-edge.mp4', 'film-face.mp4', 'entry.json', 'entry3d.json', 'stage_report.json', '3d']

def ffprobe(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                          'stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames:format=duration,size',
                          '-of', 'json', str(p)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j['streams'][0]
    return dict(codec=s['codec_name'], profile=s.get('profile'), width=s['width'], height=s['height'], pix_fmt=s['pix_fmt'],
                r_frame_rate=s['r_frame_rate'], avg_frame_rate=s['avg_frame_rate'], frames=int(s['nb_read_frames']),
                duration=float(j['format']['duration']), bytes=int(j['format']['size']))

def verify_folder(root, rep):
    names = sorted(os.listdir(root))
    assert names == sorted(EXPECTED), ('folder content', names)
    res = {}
    entry = json.loads((root / 'entry.json').read_text(encoding='utf-8')); e3 = json.loads((root / 'entry3d.json').read_text(encoding='utf-8'))
    n = len(entry['frames'])
    assert n == len(entry['times']) == len(entry['dense']) == e3['frames'] and 'base' not in entry and 'base' not in e3
    for view, w in (('edge', 256), ('face', 128)):
        with Image.open(root / (view + '.png')) as im:
            im.load(); assert im.size == (w, 128 * n) and im.mode == 'RGB'
        with Image.open(root / ('poster-%s.jpg' % view)) as im:
            im.load(); assert im.size == ((768, 384) if view == 'edge' else (384, 384))
        pr = ffprobe(root / ('film-%s.mp4' % view))
        assert pr['codec'] == 'h264' and pr['pix_fmt'] == 'yuv420p' and (pr['width'], pr['height']) == (1920, 1080) and pr['r_frame_rate'] == '60/1', pr
        assert pr['bytes'] < 25 * 1000 * 1000 and 19 < pr['duration'] < 23, pr
        assert pr['frames'] == rep['film']['views'][view]['frames'], (pr, rep['film']['views'][view])
        res['film_' + view] = pr
    idx = json.loads((root / '3d/index.json').read_text(encoding='utf-8'))
    assert idx['frames'] == ['f%03d.bin' % i for i in range(n)] and len(idx['times']) == n and idx['times'] == entry['times']
    tri = []
    for i, f in enumerate(idx['frames']):
        blob = (root / '3d' / f).read_bytes(); ns, nt = decode_mesh(blob)
        assert ns == idx['shell_counts'][i] and nt == idx['tris'][i]; tri.append(nt)
    assert sorted(os.listdir(root / '3d')) == sorted(idx['frames'] + ['index.json'])
    zero = [str(p) for p in root.rglob('*') if p.is_file() and not not_zero_filled(p)]
    assert not zero, ('zero filled', zero)
    res['files'] = sum(1 for p in root.rglob('*') if p.is_file()); res['bytes'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    res['mesh_frames_decoded'] = len(tri)
    # visible text: no dash punctuation, no internal names
    text = ' '.join([entry['label'], entry['note'], e3['label'], e3['note'], entry['status'], entry.get('boundary', '')])
    assert not re.search('[\u2012\u2013\u2014\u2015]|--| - ', text), text
    assert not re.search(r'(?i)ultra|hires|sharp13|full_0|\.athdf|\.phdf', text), text
    return res

def look_frames(root):
    out = NOTES / 'look' / RID; out.mkdir(parents=True, exist_ok=True)
    rep = json.loads((root / 'stage_report.json').read_text(encoding='utf-8'))
    for view in ('edge', 'face'):
        nf = rep['film']['views'][view]['frames']
        picks = [0, nf // 4 + 7, nf // 2 + 3, nf - 1]
        tiles = []
        for k in picks:
            png = out / ('%s_%04d.png' % (view, k))
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(root / ('film-%s.mp4' % view)), '-vf', 'select=eq(n\\,%d)' % k,
                            '-frames:v', '1', str(png)], check=True)
            tiles.append(Image.open(png).convert('RGB').resize((960, 540), Image.Resampling.LANCZOS))
        sheet = Image.new('RGB', (1920, 1080))
        for j, im in enumerate(tiles): sheet.paste(im, ((j % 2) * 960, (j // 2) * 540))
        sheet.save(out / ('sheet_%s.png' % view))
    # sprite rows of every tenth state, edge on and face on side by side
    e = Image.open(root / 'edge.png').convert('RGB'); f = Image.open(root / 'face.png').convert('RGB')
    n = e.size[1] // 128; picks = list(range(0, n, 10)) + ([n - 1] if (n - 1) % 10 else [])
    sh = Image.new('RGB', (2 * (256 + 128 + 8), 128 * ((len(picks) + 1) // 2)), (40, 40, 40))
    for j, i in enumerate(picks):
        x = (j % 2) * (256 + 128 + 8); y = (j // 2) * 128
        sh.paste(e.crop((0, 128 * i, 256, 128 * i + 128)), (x, y)); sh.paste(f.crop((0, 128 * i, 128, 128 * i + 128)), (x + 256 + 2, y))
    sh.save(out / 'sprites_every_tenth.png')
    Image.open(root / 'poster-edge.jpg').save(out / 'poster-edge.png'); Image.open(root / 'poster-face.jpg').save(out / 'poster-face.png')

def phase_finish():
    t0 = time.perf_counter()
    rep = json.loads((WORK / 'stage_report.json').read_text(encoding='utf-8'))
    res = verify_folder(WORK, rep)
    look_frames(WORK)
    rep['verification'] = res
    if rep['limited_test']:
        write_json(WORK / 'stage_report.json', rep, compact=False)
        log('limited test: verified in the work folder, not moved'); return
    if FINAL.exists():
        raise SystemExit('staging folder exists already: %s (remove it by hand first)' % FINAL)
    STAGING.mkdir(exist_ok=True)
    rep['staged_to'] = str(FINAL).replace('/mnt/d/', 'D:/')
    rep['stages']['finish_seconds'] = round(time.perf_counter() - t0, 1)
    rep['stages']['total_wall_seconds'] = round(rep['stages']['read_phase_wall_seconds'] + rep['film']['wall_seconds'] + rep['stages']['finish_seconds'], 1)
    write_json(WORK / 'stage_report.json', rep, compact=False)
    before = {str(p.relative_to(WORK)): (p.stat().st_size, sha256_file(p)) for p in WORK.rglob('*') if p.is_file()}
    shutil.move(str(WORK), str(FINAL))
    after = {str(p.relative_to(FINAL)): (p.stat().st_size, sha256_file(p)) for p in FINAL.rglob('*') if p.is_file()}
    assert before == after, 'files changed during the move'
    res2 = verify_folder(FINAL, rep)
    log('staged to', FINAL, '%d files, %.1f MB' % (res2['files'], res2['bytes'] / 1e6))

if a.phase in ('all', 'read'): phase_read()
if a.phase in ('all', 'film'): phase_film()
if a.phase in ('all', 'finish'): phase_finish()
if a.phase == 'look':
    _r = verify_folder(WORK, json.loads((WORK / 'stage_report.json').read_text(encoding='utf-8'))); look_frames(WORK)
    log('look: verified in the work folder', json.dumps({k: v for k, v in _r.items() if not k.startswith('film')}),
        json.dumps({k: (v['frames'], v['bytes'], v['duration']) for k, v in _r.items() if k.startswith('film')}))
