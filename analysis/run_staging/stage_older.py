"""Restage the fifteen older Cloud Studio runs with ALL their saved states (2026-11-23), under their existing ids.

The site showed only 11 saved states of each of these runs (assets/recent/catalog.json of the site working copy, which
also holds the full dense fraction history of each run). This tool reads every saved state of a run once, read only,
confirms that it is the run the site shows (times and dense fraction reproduce the site's history at every saved
time, and masses and code times reproduce the run's own receipt), and writes the folder of the data contract of
2026-11-22:

  edge.png, face.png                 sprite sheets, one 128 px row per saved state (256 / 128 px wide)
  poster-edge.jpg, poster-face.jpg   the state nearest 2.5 t_cc, picture only (768 x 384, 384 x 384)
  film-edge.mp4, film-face.mp4       made with the film code of stage_run2.py for now (redrawn later by the shared
                                     renderer from the cache kept in <notes>/cache/<id>.npz)
  3d/index.json, 3d/fNNN.bin         two density surfaces (0.15 and 0.6 of the initial cloud density), mesh step 2
  entry.json, entry3d.json           catalog entries (no "base", no "group")
  stage_report.json                  what was read, the checks and their results, sizes, wall time

Run folders and receipts are those of the site's analysis/recent_gallery_export.py (and add_plm_display.py for the
HLLC/PLM run). Readers are lifted unchanged from the two staging tools: stage_grid.py (Athena++, AthenaPK, Enzo,
Enzo-E) and stage_run2.py (GIZMO particles); the PNG writer, colour table and mesh encoder come from the published
site checkout, as in both tools; the film code (layout, readout, schedule, encoder call) is lifted from stage_run2.py.

  python stage_older.py --id enzo-10 --phase read     read every state once, check, write the work folder and the cache
  python stage_older.py --id enzo-10 --phase film     posters and films from the cache
  python stage_older.py --id enzo-10 --phase check    verify every file in the work folder and extract look frames
  python stage_older.py --id enzo-10 --phase finish   verify again and move the work folder to the staging folder
  --pick 0,40,41,100 (test only): read just these states; nothing can be moved to the staging folder
"""
import argparse, ast, glob, gzip, hashlib, json, math, os, re, resource, shutil, struct, subprocess, sys, time, zlib
from pathlib import Path
for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(k, '2')
import numpy as np, h5py
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
from PIL import Image, ImageDraw, ImageFont

NOTES = Path('/mnt/d/CloudCrushing/run_simple/analysis_20261122/studio_impl/stage_older')
STAGING = Path('/mnt/d/CloudStudio-runs-staging')
REPO = Path('/mnt/d/CloudStudio-refresh-20261110')     # published site checkout, read only (colour table, PNG writer, mesh encoder)
SITE = Path('/mnt/d/CloudStudio-update-20261122')      # site working copy, read only (current catalog entries of these runs)
TOOLS = Path('/mnt/d/CloudCrushing/run_simple/analysis_20261122/studio_impl')
GRID_TOOL = TOOLS / 'stage_grid' / 'stage_grid.py'
OTHER_TOOL = TOOLS / 'stage_other' / 'stage_run2.py'
B = Path('/mnt/d/CloudCrushing/meeting_20261010_v1')
NR = Path('/mnt/d/CloudCrushing/native_runs')

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def lin(p):
    s = str(p).replace('\\', '/')
    return Path(re.sub(r'^[Dd]:/', '/mnt/d/', s))

# ------------------------------------------------------------------ the fifteen runs
GAMMA = 5 / 3
VW_STD = 2 * math.sqrt(GAMMA)      # rho_w = 1, P_w = 1, Mach 2 (Enzo, Enzo-E, Athena++, GIZMO)
VW_APK = 1.0                       # older AthenaPK runs: rho_w = 1, v_w = 1, P_w = 0.15 in code units (R = 100 pc, 1e-27 g/cm3, 305.8 km/s)
OPEN = 'Wind enters through the upstream face and leaves through the downstream face.'
ENZOE = 'Wind enters through the upstream face. This run has no passive tracer, so cloud gas is followed by its density.'
RUNS = {}
for chi in (10, 1000):
    root = NR / ('enzo_L5_chi%d_20261010_v1/full_sharp13_v1' % chi)
    RUNS['enzo-%d' % chi] = dict(kind='enzo', code='Enzo', chi=chi, root=root, note=OPEN, qual='', vw=VW_STD,
                                 receipt=(B / 'enzo_L5_chi1000_analysis_v2/actual.json') if chi == 1000 else root / 'native_completion.json')
for chi in (10, 1000):
    root = NR / ('enzoe_L5_chi%d_20261010_v1/full_sharp13' % chi)
    RUNS['enzoe-%d' % chi] = dict(kind='enzoe', code='Enzo-E', chi=chi, root=root, note=ENZOE, qual='', vw=VW_STD,
                                  receipt=root / 'evolution_series.json' if chi == 1000 else root.parent / 'full_validation_v1/evolution_series.json')
for chi, root in ((10, NR / 'athpp_L5_chi10_20261010_v1/full_sharp13_v11'), (1000, NR / 'athpp_L5_chi1000_20261028_v1/full_sharp13_v23')):
    RUNS['athpp-%d' % chi] = dict(kind='athpp', code='Athena++', chi=chi, root=root, note=OPEN, qual='', vw=VW_STD, receipt=root / 'native_completion.json')
APK = [('apk-hlle-off', 100, 'hlle', 'plm', False, B / 'cooling_repair_source_v1/tracer_global_pair_20261026_v1/off', NR / 'tracer_pair_20261026_v1/global_v1/off'),
       ('apk-hlle-on', 100, 'hlle', 'plm', True, B / 'cooling_repair_source_v1/tracer_global_pair_20261026_v1/on', NR / 'tracer_pair_20261026_v1/global_v1/on'),
       ('apk-hlle-10', 10, 'hlle', 'plm', False, B / 'apk_L5_chi10_queue_20261026_v2/chi10', None),
       ('apk-hllc-off', 100, 'hllc', 'ppm', False, B / 'apk_hllc_handoff_20261027_v1/off', None),
       ('apk-hllc-on', 100, 'hllc', 'ppm', True, B / 'tracer_proactive_repair_20261027_v5/on', None),
       ('apk-hllc-10', 10, 'hllc', 'ppm', False, B / 'chi10_followon_20261028_v1/validate_chi10', NR / 'tracer_endpoint_20261027_v1/chi10/run/chi10')]
for rid, chi, riemann, recon, cool, ctl, raw in APK:
    RUNS[rid] = dict(kind='apk', code='AthenaPK', chi=chi, riemann=riemann, recon=recon, cooling_on=cool, receipt=ctl / 'validation_result.json',
                     root=raw if raw is not None else ('config', ctl / 'config.json'), vw=VW_APK)
RUNS['apk-hllc-plm-off'] = dict(kind='apk', code='AthenaPK', chi=100, riemann='hllc', recon='plm', cooling_on=False, vw=VW_APK,
                                integration=B / 'chi10_followon_20261028_v1/plm_v13_validated_result_integration.json')
for rid, r in RUNS.items():
    if r['kind'] == 'apk':
        sr = '%s/%s' % (r['riemann'].upper(), r['recon'].upper())
        r['qual'] = (' · cooling %s · %s' % ('on' if r['cooling_on'] else 'off', sr)) if r['chi'] == 100 else ' · ' + sr
        r['note'] = 'AthenaPK with the %s solver and %s reconstruction.' % (r['riemann'].upper(), r['recon'].upper()) + (' Tabulated radiative cooling is on.' if r['cooling_on'] else '')
GIZ = 'Meshless finite %s method in a box that is periodic on all faces. The wind starts with a smooth tanh velocity profile around the cloud.'
RUNS['mfm-historical'] = dict(kind='gizmo', code='GIZMO MFM', chi=100, vw=VW_STD, qual=' · smooth velocity profile', note=GIZ % 'mass',
                              root=NR / 'sensitivity_20260907/gizmo_mfm_L5_20260924_v1/gizmo_mfm_L5_full_1_repair20261022_v4/output',
                              receipt=Path('/mnt/d/CloudCrushing/local_queue_20261023_v3/validate_full1/validation.json'))
RUNS['mfv-historical'] = dict(kind='gizmo', code='GIZMO MFV', chi=100, vw=VW_STD, qual=' · smooth velocity profile', note=GIZ % 'volume',
                              root=NR / 'sensitivity_20260907/gizmo_mfv_L5_20261023_v1/historical3_resume/output',
                              receipt=Path('/mnt/d/CloudCrushing/mfv_L5_queue_20261023_v1/historical_v3/validate_full/validation.json'))
ORDER = ['enzo-10', 'enzo-1000', 'enzoe-10', 'enzoe-1000', 'athpp-10', 'athpp-1000', 'apk-hlle-off', 'apk-hlle-on', 'apk-hlle-10',
         'apk-hllc-off', 'apk-hllc-on', 'apk-hllc-10', 'apk-hllc-plm-off', 'mfm-historical', 'mfv-historical']
assert sorted(ORDER) == sorted(RUNS)

ap = argparse.ArgumentParser()
ap.add_argument('--id', required=True, choices=ORDER)
ap.add_argument('--phase', required=True, choices=['read', 'film', 'check', 'finish'])
ap.add_argument('--pick', default='', help='test only: comma separated state indices to read')
a = ap.parse_args()
RID = a.id; RUN = dict(RUNS[RID]); KIND = RUN['kind']
CHI = RUN['chi']; CODE = RUN['code']; LEVEL = 5; N = 128; DX = 10 / N
VW = RUN['vw']; TCC = math.sqrt(CHI) / VW                 # R = 1 in every run
THRESH = CHI / 3                                          # wind density is 1 in every run
MESH_STEP = 2
MODE = 'wrap' if KIND == 'gizmo' else 'nearest'          # display smoothing wraps for the periodic particle runs (as stage_run2.py)
LABEL = '%s · χ %d · level %d%s' % (CODE, CHI, LEVEL, RUN['qual'])
NOTE = RUN['note']
BOUNDARY = 'periodic on all faces' if KIND == 'gizmo' else 'inflow and outflow'
COOLING = 'tabular' if RUN.get('cooling_on') else 'none'
PICK = [int(x) for x in a.pick.split(',')] if a.pick else []
TAG = RID + ('_test' if PICK else '')
WORK = NOTES / 'work' / TAG
CACHE_FILE = NOTES / 'cache' / (TAG + '.npz')
FINAL = STAGING / RID

def log(*x):
    print(time.strftime('%H:%M:%S'), RID, *x, flush=True)

# ------------------------------------------------------------------ lifted code
def lift(path, names):
    src = Path(path).read_text(encoding='utf-8'); out = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            out[node.name] = ast.get_source_segment(src, node)
        elif isinstance(node, ast.Assign):
            tn = {n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            if tn and tn <= set(names):
                out[','.join(sorted(tn))] = ast.get_source_segment(src, node)
    found = {n for k in out for n in k.split(',')}
    assert found >= set(names), (str(path), sorted(set(names) - found))
    return out

L = dict(np=np, h5py=h5py, os=os, re=re, glob=glob, math=math, json=json, struct=struct, gzip=gzip, zlib=zlib, subprocess=subprocess, time=time,
         hashlib=hashlib, Path=Path, Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont, gaussian_filter=gaussian_filter, marching_cubes=marching_cubes,
         N=N, DX=DX, CHI=CHI, TCC=TCC)
GRID_NAMES = ['sha256_file', 'lsum', 'not_zero_filled', 'write_bytes', 'write_json', 'color', 'to_sprite', 'check_box', 'read_athpp', 'read_apk',
              'parse_enzo_hierarchy', 'read_enzo', 'read_enzoe', 'decode_mesh']
OTHER_NAMES = ['read_particles', 'font', 'film_layout', 'background', 'Readout', 'schedule', 'make_film',
               'BG', 'INK', 'MUTED', 'ACCENT', 'LINE', 'W', 'H', 'FPS', 'FRAMES_PER_TCC', 'HOLD_START', 'HOLD_END', 'FONTS']
LIFTED = dict(grid=lift(GRID_TOOL, GRID_NAMES), other=lift(OTHER_TOOL, OTHER_NAMES),
              site=dict(**lift(REPO / 'analysis/recent_gallery_export.py', ['png']), **lift(REPO / 'analysis/recent_3d_export.py', ['encode'])))
for code in list(LIFTED['grid'].values()) + list(LIFTED['other'].values()) + [LIFTED['site']['png']]:
    exec(code, L)
L['LUT'] = LUT = np.array(load(REPO / 'assets/recent/catalog.json')['colormap'])
assert LUT.shape == (256, 3)
_enc = LIFTED['site']['encode']
assert "step_size=2" in _enc and "mode='wrap' if periodic else 'nearest'" in _enc
_enc = _enc.replace("mode='wrap' if periodic else 'nearest'", 'mode=periodic')     # third argument carries the filter mode (as stage_grid.py)
ENCODERS = []
for step in (MESH_STEP, 1):
    ns = dict(L); exec(_enc.replace('step_size=2', 'step_size=%d' % step), ns); ENCODERS.append((step, ns['encode']))
color, to_sprite, decode_mesh, lsum = L['color'], L['to_sprite'], L['decode_mesh'], L['lsum']
write_bytes, write_json, not_zero_filled, sha256_file, png_site = L['write_bytes'], L['write_json'], L['not_zero_filled'], L['sha256_file'], L['png']
READERS = dict(athpp=L['read_athpp'], apk=L['read_apk'], enzo=L['read_enzo'], enzoe=L['read_enzoe'])

def safe_encode(rho, fallbacks, i):
    for k, (step, enc) in enumerate(ENCODERS):
        try:
            out = enc(rho, CHI, MODE)
            if k: fallbacks.append(dict(state=i, used_step=step))
            return out
        except RuntimeError:
            continue
    fallbacks.append(dict(state=i, used_step=None, empty=True))
    return gzip.compress(struct.pack('<B', 0), compresslevel=6, mtime=0), 0, 0

def zero_pages(p):
    """Every 4 KiB page of the file (and the tail) must hold a nonzero byte: none of the formats written here has a
    page of zeros, and the PC's fault zero fills freshly written files."""
    b = np.fromfile(str(p), dtype=np.uint8); n = b.size
    if n == 0: return ['empty file']
    k = n // 4096; bad = []
    if k:
        bad = [int(x) for x in np.nonzero(~b[:k * 4096].reshape(k, 4096).any(axis=1))[0]]
    if n % 4096 and not b[k * 4096:].any(): bad.append(k)
    return bad

# ------------------------------------------------------------------ site entry and receipt
def site_entry():
    p = SITE / 'assets/recent/catalog.json'
    e = [r for r in load(p)['runs'] if r['id'] == RID]
    assert len(e) == 1, ('site entry', RID, len(e))
    return e[0], dict(file=str(p), sha256=sha256_file(p))

def receipt_rows():
    if 'integration' in RUN:
        integ = load(RUN['integration'])
        assert integ['status'] == 'ACCEPTED_BOUNDED_MATCHED_L5'
        rec = lin(integ['validation_control']) / 'validation_result.json'
        assert sha256_file(rec) == integ['validation_result_sha256'], 'receipt changed since the site export'
        RUN['root'] = lin(integ['raw'])
    else:
        rec = RUN['receipt']
    j = load(rec)
    rows = next(j[k] for k in ('series', 'outputs', 'snapshots') if isinstance(j.get(k), list))
    if isinstance(RUN.get('root'), tuple):
        RUN['root'] = lin(load(RUN['root'][1])['target_windows'])
    return j, rows, dict(file=str(rec), sha256=sha256_file(rec), rows=len(rows))

def rmass(row):
    return float(row['total_mass'] if 'total_mass' in row else row['mass'])

# ------------------------------------------------------------------ saved states of a run, each used once
def apk_deck(path):
    with h5py.File(path, 'r') as h:
        txt = h['Input'].attrs['File']
    txt = txt.decode() if isinstance(txt, bytes) else str(txt)
    out = {}; sec = None
    for line in txt.splitlines():
        line = line.split('#')[0].strip()
        if line.startswith('<'): sec = line.strip('<>'); continue
        if '=' in line:
            k, v = [x.strip() for x in line.split('=', 1)]; out['%s/%s' % (sec, k)] = v
    return out

def state_list(j, rows):
    root = Path(RUN['root']); notused = []
    if KIND == 'enzo':
        dumps = sorted(n for n in os.listdir(root) if re.fullmatch(r'DD\d{4}', n))
        # DD0101 is a second dump of the final state, written at the stop time just after DD0100: use each state once
        assert len(dumps) == 102 and dumps[-1] == 'DD0101', dumps[-3:]
        assert [r['base'] for r in rows] == ['%s/CW_%s' % (n, n[2:]) for n in dumps], 'receipt rows name other dumps'
        st = [dict(name=n, files=[str(root / n)], row=rows[i]) for i, n in enumerate(dumps[:101])]
        notused = ['DD0101 (second dump of the final state)']
    elif KIND == 'enzoe':
        fs = glob.glob(str(root) + '/ic-*-p*.h5')
        counts = sorted({int(re.search(r'ic-(\d+)-p', f).group(1)) for f in fs}); procs = sorted({int(re.search(r'-p(\d+)\.h5$', f).group(1)) for f in fs})
        assert counts == list(range(101)) and procs == list(range(8)) and len(fs) == 808, (len(fs), counts[:2], procs)
        assert len(rows) == 101
        st = [dict(name='ic-%03d' % c, files=['%s/ic-%03d-p%02d.h5' % (root, c, p) for p in procs], row=rows[c]) for c in counts]
    elif KIND == 'athpp':
        fs = sorted(glob.glob(str(root) + '/*.out2.*.athdf'))
        assert len(fs) == 101 and len(rows) == 101 and [os.path.basename(f) for f in fs] == [r['snapshot'] for r in rows], 'receipt rows name other files'
        st = [dict(name=os.path.basename(f), files=[f], row=rows[i]) for i, f in enumerate(fs)]
    elif KIND == 'apk':
        seg_root = {None: root}
        if j.get('retained_prefix_root'): seg_root['prefix'] = lin(j['retained_prefix_root'])
        if j.get('resume_root'): seg_root['resume'] = lin(j['resume_root'])
        if 'prefix' in seg_root: assert seg_root['prefix'] == root, (seg_root, root)
        assert len(rows) == 101
        st = []
        for i, r in enumerate(rows):
            assert r.get('index', i) == i
            p = seg_root[r.get('segment')] / r['file']
            assert p.is_file() and os.path.getsize(p) == r['bytes'], ('file size differs from the receipt', str(p))
            st.append(dict(name=('%s/' % r['segment'] if r.get('segment') else '') + r['file'], files=[str(p)], row=r))
        used = {s['files'][0] for s in st}
        for d in sorted({str(v) for v in seg_root.values()}):
            notused += sorted(os.path.relpath(f, str(root.parent)) for f in glob.glob(d + '/parthenon.prim.*.phdf') if f not in used)
        decks = [apk_deck(st[0]['files'][0]), apk_deck(st[-1]['files'][0])]
        for dk in decks:
            assert dk['hydro/riemann'] == RUN['riemann'] and dk['hydro/reconstruction'] == RUN['recon'], (dk['hydro/riemann'], dk['hydro/reconstruction'])
            assert dk['cooling/enable_cooling'] == ('tabular' if RUN['cooling_on'] else 'none'), dk['cooling/enable_cooling']
            vw = float(dk['problem/cloud/v_wind_cgs']) * float(dk['units/code_time_cgs']) / float(dk['units/code_length_cgs'])
            rw = float(dk['problem/cloud/rho_wind_cgs']) * float(dk['units/code_length_cgs']) ** 3 / float(dk['units/code_mass_cgs'])
            r0 = float(dk['problem/cloud/r0_cgs']) / float(dk['units/code_length_cgs'])
            chi = float(dk['problem/cloud/rho_cloud_cgs']) / float(dk['problem/cloud/rho_wind_cgs'])
            assert abs(vw - VW) < 1e-9 and abs(rw - 1) < 1e-9 and abs(r0 - 1) < 1e-12 and abs(chi / CHI - 1) < 1e-12, (vw, rw, r0, chi)
        RUN['deck'] = {k: decks[0][k] for k in ('hydro/riemann', 'hydro/reconstruction', 'hydro/first_order_flux_correct', 'cooling/enable_cooling',
                                                'units/code_length_cgs', 'units/code_mass_cgs', 'units/code_time_cgs', 'problem/cloud/rho_wind_cgs',
                                                'problem/cloud/rho_cloud_cgs', 'problem/cloud/v_wind_cgs', 'problem/cloud/T_wind_cgs', 'problem/cloud/cloud_steepness',
                                                'problem/cloud/rv_scale')}
        RUN['deck']['wind_speed_code_units'] = vw
    elif KIND == 'gizmo':
        assert len(rows) == 101
        prov = j.get('resume_provenance')
        st = []
        for i, r in enumerate(rows):
            assert r['index'] == i
            d = lin(prov['source']) / 'output' if (prov and i < prov['snapshot_next']) else root
            p = d / ('snapshot_%03d.hdf5' % i)
            assert p.is_file(), str(p)
            if 'bytes' in r: assert os.path.getsize(p) == r['bytes'], ('file size differs from the receipt', str(p))
            st.append(dict(name=os.path.relpath(p, str(root.parent.parent)), files=[str(p)], row=r))
        if prov:
            src = lin(prov['source']) / 'output'
            notused = sorted(os.path.relpath(f, str(root.parent.parent)) for f in glob.glob(str(src) + '/snapshot_*.hdf5')
                             if int(re.search(r'snapshot_(\d+)', f).group(1)) >= prov['snapshot_next'])
    else:
        raise ValueError(KIND)
    where = dict(root=str(root), states=len(st), not_used=notused)
    if KIND == 'apk' and len({str(Path(s['files'][0]).parent) for s in st}) > 1:
        where['segments'] = {k: str(v) for k, v in dict(prefix=lin(j['retained_prefix_root']), resume=lin(j['resume_root'])).items()}
    if KIND == 'gizmo' and j.get('resume_provenance'):
        where['resume_provenance'] = j['resume_provenance']
    return st, where

# ------------------------------------------------------------------ readers for the particle runs
def read_gizmo(path):
    r = L['read_particles'](Path(path))          # stage_run2.read_particles: masses binned onto the level 5 lattice, dense from particle density
    return r

def gizmo_velocity(path, rho_cut=1.5):
    """State 0 only: the wind speed far from the cloud and the share of gas moving at an intermediate speed, which is
    zero for the sharp velocity profile and not zero for the smooth tanh profile."""
    with h5py.File(path, 'r') as h:
        v = h['PartType0/Velocities'][:]; d = h['PartType0/Density'][:]
    vx = v[:, 0].astype(np.float64) / VW
    wind = d < rho_cut
    mid = (vx > .02) & (vx < .98)
    return dict(median_vx_over_vw_wind=float(np.median(vx[wind])), median_vy_over_vw_wind=float(np.median(v[wind, 1]) / VW),
                median_vz_over_vw_wind=float(np.median(v[wind, 2]) / VW), particles=int(len(vx)),
                share_at_intermediate_speed=float(mid.mean()), share_at_rest=float((np.abs(vx) <= .02).mean()),
                vx_over_vw_quantiles_1_10_50_90_99=[float(x) for x in np.percentile(vx, [1, 10, 50, 90, 99])])

# ------------------------------------------------------------------ phase read
def rel(x, y):
    return 0.0 if x == y else abs(x - y) / max(abs(y), 1e-300)

def phase_read():
    t0 = time.perf_counter()
    site, site_src = site_entry()
    j, rows_rec, rec_src = receipt_rows()
    states, where = state_list(j, rows_rec)
    assert len(states) == 101
    full = not PICK
    sel = PICK if PICK else list(range(101))
    if WORK.exists(): shutil.rmtree(WORK)
    (WORK / '3d').mkdir(parents=True)
    CACHE_FILE.parent.mkdir(exist_ok=True)
    rows = []; rgb_e = []; rgb_f = []; col_e = []; col_f = []; fallbacks = []; read_s = mesh_s = 0.0
    init_check = None; vel_profile = None; dense0 = None
    for k, i in enumerate(sel):
        st = states[i]; s = time.perf_counter()
        if KIND == 'gizmo':
            r = read_gizmo(st['files'][0])
            rho = r['rho']; t = r['t_code']; mass = r['total']; dense = r['dense']; extra = dict(r['extra'])
            if i == 0: vel_profile = gizmo_velocity(st['files'][0])
        else:
            fld, t, extra = READERS[KIND](st['files'], i == 0)
            rho = fld['rho']
        read_s += time.perf_counter() - s
        assert rho.shape == (N, N, 2 * N), rho.shape
        assert np.isfinite(rho).all(), ('finite', st['name'])
        if KIND == 'gizmo':
            assert rho.min() >= 0 and mass > 0 and np.isfinite(mass) and np.isfinite(dense), ('non negative', st['name'])
        else:
            assert rho.min() > 0, ('positive', st['name'])
            mass = lsum(rho) * DX ** 3
            dense = lsum(rho[rho > THRESH]) * DX ** 3
        if i == 0 and KIND != 'gizmo':
            wind = rho < 1.5
            init_check = dict(median_vx_over_vw=float(np.median(fld['vx'][wind]) / VW), median_vy_over_vw=float(np.median(fld['vy'][wind]) / VW),
                              median_vz_over_vw=float(np.median(fld['vz'][wind]) / VW), max_rho_over_chi=float(rho.max() / CHI), min_rho=float(rho.min()),
                              max_density_at_centre=bool(np.unravel_index(np.argmax(rho), rho.shape)[2] in (int(3 / DX) - 1, int(3 / DX))), wind_speed=VW)
            assert abs(init_check['median_vx_over_vw'] - 1) < 1e-6 and abs(init_check['median_vy_over_vw']) < 1e-6 and abs(init_check['median_vz_over_vw']) < 1e-6, init_check
            assert abs(init_check['max_rho_over_chi'] - 1) < 1e-3 and init_check['max_density_at_centre'], init_check
            del fld
        if i == 0 and KIND == 'gizmo':
            init_check = dict(max_lattice_density_over_chi=float(rho.max() / CHI), wind_speed=VW, **vel_profile)
            assert abs(vel_profile['median_vx_over_vw_wind'] - 1) < 1e-4 and abs(vel_profile['median_vy_over_vw_wind']) < 1e-4 and abs(vel_profile['median_vz_over_vw_wind']) < 1e-4, vel_profile
            # the same measure on snapshot 0 of the sharp runs (scripts/p05_sharp_velocity_reference.txt): MFV 0.000024, MFM 0.000606
            init_check['sharp_reference_share_at_intermediate_speed'] = dict(mfv_sharp=0.000024, mfm_sharp=0.000606)
            assert vel_profile['share_at_intermediate_speed'] > 1e-3, ('the label says smooth velocity profile', vel_profile)
        y_asym = float(np.abs(rho - rho[:, ::-1, :]).max()); z_asym = float(np.abs(rho - rho[::-1, :, :]).max())
        ce = rho.sum(axis=0) * DX / CHI; cf = rho.sum(axis=2) * DX / CHI
        tol = 1e-9 if KIND == 'gizmo' else 1e-10
        assert abs(ce.sum() * DX ** 2 * CHI / mass - 1) < tol and abs(cf.sum() * DX ** 2 * CHI / mass - 1) < tol
        rgb_e.append(color(to_sprite(ce))); rgb_f.append(color(to_sprite(cf)))
        col_e.append(ce.astype(np.float32)); col_f.append(cf.astype(np.float32))
        s = time.perf_counter()
        blob, ntri, nsh = safe_encode(rho, fallbacks, i)
        dn, dt_ = decode_mesh(blob); assert (dn, dt_) == (nsh, ntri)
        write_bytes(WORK / '3d' / ('f%03d.bin' % k), blob)
        mesh_s += time.perf_counter() - s
        del rho
        t_tcc = t / TCC
        if dense0 is None: dense0 = dense
        fd = dense / dense0
        rr = st['row']
        row = dict(state=i, name=st['name'], time_code=t, t_tcc=t_tcc, total_mass=mass, dense_mass=dense, dense_fraction=fd, y_asym=y_asym, z_asym=z_asym,
                   mesh_bytes=len(blob), triangles=ntri, shells=nsh,
                   receipt_rel_diff=dict(time_code=rel(t, float(rr['time_code'])), total_mass=rel(mass, rmass(rr)), dense_mass=rel(dense, float(rr['dense_mass']))),
                   site_abs_diff=dict(time=abs(t_tcc - site['times'][i]), dense=abs(fd - site['dense'][i])),
                   **{k_: v for k_, v in extra.items() if v is not None})
        # stop at the first state that is not the run the site shows
        assert row['receipt_rel_diff']['time_code'] < 1e-12, ('time differs from the receipt', i, t, rr['time_code'])
        assert row['receipt_rel_diff']['total_mass'] < 1e-12, ('total mass differs from the receipt', i, mass, rmass(rr))
        assert row['receipt_rel_diff']['dense_mass'] < 1e-12, ('dense mass differs from the receipt', i, dense, rr['dense_mass'])
        assert row['site_abs_diff']['time'] < 1e-12, ('time differs from the site', i, t_tcc, site['times'][i])
        assert row['site_abs_diff']['dense'] < 1e-12, ('dense fraction differs from the site', i, fd, site['dense'][i])
        if KIND == 'athpp':
            assert y_asym == 0 and z_asym == 0, ('Athena++ keeps exact mirror symmetry in y and z', i, y_asym, z_asym)
        rows.append(row)
        if i % 10 == 0 or k == len(sel) - 1:
            log('state %3d/101  t = %.4f t_cc  M = %.6f  f_d = %.5f (site %.5f)  mesh %d KB  read %.0f s  mesh %.0f s' % (
                i, t_tcc, mass, fd, site['dense'][i], len(blob) // 1024, read_s, mesh_s))
    times = [r['t_tcc'] for r in rows]
    assert abs(times[0]) < 1e-12 and all(b > c for b, c in zip(times[1:], times[:-1])), 'times must start at 0 and increase'
    if full:
        assert len(rows) == 101 and abs(times[-1] - 5) < 2e-6, (len(rows), times[-1])
        n_site = len(site['times'])
        assert n_site in (101, 102) and (n_site == 101 or KIND == 'enzo'), n_site
    fd = [r['dense_fraction'] for r in rows]
    tcode = [r['time_code'] for r in rows]; total = [r['total_mass'] for r in rows]; dense = [r['dense_mass'] for r in rows]
    tris = [r['triangles'] for r in rows]; shells = [r['shells'] for r in rows]
    ea = np.stack(rgb_e); fa = np.stack(rgb_f)
    tmp = CACHE_FILE.with_name(CACHE_FILE.stem + '.tmp.npz')
    np.savez(tmp, rgb_e=ea, rgb_f=fa, col_e=np.stack(col_e), col_f=np.stack(col_f), t_tcc=np.array(times), times=np.array(times), t_code=np.array(tcode),
             total=np.array(total), dense=np.array(dense), fd=np.array(fd), tris=np.array(tris), shells=np.array(shells), label=np.array(LABEL))
    os.replace(tmp, CACHE_FILE)
    assert not_zero_filled(CACHE_FILE)
    with np.load(CACHE_FILE) as z:
        assert np.array_equal(z['rgb_e'], ea) and np.array_equal(z['rgb_f'], fa) and list(z['t_tcc']) == times and str(z['label']) == LABEL
    # sprite sheets
    for view, arr, w in (('edge', ea, 256), ('face', fa, 128)):
        sheet = np.concatenate(list(arr), axis=0); assert sheet.shape == (128 * len(rows), w, 3)
        p = WORK / (view + '.png'); png_site(p, sheet)
        assert not_zero_filled(p)
        with Image.open(p) as im:
            assert im.size == (w, 128 * len(rows)) and im.mode == 'RGB'
            assert np.array_equal(np.asarray(im.convert('RGB')), sheet), view + ' sprite does not read back'
    entry = dict(id=RID, label=LABEL, code=CODE, chi=CHI, mach=2, n=N, level=LEVEL, cells=2 * N ** 3,
                 frames=[dict(time=t, nominal=round(t * 20) / 20) for t in times], views=['edge', 'face'], note=NOTE, status='Complete run',
                 boundary=BOUNDARY, cooling=COOLING, times=times, dense=fd, extent=[-3, 17, -5, 5], image_shape=[128, 256], color_range=[.008, 5])
    write_json(WORK / 'entry.json', entry)
    e3 = dict(label=LABEL, code=CODE, chi=CHI, lvl=LEVEL, frames=len(rows), note=NOTE, projection_id=RID)
    write_json(WORK / 'entry3d.json', e3)
    index = dict(schema_version=2, frames=['f%03d.bin' % k for k in range(len(rows))], times=times, tris=tris, shell_counts=shells, display=e3,
                 visualization=dict(field='total gas density / initial cloud density', grid=[2 * N, N, N], gaussian_sigma_native_cells=.8,
                                    mesh_step_native_cells=MESH_STEP, position_bits=16,
                                    particle_deposition='cell mass / cell volume' if KIND == 'gizmo' else None, temporal_interpolation=False),
                 diagnostics=dict(schema_version=2, series=[dict(t_over_tcc=t, dense_mass_over_initial_dense_mass=d) for t, d in zip(times, fd)]))
    write_json(WORK / '3d' / 'index.json', index)
    mb = [r['mesh_bytes'] for r in rows]; m = total
    match = dict(site_catalog=site_src, site_label_before=site['label'], site_states_shown_before=len(site['frames']), site_history_points=len(site['times']),
                 site_history_points_not_used=[dict(index=i, time=site['times'][i], dense=site['dense'][i]) for i in range(101, len(site['times']))],
                 max_abs_diff_time_vs_site=max(r['site_abs_diff']['time'] for r in rows), max_abs_diff_dense_fraction_vs_site=max(r['site_abs_diff']['dense'] for r in rows),
                 receipt=rec_src, max_rel_diff_time_code_vs_receipt=max(r['receipt_rel_diff']['time_code'] for r in rows),
                 max_rel_diff_total_mass_vs_receipt=max(r['receipt_rel_diff']['total_mass'] for r in rows),
                 max_rel_diff_dense_mass_vs_receipt=max(r['receipt_rel_diff']['dense_mass'] for r in rows),
                 tolerance=dict(site_abs=1e-12, receipt_rel=1e-12), states_compared=len(rows), all_pass=True)
    checks = dict(states=len(rows), times_from_files=True, finite=True, positive=KIND != 'gizmo', non_negative_lattice=KIND == 'gizmo',
                  t_tcc_first_last=[times[0], times[-1]], strictly_increasing=True,
                  smallest_step_tcc=min(b - c for b, c in zip(times[1:], times[:-1])) if len(times) > 1 else None,
                  largest_step_tcc=max(b - c for b, c in zip(times[1:], times[:-1])) if len(times) > 1 else None,
                  total_mass_first_last_min_max=[m[0], m[-1], min(m), max(m)], dense_mass_first_last=[dense[0], dense[-1]], dense_fraction_final=fd[-1],
                  max_mirror_difference_y=max(r['y_asym'] for r in rows), max_mirror_difference_z=max(r['z_asym'] for r in rows),
                  exact_mirror_symmetry_y_z=(max(r['y_asym'] for r in rows) == 0 and max(r['z_asym'] for r in rows) == 0) if KIND == 'athpp' else 'not required for this code',
                  axis_and_initial_state=init_check)
    rep = dict(id=RID, label=LABEL, code=CODE, chi=CHI, mach=2, level=LEVEL, n=N, cells=2 * N ** 3, dx=DX, kind=KIND, wind_speed_code_units=VW,
               t_cc_code_units=TCC, dense_threshold=THRESH, boundary=BOUNDARY, cooling=COOLING, note=NOTE,
               read_from=where, input_deck=RUN.get('deck'), picked_states=PICK or None, match=match, checks=checks,
               mesh=dict(step=MESH_STEP, filter_mode=MODE, fallbacks=fallbacks, total_bytes=sum(mb), min=min(mb), median=sorted(mb)[len(mb) // 2], max=max(mb),
                         triangles_max=max(tris), empty_frames=sum(1 for x in shells if x == 0)),
               cache=dict(file=str(CACHE_FILE), keys='rgb_e, rgb_f (uint8 sprite rows), col_e, col_f (float32 column density / (rho_c,0 R)), t_tcc and times, '
                                                     't_code, total, dense, fd, tris, shells, label', bytes=os.path.getsize(CACHE_FILE)),
               stages=dict(read_seconds=round(read_s, 1), mesh_seconds=round(mesh_s, 1), read_phase_wall_seconds=round(time.perf_counter() - t0, 1)),
               max_rss_MB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024), states_table=rows,
               stage_script=dict(path=str(Path(__file__).resolve()), sha256=sha256_file(__file__)),
               lifted=dict(grid_tool=dict(path=str(GRID_TOOL), sha256=sha256_file(GRID_TOOL), names=GRID_NAMES),
                           other_tool=dict(path=str(OTHER_TOOL), sha256=sha256_file(OTHER_TOOL), names=OTHER_NAMES),
                           encoder=dict(path=str(REPO / 'analysis/recent_3d_export.py'), sha256=sha256_file(REPO / 'analysis/recent_3d_export.py')),
                           png=dict(path=str(REPO / 'analysis/recent_gallery_export.py'), sha256=sha256_file(REPO / 'analysis/recent_gallery_export.py')),
                           colour_table=dict(path=str(REPO / 'assets/recent/catalog.json'), sha256=sha256_file(REPO / 'assets/recent/catalog.json'))))
    write_json(WORK / 'stage_report.json', rep, compact=False)
    meta = dict(id=RID, label=LABEL, times=times, cache=str(CACHE_FILE), view_sizes=dict(edge=[128, 256], face=[128, 128]), colour='magma, log10 0.008 to 5')
    write_json(CACHE_FILE.with_suffix('.json'), meta, compact=False)
    log('read phase done: %d states, %.0f s; site match: time %.2e, dense %.2e; receipt: t %.2e, M %.2e, Md %.2e' % (
        len(rows), time.perf_counter() - t0, match['max_abs_diff_time_vs_site'], match['max_abs_diff_dense_fraction_vs_site'],
        match['max_rel_diff_time_code_vs_receipt'], match['max_rel_diff_total_mass_vs_receipt'], match['max_rel_diff_dense_mass_vs_receipt']))

# ------------------------------------------------------------------ phase film (film code of stage_run2.py)
def probe(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                          'stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames,color_space,color_transfer,color_primaries,color_range'
                          ':format=duration,size', '-of', 'json', str(p)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j['streams'][0]
    return dict(codec=s['codec_name'], profile=s.get('profile'), width=s['width'], height=s['height'], pix_fmt=s['pix_fmt'], r_frame_rate=s['r_frame_rate'],
                avg_frame_rate=s['avg_frame_rate'], frames=int(s['nb_read_frames']), color_space=s.get('color_space'), color_transfer=s.get('color_transfer'),
                color_primaries=s.get('color_primaries'), color_range=s.get('color_range'), duration=float(j['format']['duration']), bytes=int(j['format']['size']))

def phase_film():
    t0 = time.perf_counter()
    z = np.load(CACHE_FILE); times = [float(v) for v in z['t_tcc']]; rgb_e, rgb_f = z['rgb_e'], z['rgb_f']
    assert str(z['label']) == LABEL
    rep = load(WORK / 'stage_report.json')
    ip = int(np.argmin([abs(t - 2.5) for t in times]))
    for view, arr, size in (('edge', rgb_e, (768, 384)), ('face', rgb_f, (384, 384))):
        p = WORK / ('poster-%s.jpg' % view); tmp = p.with_name('tmp-' + p.name)
        Image.fromarray(arr[ip]).resize(size, Image.Resampling.LANCZOS).save(tmp, quality=92)
        os.replace(tmp, p); assert not_zero_filled(p) and not zero_pages(p)
    films = {}
    for view, arr in (('edge', rgb_e), ('face', rgb_f)):
        s = time.perf_counter(); crf = 18
        dest = WORK / ('film-%s.mp4' % view); tmp = WORK / ('tmp-film-%s.mp4' % view)
        while True:
            nfr, fidx = L['make_film'](arr, times, view, LABEL, tmp, crf)
            pr = probe(tmp)
            if pr['bytes'] < 25 * 1000 * 1000 or crf >= 30: break
            crf += 2; log('film over 25 MB, crf ->', crf)
        assert pr['codec'] == 'h264' and pr['profile'] == 'High' and pr['pix_fmt'] == 'yuv420p' and (pr['width'], pr['height']) == (1920, 1080), pr
        assert pr['r_frame_rate'] == '60/1' and pr['frames'] == nfr and pr['color_space'] == 'bt709' and pr['bytes'] < 25 * 1000 * 1000, pr
        os.replace(tmp, dest); assert not zero_pages(dest)
        films[view] = dict(crf=crf, frames_written=nfr, state_frames=fidx, seconds_to_make=round(time.perf_counter() - s, 1), **pr)
        log('film %s: %d frames, %.1f MB, crf %d, %.0f s' % (view, nfr, pr['bytes'] / 1e6, crf, time.perf_counter() - s))
    rep['posters'] = dict(state=ip, t_tcc=times[ip], sizes=dict(edge=[768, 384], face=[384, 384]), resample='lanczos', jpeg_quality=92)
    rep['film'] = dict(code='stage_run2.py make_film, background, Readout, schedule (lifted unchanged)', fps=L['FPS'], frames_per_tcc=L['FRAMES_PER_TCC'],
                       hold_start_frames=L['HOLD_START'], hold_end_frames=L['HOLD_END'], label=LABEL, views=films, wall_seconds=round(time.perf_counter() - t0, 1),
                       method='every saved state shown unblended on frame hold_start + round(t x 240); frames in between are linear cross fades of the two '
                              'neighbouring states (colour mapped first); the time readout is interpolated linearly between their times and drawn after the fade',
                       to_be_redrawn='by the shared renderer from the cache')
    write_json(WORK / 'stage_report.json', rep, compact=False)

# ------------------------------------------------------------------ phase check and finish
TOP = ['3d', 'edge.png', 'entry.json', 'entry3d.json', 'face.png', 'film-edge.mp4', 'film-face.mp4', 'poster-edge.jpg', 'poster-face.jpg', 'stage_report.json']
ENTRY_KEYS = ['id', 'label', 'code', 'chi', 'mach', 'n', 'level', 'cells', 'frames', 'views', 'note', 'status', 'boundary', 'cooling', 'times', 'dense',
              'extent', 'image_shape', 'color_range']

def verify_folder(root, rep):
    names = sorted(os.listdir(root))
    assert names == sorted(TOP), ('folder content', names)
    res = {}
    entry = load(root / 'entry.json'); e3 = load(root / 'entry3d.json')
    assert list(entry) == ENTRY_KEYS, list(entry)
    n = len(entry['frames'])
    assert n == len(entry['times']) == len(entry['dense']) == e3['frames'] and entry['times'] == [f['time'] for f in entry['frames']]
    assert entry['id'] == RID and entry['label'] == LABEL == e3['label'] and entry['note'] == NOTE == e3['note'] and e3['projection_id'] == RID
    assert entry['code'] == CODE == e3['code'] and entry['chi'] == CHI == e3['chi'] and entry['level'] == 5 == e3['lvl'] and entry['status'] == 'Complete run'
    assert entry['boundary'] == BOUNDARY and entry['cooling'] == COOLING and entry['color_range'] == [.008, 5] and entry['cells'] == 4194304
    if not PICK:
        assert n == 101 and abs(entry['times'][-1] - 5) < 2e-6
    z = np.load(CACHE_FILE)
    assert list(z['t_tcc']) == entry['times'] and list(z['fd']) == entry['dense']
    for view, w, key in (('edge', 256, 'rgb_e'), ('face', 128, 'rgb_f')):
        with Image.open(root / (view + '.png')) as im:
            im.load(); assert im.size == (w, 128 * n) and im.mode == 'RGB'
            assert np.array_equal(np.asarray(im), np.concatenate(list(z[key]), axis=0)), view + ' sprite differs from the cache'
        with Image.open(root / ('poster-%s.jpg' % view)) as im:
            im.load(); assert im.size == ((768, 384) if view == 'edge' else (384, 384)) and im.mode == 'RGB'
        f = root / ('film-%s.mp4' % view)
        pr = probe(f)
        want = L['HOLD_START'] + int(round(entry['times'][-1] * L['FRAMES_PER_TCC'])) + 1 + L['HOLD_END']
        assert pr['codec'] == 'h264' and pr['profile'] == 'High' and pr['pix_fmt'] == 'yuv420p' and (pr['width'], pr['height']) == (1920, 1080), pr
        # the film code of stage_run2.py tags the matrix and range; with ffmpeg 8.0.1 primaries and transfer stay unset
        # (same as the films staged on 2026-11-22); the shared renderer redraws the films
        assert pr['r_frame_rate'] == '60/1' and pr['color_space'] == 'bt709' and pr['color_range'] == 'tv', pr
        assert pr['frames'] == want == rep['film']['views'][view]['frames_written'] and pr['bytes'] < 25 * 1000 * 1000, (pr, want)
        dec = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(f), '-f', 'null', '-'], capture_output=True, text=True)
        assert dec.returncode == 0 and not dec.stderr.strip(), ('decode', dec.stderr[-500:])
        pr['full_decode'] = 'ffmpeg decoded every frame without a message'
        res['film_' + view] = pr
    idx = load(root / '3d/index.json')
    assert idx['frames'] == ['f%03d.bin' % i for i in range(n)] and idx['times'] == entry['times'] and idx['display'] == e3
    assert [s['dense_mass_over_initial_dense_mass'] for s in idx['diagnostics']['series']] == entry['dense']
    tri = []
    for i, fn in enumerate(idx['frames']):
        blob = (root / '3d' / fn).read_bytes(); ns, nt = decode_mesh(blob)
        assert ns == idx['shell_counts'][i] and nt == idx['tris'][i]; tri.append(nt)
    assert sorted(os.listdir(root / '3d')) == sorted(idx['frames'] + ['index.json'])
    bad = {str(p.relative_to(root)): zero_pages(p) for p in root.rglob('*') if p.is_file()}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, ('zero filled pages', bad)
    for p in [root / 'entry.json', root / 'entry3d.json', root / '3d/index.json', root / 'stage_report.json']:
        load(p)
    res['files'] = sum(1 for p in root.rglob('*') if p.is_file()); res['bytes'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    res['mesh_frames_decoded'] = len(tri); res['zero_filled_pages'] = 0
    text = ' '.join([entry['label'], entry['note'], e3['label'], e3['note'], entry['status'], entry['boundary'], entry['cooling'], entry['code']])
    assert not re.search('[\u2012\u2013\u2014\u2015]|--| - ', text), text
    assert not re.search(r'(?i)ultra|hires|sharp13|full_0|full_1|\.athdf|\.phdf|historical|receipt|accepted|bounded|screen|preview|blended|interpolated|tracer_|repair', text), text
    res['visible_text_checked'] = text
    return res

def look_frames(root, rep):
    out = NOTES / 'look' / TAG; out.mkdir(parents=True, exist_ok=True)
    entry = load(root / 'entry.json'); t = entry['times']
    i25 = int(np.argmin([abs(x - 2.5) for x in t]))
    hold = L['HOLD_START']; picks = {}
    sheets = []
    for view in ('edge', 'face'):
        film = rep['film']['views'][view]; nb = film['frames_written']
        fr = [hold, hold + film['state_frames'][i25], hold + film['state_frames'][i25] + 6, nb - 1]
        picks[view] = fr; tiles = []
        for k in fr:
            dst = out / ('%s_%s_f%04d.png' % (RID, view, k))
            subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(root / ('film-%s.mp4' % view)), '-vf', 'select=eq(n\\,%d)' % k, '-vsync', '0',
                            '-frames:v', '1', str(dst)], check=True)
            tiles.append(Image.open(dst).convert('RGB'))
        grid = Image.new('RGB', (1920, 1080), (40, 40, 40))
        for m_, im in enumerate(tiles):
            grid.paste(im.resize((958, 538), Image.Resampling.LANCZOS), ((m_ % 2) * 962, (m_ // 2) * 542))
        grid.save(out / ('%s_%s_grid.png' % (RID, view))); sheets.append(grid)
    # sprite rows nearest t = 0, 1, 2, 3, 4, 5 t_cc, edge and face side by side
    idx = [int(np.argmin([abs(x - target) for x in t])) for target in (0, 1, 2, 3, 4, 5)]
    e = np.asarray(Image.open(root / 'edge.png').convert('RGB')); fa = np.asarray(Image.open(root / 'face.png').convert('RGB'))
    gap = 8
    sheet = Image.new('RGB', (3 * gap + 512 + 256, len(idx) * (256 + gap) + gap), (11, 16, 23))
    for r, i in enumerate(idx):
        sheet.paste(Image.fromarray(e[128 * i:128 * (i + 1)]).resize((512, 256), Image.Resampling.NEAREST), (gap, gap + r * (256 + gap)))
        sheet.paste(Image.fromarray(fa[128 * i:128 * (i + 1)]).resize((256, 256), Image.Resampling.NEAREST), (2 * gap + 512, gap + r * (256 + gap)))
    sheet.save(out / ('%s_sprites_t012345.png' % RID))
    for v in ('edge', 'face'):
        Image.open(root / ('poster-%s.jpg' % v)).save(out / ('%s_poster-%s.png' % (RID, v)))
    return dict(folder=str(out), film_frames=picks, sprite_rows=idx)

def phase_check():
    rep = load(WORK / 'stage_report.json')
    res = verify_folder(WORK, rep)
    lk = look_frames(WORK, rep)
    rep['verification_in_work_folder'] = res; rep['look'] = lk
    write_json(WORK / 'stage_report.json', rep, compact=False)
    log('check ok: %d files, %.1f MB; films %s' % (res['files'], res['bytes'] / 1e6, {k: (v['frames'], v['bytes']) for k, v in res.items() if k.startswith('film')}))

def phase_finish():
    t0 = time.perf_counter()
    assert not PICK, 'a test folder is never moved to the staging folder'
    rep = load(WORK / 'stage_report.json')
    res = verify_folder(WORK, rep)
    if FINAL.exists():
        raise SystemExit('staging folder exists already: %s' % FINAL)
    rep['verification'] = res
    rep['staged_to'] = str(FINAL).replace('/mnt/d/', 'D:/')
    rep['stages']['finish_seconds'] = round(time.perf_counter() - t0, 1)
    rep['stages']['total_wall_seconds'] = round(rep['stages']['read_phase_wall_seconds'] + rep['film']['wall_seconds'] + rep['stages']['finish_seconds'], 1)
    rep['written'] = time.strftime('%Y-%m-%d %H:%M:%S')
    write_json(WORK / 'stage_report.json', rep, compact=False)
    before = {str(p.relative_to(WORK)): (p.stat().st_size, sha256_file(p)) for p in WORK.rglob('*') if p.is_file()}
    shutil.move(str(WORK), str(FINAL))
    after = {str(p.relative_to(FINAL)): (p.stat().st_size, sha256_file(p)) for p in FINAL.rglob('*') if p.is_file()}
    assert before == after, 'files changed during the move'
    res2 = verify_folder(FINAL, rep)
    log('staged to %s: %d files, %.1f MB' % (FINAL, res2['files'], res2['bytes'] / 1e6))

if a.phase == 'read': phase_read()
elif a.phase == 'film': phase_film()
elif a.phase == 'check': phase_check()
elif a.phase == 'finish': phase_finish()
