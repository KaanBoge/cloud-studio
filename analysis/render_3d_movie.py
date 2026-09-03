#!/usr/bin/env python
"""Genuinely three-dimensional cloud-crushing movies.

The old "3D" movies were mid-plane slices, so they looked exactly like the 2D
panels.  This renderer instead extracts NESTED DENSITY ISOSURFACES from the full
3D volume and draws them as a shaded, depth-sorted solid with a slowly orbiting
camera, so the cloud reads as an object with front, back and volume.

Framing is deliberately identical to the 2D panels: wind blows left to right
along +x, the cloud starts at the origin, x spans -3..17 cloud radii and y spans
-5..5.  Colours come from the same viridis map with the same fixed per-chi log
density limits used everywhere else in the project.

Usage:
  render_3d_movie.py <kind> <chi> <tcc> <label> <outname> <dir> <glob> [stride]
    kind: apk | flash | athw
Writes /mnt/c/Users/kaanb/CloudCrushing/results_A8/movies/<outname>.mp4
   and .../<outname>_slow.mp4
"""
import glob
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yt
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage.measure import marching_cubes

try:
    from scipy.ndimage import gaussian_filter
except Exception:  # scipy optional
    gaussian_filter = None

yt.set_log_level(40)

if len(sys.argv) < 8:
    sys.exit(__doc__)

KIND, CHI, TCC, LABEL, OUTNAME, DIR, PATTERN = (
    sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4],
    sys.argv[5], sys.argv[6], sys.argv[7])
STRIDE = int(sys.argv[8]) if len(sys.argv) > 8 else int(os.environ.get("R3D_STRIDE", "1"))

# ----------------------------------------------------------------- constants
CLIM = {10: (-1.0, 1.5), 100: (-1.0, 2.5), 1000: (-1.0, 3.5)}
LO, HI = CLIM.get(CHI, (-1.0, 1.5))

XLIM, YLIM, ZLIM = (-3.0, 17.0), (-5.0, 5.0), (-5.0, 5.0)
TARGET_CPR = float(os.environ.get("R3D_CPR", "24"))   # cells per cloud radius
MAX_CELLS = float(os.environ.get("R3D_MAXCELLS", "1.6e8"))  # memory guard
NPROC = int(os.environ.get("R3D_NPROC", "0"))         # 0 = auto
AZ0, AZ_SWEEP = -80.0, 40.0   # gentle orbit: azimuth sweeps 40 deg
ELEV = 22.0
LIGHT = np.array([0.30, -0.80, 0.52])
LIGHT /= np.linalg.norm(LIGHT)
BG = np.array([1.0, 1.0, 1.0])

OUTDIR = "/mnt/c/Users/kaanb/CloudCrushing/results_A8/movies"
FRAMEDIR = os.path.join(DIR, "_iso3d_frames")


def levels_for(chi):
    """Three nested density isosurfaces: faint shocked shell, cloud, dense core.

    All are pushed above the wind density (1.0) so the shell is a real
    over-density and not just the ambient wind."""
    lv = [max(f * chi, 1.35 + 0.25 * i) for i, f in enumerate((0.06, 0.22, 0.60))]
    out = []
    for v in lv:                       # keep them strictly separated
        if out and v <= out[-1] * 1.25:
            v = out[-1] * 1.25
        out.append(v)
    return out


LEVELS = levels_for(CHI)
OPAC = [0.22, 0.58, 1.00]
STEP = [1, 1, 1]                       # full-resolution triangles on every shell
viridis = matplotlib.colormaps["viridis"]


# --------------------------------------------------------------- data loading
def load_volume(fn):
    """Return (rho[x,y,z], lo_xyz, spacing, t) in CLOUD RADII with cloud at origin.

    Coordinate conventions match render_unified.py:
      apk   - domain is rotated, wind along +x2; transpose so wind runs along +x.
              Lengths are already cloud radii with the cloud at the origin.
      flash - domain 0..2 x 0..1 x 0..1, cloud at (0.3,0.5,0.5), radius 0.1.
      athw  - already cloud-radius units with the cloud at the origin.
    """
    ds = yt.load(fn)
    t = float(ds.current_time)
    dle = np.array(ds.domain_left_edge, dtype=float)
    dre = np.array(ds.domain_right_edge, dtype=float)
    base = np.array([int(v) for v in ds.domain_dimensions])

    if KIND == "flash":
        cen, R = np.array([0.3, 0.5, 0.5]), 0.1
    elif KIND == "ramses":
        # cubic [0,20]^3 box, cloud at (3,10,10); shift into the shared frame
        cen, R = np.array([3.0, 10.0, 10.0]), 1.0
    else:
        cen, R = np.zeros(3), 1.0

    # streamwise axis in the file's own index order (apk stores it as axis 1)
    sx = 1 if KIND == "apk" else 0
    span_r = (dre[sx] - dle[sx]) / R                      # streamwise cloud radii
    cpr0 = base[sx] / span_r                              # cells per radius, level 0
    try:
        maxl = int(ds.index.max_level)
    except Exception:
        maxl = 0
    lvl = 0
    while lvl < maxl and cpr0 * 2 ** lvl < TARGET_CPR:
        lvl += 1
    # never ask for a covering grid bigger than the memory guard allows
    while lvl > 0 and float(np.prod([d * 2 ** lvl for d in base])) > MAX_CELLS:
        lvl -= 1

    dims = [int(d * 2 ** lvl) for d in base]
    cg = ds.covering_grid(lvl, ds.domain_left_edge, dims)
    rho = np.array(cg[("gas", "density")], dtype=np.float32)
    del cg, ds

    if KIND == "apk":
        # wind runs along +x2 here, so swap the first two axes into (x, y, z)
        rho = np.ascontiguousarray(np.transpose(rho, (1, 0, 2)))
        lo_xyz = np.array([dle[1], dle[0], dle[2]])
        hi_xyz = np.array([dre[1], dre[0], dre[2]])
    else:
        lo_xyz, hi_xyz = dle.copy(), dre.copy()
    lo_xyz = (lo_xyz - cen) / R
    hi_xyz = (hi_xyz - cen) / R

    # decimate anisotropically down to ~TARGET_CPR cells per cloud radius
    cell = (hi_xyz - lo_xyz) / np.array(rho.shape, dtype=float)
    fac = []
    for i in range(3):
        cpr = rho.shape[i] / max(hi_xyz[i] - lo_xyz[i], 1e-9)
        fac.append(max(1, int(np.floor(cpr / TARGET_CPR))))
    rho = block_mean(rho, fac)

    # derive spacing from the ORIGINAL cell size: block_mean may crop a ragged
    # remainder, so rescaling the full span over the new shape would drift.
    spacing = cell * np.array(fac, dtype=float)
    if gaussian_filter is not None:
        rho = gaussian_filter(rho, sigma=0.45, mode="nearest")
    return rho, lo_xyz, spacing, t


def block_mean(a, fac):
    """Average-pool by integer factors per axis (crops the ragged remainder)."""
    fac = [int(f) for f in fac]
    if all(f == 1 for f in fac):
        return a
    n = [(a.shape[i] // fac[i]) * fac[i] for i in range(3)]
    a = a[: n[0], : n[1], : n[2]]
    a = a.reshape(n[0] // fac[0], fac[0], n[1] // fac[1], fac[1], n[2] // fac[2], fac[2])
    return a.mean(axis=(1, 3, 5), dtype=np.float32)


# ------------------------------------------------------------------- geometry
def surface(rho, lo_xyz, spacing, level, step):
    """Marching-cubes isosurface -> (triangles[F,3,3], face normals[F,3])."""
    if not (float(rho.min()) < level < float(rho.max())):
        return None
    try:
        verts, faces, normals, _ = marching_cubes(rho, level=level, step_size=step)
    except (ValueError, RuntimeError):
        return None
    if len(faces) == 0:
        return None
    pts = lo_xyz[None, :] + verts * spacing[None, :]
    # vertex normals live in index space; rescale into physical space
    nrm = normals / spacing[None, :]
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12

    tri = pts[faces]                               # (F,3,3)
    fn = nrm[faces].mean(axis=1)                   # averaged -> softer shading
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12

    # make normals point outward (marching_cubes orientation can be global-flipped)
    cent = pts.mean(axis=0)
    radial = tri.mean(axis=1) - cent
    if float(np.sum(fn * radial)) < 0.0:
        fn = -fn
    return tri, fn


def shade(tri, fn, base_rgb, alpha, cam, dref):
    """Lambertian + specular lighting and aerial perspective, so depth is obvious.

    dref is the (min, max) camera-depth of the WHOLE scene, so every shell fades
    on one common scale instead of each being hazed independently.
    """
    lam = np.clip(fn @ LIGHT, 0.0, 1.0)
    bright = 0.26 + 0.74 * lam ** 0.8               # ambient + diffuse
    rgb = np.clip(base_rgb[None, :] * bright[:, None], 0.0, 1.0)

    if alpha > 0.9:                                 # crisp highlight on the core
        half = LIGHT + cam
        half /= np.linalg.norm(half)
        spec = np.clip(fn @ half, 0.0, 1.0) ** 16
        rgb = np.clip(rgb + 0.35 * spec[:, None], 0.0, 1.0)

    depth = tri.mean(axis=1) @ cam                  # + = closer to camera
    d = (depth - dref[0]) / (dref[1] - dref[0] + 1e-12)
    haze = 0.34 * (1.0 - np.clip(d, 0.0, 1.0)) ** 1.3   # far faces recede
    rgb = rgb * (1.0 - haze[:, None]) + BG[None, :] * haze[:, None]

    a = np.full(len(tri), alpha, dtype=float)
    if alpha < 0.9:                                 # translucent shells: rim-fade
        a = a * (0.30 + 0.70 * (1.0 - np.abs(fn @ cam)) ** 0.7)
    return np.concatenate([rgb, a[:, None]], axis=1)


def camera_vector(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


# -------------------------------------------------------------------- drawing
def render_frame(fn, out, azim):
    rho, lo_xyz, spacing, t = load_volume(fn)
    cam = camera_vector(ELEV, azim)

    # the faint outer shell is marched on a coarser stride, so smooth it harder
    # first or the near-tangent shock front turns into a staircase
    soft = rho
    if gaussian_filter is not None and STEP[0] > 1:
        soft = gaussian_filter(rho, sigma=0.9, mode="nearest")

    raw = []
    for level, alpha, step in zip(LEVELS, OPAC, STEP):
        s = surface(soft if step > 1 else rho, lo_xyz, spacing, level, step)
        if s is None:
            continue
        tri, nrm = s
        # clip to the standard comparison window
        c = tri.mean(axis=1)
        keep = ((c[:, 0] > XLIM[0]) & (c[:, 0] < XLIM[1]) &
                (c[:, 1] > YLIM[0]) & (c[:, 1] < YLIM[1]) &
                (c[:, 2] > ZLIM[0]) & (c[:, 2] < ZLIM[1]))
        tri, nrm = tri[keep], nrm[keep]
        if len(tri) == 0:
            continue
        raw.append((tri, nrm, level, alpha))
    if not raw:
        print("no isosurfaces in", fn)
        return False

    # one common depth scale for every shell
    allc = np.concatenate([r[0].mean(axis=1) for r in raw], axis=0) @ cam
    dref = (float(allc.min()), float(allc.max()))

    tris, cols = [], []
    for tri, nrm, level, alpha in raw:
        frac = float(np.clip((np.log10(level) - LO) / (HI - LO), 0.0, 1.0))
        tris.append(tri)
        cols.append(shade(tri, nrm, np.array(viridis(frac)[:3]), alpha, cam, dref))
    tri = np.concatenate(tris, axis=0)
    col = np.concatenate(cols, axis=0)
    print("  %s: %d triangles" % (os.path.basename(fn), len(tri)))

    fig = plt.figure(figsize=(13.6, 7.4), dpi=float(os.environ.get("R3D_DPI", "150")))
    ax = fig.add_axes([0.0, 0.065, 0.875, 0.865], projection="3d")

    # cast a soft shadow of the cloud onto the floor: strongest single cue that
    # this is a solid body sitting in a 3D box rather than a flat picture.
    gx = np.linspace(lo_xyz[0], lo_xyz[0] + spacing[0] * rho.shape[0], rho.shape[0])
    gy = np.linspace(lo_xyz[1], lo_xyz[1] + spacing[1] * rho.shape[1], rho.shape[1])
    col_max = rho.max(axis=2)
    if float(col_max.max()) > LEVELS[1]:
        ax.contourf(gx, gy, col_max.T, levels=[LEVELS[1], LEVELS[2], 1e30],
                    zdir="z", offset=ZLIM[0] + 0.01,
                    colors=[(0.30, 0.32, 0.38, 0.16), (0.20, 0.22, 0.28, 0.30)],
                    antialiased=True)
    del rho, soft

    # ONE collection holding every shell so matplotlib depth-sorts the whole
    # scene together -- that is what makes the nesting read correctly.
    pc = Poly3DCollection(tri, facecolors=col, edgecolors="none",
                          linewidths=0, zsort="average")
    pc.set_alpha(None)               # keep the per-face alphas we computed
    ax.add_collection3d(pc)

    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_zlim(*ZLIM)
    ax.set_box_aspect((2.0, 1.0, 1.0), zoom=1.18)
    ax.view_init(elev=ELEV, azim=azim)
    ax.set_xlabel("x / r_cloud", labelpad=14)
    ax.set_ylabel("y / r_cloud", labelpad=10)
    ax.set_zlabel("z / r_cloud", labelpad=2)
    ax.tick_params(labelsize=9, pad=1)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_facecolor((0.960, 0.964, 0.972, 1.0))
        pane.pane.set_edgecolor((0.78, 0.78, 0.81, 1.0))
        pane._axinfo["grid"]["color"] = (0.855, 0.855, 0.875, 1.0)
    ax.set_facecolor("white")
    fig.text(0.5, 0.965, "%s    chi = %d    t = %.1f t_cc" % (LABEL, CHI, t / TCC),
             ha="center", va="top", fontsize=14)

    cax = fig.add_axes([0.918, 0.20, 0.014, 0.58])
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=Normalize(vmin=LO, vmax=HI))
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("log10 density / wind density", fontsize=10)
    cb.ax.tick_params(labelsize=9)
    for level in LEVELS:                 # mark where the isosurfaces sit
        cb.ax.axhline(np.log10(level), color="white", lw=1.4)

    fig.savefig(out, facecolor="white")
    plt.close(fig)
    return True


# ------------------------------------------------------------------ workers
def _auto_nproc():
    """One worker per core, throttled by free memory and by current load."""
    try:
        ncpu = len(os.sched_getaffinity(0))
    except Exception:
        ncpu = os.cpu_count() or 4
    try:
        with open("/proc/meminfo") as fh:
            mem = {k.split(":")[0]: int(k.split()[1]) for k in fh if ":" in k}
        avail_gb = mem.get("MemAvailable", 4 << 20) / (1 << 20)
    except Exception:
        avail_gb = 4.0
    try:
        load = os.getloadavg()[0]
    except Exception:
        load = 0.0
    by_mem = max(1, int(avail_gb / 1.6))        # ~1.6 GB per worker
    by_cpu = max(1, int(ncpu - load * 0.75))    # yield to running simulations
    return max(1, min(ncpu, by_mem, by_cpu, 8))


def _one(job):
    """Render a single frame; used by the worker pool."""
    fn, out, azim = job
    try:
        tmp = out + ".part.png"
        okf = render_frame(fn, tmp, azim)
        if okf and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, out)
            return True
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception as e:
        print("FAIL", fn, repr(e))
    return False


# ----------------------------------------------------------------------- main
def main():
    files = sorted(glob.glob(os.path.join(DIR, PATTERN)))
    files = [f for f in files if "final" not in os.path.basename(f)
             and not f.endswith((".png", ".xdmf"))]
    files = files[::max(STRIDE, 1)]
    if not files:
        print("no files for", DIR, PATTERN)
        return
    os.makedirs(FRAMEDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    jobs = []
    n = 0
    for i, f in enumerate(files):
        out = os.path.join(FRAMEDIR, "f%04d.png" % i)
        azim = AZ0 + AZ_SWEEP * i / max(len(files) - 1, 1)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            n += 1
            continue
        jobs.append((f, out, azim))

    if jobs:
        nproc = NPROC or _auto_nproc()
        print("rendering %d frames on %d workers" % (len(jobs), nproc))
        if nproc <= 1:
            for j in jobs:
                n += 1 if _one(j) else 0
        else:
            import multiprocessing as mp
            with mp.get_context("fork").Pool(nproc) as pool:
                for okf in pool.imap_unordered(_one, jobs):
                    n += 1 if okf else 0
    print("iso3d frames: %d/%d" % (n, len(files)))
    # a one- or two-frame movie is not a movie; refuse rather than emit a stub
    if n < 4:
        print("only %d frame(s) -- too few to encode, skipping mp4" % n)
        return

    mp4 = os.path.join(OUTDIR, "%s.mp4" % OUTNAME)
    slow = os.path.join(OUTDIR, "%s_slow.mp4" % OUTNAME)
    fps = "10" if len(files) > 25 else "5"
    subprocess.run(["nice", "-n", "19", "ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", fps, "-i", os.path.join(FRAMEDIR, "f%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", mp4],
                   check=False)
    # half speed, motion-interpolated to 30 fps so the orbit glides
    subprocess.run(["nice", "-n", "19", "ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(max(int(fps) // 2, 2)),
                    "-i", os.path.join(FRAMEDIR, "f%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                           "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1",
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", slow],
                   check=False)
    # smooth: motion-interpolated to 60 fps at the original pace
    smooth = os.path.join(OUTDIR, "%s_smooth.mp4" % OUTNAME)
    subprocess.run(["nice", "-n", "19", "ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", fps, "-i", os.path.join(FRAMEDIR, "f%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                           "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", smooth],
                   check=False)
    print("wrote", mp4)
    print("wrote", slow)
    print("wrote", smooth)


if __name__ == "__main__":
    main()
