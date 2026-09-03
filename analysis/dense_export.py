"""Dense frame exporter: EVERY snapshot becomes a streamable 3D frame.

Why this beats the embedded volumes 5-6x on size:
  - marching_cubes returns an INDEXED mesh; the old export expanded it into a
    triangle soup, storing every vertex ~6 times. Here verts+faces ship as-is.
  - raw little-endian binary instead of base64 (1.33x)
  - gzipped at rest; browsers inflate natively via DecompressionStream

Frame file (.bin, gzipped):
  u8 nshells; per shell: f32 level, f32 opacity, f32x3 color, f32x3 qlo,
  f32x3 qhi, u32 nverts, u32 nfaces, u16[nverts*3] quantized verts,
  u32[nfaces*3] indices.
index.json per run: {"times":[...],"frames":[...],"tris":[...]}

Usage: dense_export.py <tag> <kind> <chi> <outroot> <files...>
kinds: apk flash flashx ramses enzo athpp athw part tipsy
part/tipsy need env P3D_CEN="cx,cy,cz" P3D_DIMS="nx,ny,nz"
Idempotent: existing frames are skipped, index.json is rebuilt.
"""
import gzip
import json
import os
import struct
import sys

import numpy as np
import matplotlib
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

TAG, KIND, CHI = sys.argv[1], sys.argv[2], float(sys.argv[3])
OUTROOT, FILES = sys.argv[4], sys.argv[5:]
OUT = os.path.join(OUTROOT, TAG)
os.makedirs(OUT, exist_ok=True)

RAM_BOXLEN = 20.0   # RAMSES boxlen from the namelist; its box is cubic
XL, YL, ZL = (-3.0, 17.0), (-5.0, 5.0), (-5.0, 5.0)
LEVELS = [0.15 * CHI, 0.6 * CHI]
OPAC = [0.42, 0.96]
LO, HI = -3.2, 0.4
viridis = matplotlib.colormaps["viridis"]
RCLOUD = 0.1 if KIND == "flash" else 1.0
TCC = (CHI ** 0.5) * RCLOUD / 2.582

if KIND in ("part", "tipsy"):
    CEN = np.array([float(v) for v in os.environ["P3D_CEN"].split(",")])
    DIMS = tuple(int(v) for v in os.environ["P3D_DIMS"].split(","))
    if KIND == "tipsy":
        sys.path.insert(0, "/home/kaan/codes/gasoline/ics")
        from make_gasoline_cloudwind import read_tipsy  # noqa: E402
else:
    import yt
    yt.set_log_level(50)


def load_grid(fn):
    ds = yt.load(fn)
    t = float(ds.current_time)
    dle = np.array(ds.domain_left_edge, dtype=float)
    dre = np.array(ds.domain_right_edge, dtype=float)
    dims = [int(v) for v in ds.domain_dimensions]
    lvl = 0
    if KIND in ("flash", "flashx"):
        lvl = min(4, int(ds.index.max_level))
        dims = [d * 2 ** lvl for d in dims]
    cg = ds.covering_grid(lvl, ds.domain_left_edge, dims)
    rho = np.array(cg[("gas", "density")], dtype=np.float32)
    del cg, ds
    if KIND == "apk":
        rho = np.ascontiguousarray(np.transpose(rho, (1, 0, 2)))
        lo = np.array([dle[1], dle[0], dle[2]]); hi = np.array([dre[1], dre[0], dre[2]])
    else:
        lo, hi = dle[:3].copy(), dre[:3].copy()
    if KIND == "flash":
        lo = (lo - np.array([0.3, 0.5, 0.5])) / 0.1
        hi = (hi - np.array([0.3, 0.5, 0.5])) / 0.1
        rho = rho  # density normalisation stays in wind units
    elif KIND == "ramses":
        # yt reports RAMSES in NORMALISED [0,1] box units, not physical ones, so
        # the campaign shift has to come AFTER scaling by boxlen. Subtracting
        # first put every RAMSES cloud in a corner of the box, 0.1 units across.
        lo = lo * RAM_BOXLEN - np.array([3.0, 10.0, 10.0])
        hi = hi * RAM_BOXLEN - np.array([3.0, 10.0, 10.0])
    sp = (hi - lo) / np.array(rho.shape, dtype=float)
    return rho, lo, sp, t


def load_part(fn):
    if KIND == "tipsy":
        hdr, gas = read_tipsy(fn)
        pos = np.asarray(gas["pos"], dtype=np.float64) - CEN[None, :]
        m = np.asarray(gas["mass"], dtype=np.float64)
        try:                     # hdr is a numpy structured scalar, not a dict
            t = float(hdr["time"])
        except Exception:
            t = 0.0
    else:
        import h5py
        with h5py.File(fn, "r") as h:
            t = float(h["Header"].attrs["Time"])
            pos = np.array(h["PartType0"]["Coordinates"], dtype=np.float64) - CEN[None, :]
            m = np.array(h["PartType0"]["Masses"], dtype=np.float64)
    edges = [np.linspace(XL[0], XL[1], DIMS[0] + 1),
             np.linspace(YL[0], YL[1], DIMS[1] + 1),
             np.linspace(ZL[0], ZL[1], DIMS[2] + 1)]
    H, _ = np.histogramdd(pos, bins=edges, weights=m)
    vol = ((XL[1]-XL[0])/DIMS[0]) * ((YL[1]-YL[0])/DIMS[1]) * ((ZL[1]-ZL[0])/DIMS[2])
    rho = gaussian_filter((H / vol).astype(np.float32), sigma=0.8, mode="nearest")
    lo = np.array([XL[0], YL[0], ZL[0]])
    sp = np.array([(XL[1]-XL[0])/DIMS[0], (YL[1]-YL[0])/DIMS[1], (ZL[1]-ZL[0])/DIMS[2]])
    return rho, lo, sp, t


def frame_bytes(rho, lo, sp):
    shells = []
    for lev, op in zip(LEVELS, OPAC):
        if not (float(rho.min()) < lev < float(rho.max())):
            continue
        try:
            verts, faces, _, _ = marching_cubes(rho, level=lev, step_size=1)
        except Exception:
            continue
        v = (lo[None, :] + verts * sp[None, :]).astype(np.float32)
        keep = ((v[:, 0] > XL[0] - 0.5) & (v[:, 0] < XL[1] + 0.5))
        if not keep.all():
            # drop faces touching removed verts, remap indices
            idx = -np.ones(len(v), dtype=np.int64)
            idx[keep] = np.arange(int(keep.sum()))
            fmask = keep[faces].all(axis=1)
            faces = idx[faces[fmask]]
            v = v[keep]
        if len(v) < 3 or len(faces) < 1:
            continue
        qlo, qhi = v.min(axis=0), v.max(axis=0)
        span = np.maximum(qhi - qlo, 1e-9)
        q = np.clip((v - qlo) / span * 65535.0, 0, 65535).astype("<u2")
        frac = float(np.clip((np.log10(lev / CHI) - LO) / (HI - LO), 0, 1))
        col = viridis(frac)[:3]
        shells.append((lev, op, col, qlo, qhi, q, faces.astype("<u4")))
    if not shells:
        return None, 0
    buf = bytearray()
    buf += struct.pack("<B", len(shells))
    tris = 0
    for lev, op, col, qlo, qhi, q, f in shells:
        buf += struct.pack("<ff", lev, op)
        buf += struct.pack("<fff", *col)
        buf += struct.pack("<fff", *[float(x) for x in qlo])
        buf += struct.pack("<fff", *[float(x) for x in qhi])
        buf += struct.pack("<II", len(q), len(f))
        buf += q.tobytes(); buf += f.tobytes()
        tris += len(f)
    return gzip.compress(bytes(buf), 6), tris


times, frames, tricount = [], [], []
new = 0
for i, fn in enumerate(FILES):
    name = "f%03d.bin" % i
    path = os.path.join(OUT, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        frames.append(name); times.append(None); tricount.append(None)
        continue
    try:
        rho, lo, sp, t = load_part(fn) if KIND in ("part", "tipsy") else load_grid(fn)
        blob, tris = frame_bytes(rho, lo, sp)
    except Exception as e:
        print("skip %s: %s" % (os.path.basename(fn), e)); continue
    if blob is None:
        # an empty isosurface is DATA (the cloud dropped below threshold or
        # left the box): ship a zero-shell frame so the time grid stays whole
        blob, tris = gzip.compress(struct.pack("<B", 0)), 0
    with open(path, "wb") as f:
        f.write(blob)
    frames.append(name); times.append(round(t / TCC, 3)); tricount.append(tris)
    new += 1

# fill times for pre-existing frames from any prior index
prev = {}
ixp = os.path.join(OUT, "index.json")
if os.path.exists(ixp):
    try:
        old = json.load(open(ixp))
        prev = dict(zip(old.get("frames", []), zip(old.get("times", []), old.get("tris", []))))
    except Exception:
        pass
for j, name in enumerate(frames):
    if times[j] is None and name in prev:
        times[j], tricount[j] = prev[name]

# ORDER BY TIME, always. File names can lie about order (Flash-X's forced final
# dump sorts before the series and replayed whole runs in the viewer), duplicate
# terminal dumps exist, and nothing past 5 t_cc is physics. Enforce all three.
rows = sorted((t, n, tr) for t, n, tr in zip(times, frames, tricount) if t is not None)
times, frames, tricount = [], [], []
_last = -1.0
for t, n, tr in rows:
    if t > 5.05 or (_last >= 0 and abs(t - _last) <= 1e-6):
        continue
    times.append(round(t, 3)); frames.append(n); tricount.append(tr)
    _last = t

with open(ixp, "w") as f:
    json.dump({"tag": TAG, "chi": CHI, "times": times, "frames": frames, "tris": tricount}, f)
tot = sum(os.path.getsize(os.path.join(OUT, x)) for x in frames if os.path.exists(os.path.join(OUT, x)))
print("%s: %d frames (%d new), %.1f MB total, %.1f KB/frame mean"
      % (TAG, len(frames), new, tot / 1048576, tot / max(len(frames), 1) / 1024))
