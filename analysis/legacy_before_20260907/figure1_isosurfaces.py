r"""Figure 1 (Braspenning+2023 style, in 3D).

Rows: overdensity chi = 10, 100, 1000.  Columns: codes.
Every panel is the SAME time (as close to 5 t_cc as the run reached), the SAME
resolution and the SAME viewing geometry, so the only difference between panels
is the numerical method.

Rendered from the dense isosurface store: marching-cubes meshes of the density
field at 0.15*chi (translucent envelope) and 0.6*chi (opaque core).
"""
import gzip, json, os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

S = "/mnt/c/Users/kaanb/cloud-frames-repo"
OUT = sys.argv[1]
LEVEL = sys.argv[2]
CODES = sys.argv[3].split(",")
TIME = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
NICE = {"apk": "AthenaPK", "enzo": "Enzo", "flashx": "Flash-X", "ramses": "RAMSES",
        "athpp": "Athena++", "athw": "Athena 4.2", "flash": "FLASH 4.8",
        "arepo": "Arepo", "gas": "Gasoline", "gzmfm": "GIZMO MFM", "gzmfv": "GIZMO MFV"}
CHIS = [10, 100, 1000]
XL, YL = (-1.0, 9.0), (-3.4, 3.4)


def load_near(tag, t_target=5.0):
    p = os.path.join(S, tag)
    ix = json.load(open(os.path.join(p, "index.json")))
    times = np.array(ix["times"], float)
    i = int(np.argmin(np.abs(times - t_target)))
    raw = gzip.decompress(open(os.path.join(p, ix["frames"][i]), "rb").read())
    off = 0
    ns = struct.unpack_from("<B", raw, off)[0]; off += 1
    shells = []
    for _ in range(ns):
        lvl, opac = struct.unpack_from("<ff", raw, off); off += 8
        struct.unpack_from("<fff", raw, off); off += 12
        qlo = np.array(struct.unpack_from("<fff", raw, off)); off += 12
        qhi = np.array(struct.unpack_from("<fff", raw, off)); off += 12
        nv, nf = struct.unpack_from("<II", raw, off); off += 8
        v = np.frombuffer(raw, "<u2", nv * 3, off).reshape(nv, 3).astype(np.float32); off += nv * 6
        f = np.frombuffer(raw, "<u4", nf * 3, off).reshape(nf, 3); off += nf * 12
        shells.append((lvl, qlo + (v / 65535.0) * (qhi - qlo), f))
    return shells, times[i]


def shaded(V, F, base, light=np.array([0.45, 0.35, 0.82])):
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1.0
    lam = 0.30 + 0.70 * np.clip(np.abs((n / ln[:, None]) @ (light / np.linalg.norm(light))), 0, 1)
    return np.clip(base[None, :] * lam[:, None], 0, 1), tri


def draw(ax, shells, chi):
    rng = np.random.default_rng(0)
    for si, (lvl, V, F) in enumerate(sorted(shells, key=lambda s: s[0])):
        if len(F) == 0:
            continue
        if len(F) > 24000:
            F = F[rng.choice(len(F), 24000, replace=False)]
        # 0.15*chi is the envelope, 0.6*chi the core; split at the midpoint
        inner = lvl >= 0.375 * chi
        base = np.array([0.85, 0.26, 0.13]) if inner else np.array([0.24, 0.46, 0.72])
        fc, tri = shaded(V, F, base)
        pc = Poly3DCollection(tri, facecolors=fc, linewidths=0,
                              alpha=0.97 if inner else 0.26)
        pc.set_edgecolor("none")
        ax.add_collection3d(pc)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_zlim(*YL)
    ax.set_box_aspect((XL[1] - XL[0], YL[1] - YL[0], YL[1] - YL[0]))
    ax.view_init(elev=17, azim=-66)
    ax.grid(False)
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.pane.set_alpha(0.03); a.pane.set_edgecolor("0.85")
    ax.set_xticks([0, 4, 8]); ax.set_yticks([-2, 0, 2]); ax.set_zticks([-2, 0, 2])
    ax.tick_params(labelsize=6, pad=-3, colors="0.45")


nrow, ncol = len(CHIS), len(CODES)
fig = plt.figure(figsize=(3.05 * ncol, 2.75 * nrow), dpi=175)
fig.patch.set_facecolor("white")
missing = []
for r, chi in enumerate(CHIS):
    for c, code in enumerate(CODES):
        ax = fig.add_subplot(nrow, ncol, r * ncol + c + 1, projection="3d")
        tag = "%s_%s_chi%d" % (code, LEVEL, chi)
        has_run = os.path.isfile(os.path.join(S, tag, "index.json"))
        try:
            shells, t = load_near(tag, TIME)
            if sum(len(f) for _, _, f in shells) == 0:
                raise ValueError("__MIXED__")
            draw(ax, shells, chi)
            ax.text2D(0.97, 0.06, r"$t=%.2f\,t_{\rm cc}$" % t, transform=ax.transAxes,
                      ha="right", fontsize=8, color="0.35")
        except Exception as e:
            missing.append("%s: %s" % (tag, e))
            if has_run:
                msg = "cloud fully mixed" + chr(10) + "no gas above 0.15 chi"
                colr = "0.42"
            else:
                msg, colr = "not run", "0.72"
            ax.text2D(0.5, 0.5, msg, ha="center", va="center",
                      transform=ax.transAxes, fontsize=9.5, color=colr)
            ax.set_axis_off()
        if r == 0:
            ax.text2D(0.5, 1.02, NICE.get(code, code), transform=ax.transAxes,
                      ha="center", fontsize=12.5, weight="bold")
        if c == 0:
            ax.text2D(-0.06, 0.5, r"$\chi = %d$" % chi, transform=ax.transAxes,
                      ha="center", va="center", rotation=90, fontsize=13.5, weight="bold")

LVL = {"L3": r"level 3, $64\times32\times32$", "L4": r"level 4, $128\times64\times64$",
       "L5": r"level 5, $256\times128\times128$", "L6": r"level 6, $512\times256\times256$"}
TITLE_A = 'Cloud crushing at %.1f $t_{cc}$ in a Mach 2 wind  -  ' % TIME
TITLE_B = 'density isosurfaces at $0.15\\chi$ (blue envelope) and $0.6\\chi$ (red core); identical initial conditions in every panel'
fig.suptitle(TITLE_A + LVL.get(LEVEL, LEVEL) + chr(10) + TITLE_B, fontsize=13, y=0.985)
fig.subplots_adjust(left=0.035, right=0.995, top=0.885, bottom=0.015, wspace=0.0, hspace=0.06)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor="white")
print("wrote", OUT, "%.2f MB" % (os.path.getsize(OUT) / 1e6))
for m in missing:
    print("   missing:", m)
