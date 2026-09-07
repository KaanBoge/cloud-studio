r"""Figure 2, Braspenning+2023 style: cloud mass evolution against time,
with RESOLUTION OVERPLOTTED so convergence is visible.

Revised after review. Previously the level was passed on the command line and
one figure showed one resolution, which cannot show whether a code has
converged. Now every available level for every code is drawn in the same panel:
colour identifies the code, line weight and opacity identify the resolution
(faint and thin = coarse, solid and thick = finest). A code whose lines
converge as resolution rises is resolved; a code whose lines keep moving is not.

The plotted quantity is the mass of gas still denser than chi/3, the standard
cloud-tracking threshold, normalised to its own t = 0 value.

usage: fig2v2.py <out.png> [minlevel]
"""
import glob
import json
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

DAT = "/mnt/c/Users/kaanb/CloudCrushing/studio/data"
OUT = sys.argv[1] if len(sys.argv) > 1 else "figure2_mass_convergence.png"
MINLEVEL = int(sys.argv[2]) if len(sys.argv) > 2 else 2

NICE = {"apk": "AthenaPK", "athpp": "Athena++", "athw": "Athena 4.2",
        "enzo": "Enzo", "flash": "FLASH 4.8", "flashx": "Flash-X",
        "ramses": "RAMSES", "arepo": "Arepo", "gas": "Gasoline",
        "gzmfm": "GIZMO MFM", "gzmfv": "GIZMO MFV"}
COL = {"apk": "#1f77b4", "athpp": "#4c9be8", "athw": "#7fb2e5", "enzo": "#2ca02c",
       "flash": "#d62728", "flashx": "#ff7f0e", "ramses": "#9467bd",
       "arepo": "#8c564b", "gas": "#e377c2", "gzmfm": "#17becf", "gzmfv": "#0d7f8a"}
CHIS = [10, 100, 1000]

# level -> (linewidth, alpha). Coarse runs are deliberately faint: they are
# shown to demonstrate convergence, not because they are believable alone.
STYLE = {1: (0.7, 0.22), 2: (0.9, 0.32), 3: (1.2, 0.48),
         4: (1.7, 0.68), 5: (2.4, 0.90), 6: (3.1, 1.00)}

TAG = re.compile(r"^diag_([a-z0-9]+)_L(\d)_chi(\d+)\.json$")

runs = {}
for f in sorted(glob.glob(os.path.join(DAT, "diag_*.json"))):
    m = TAG.match(os.path.basename(f))
    if not m:
        continue                      # skips Mach and cooling variants
    code, lvl, chi = m.group(1), int(m.group(2)), int(m.group(3))
    if code not in NICE or lvl < MINLEVEL:
        continue
    runs.setdefault((chi, code), {})[lvl] = f

fig, axes = plt.subplots(1, 3, figsize=(15.8, 5.8), dpi=170, sharey=True)
fig.patch.set_facecolor("white")
codes_seen, levels_seen, report = set(), set(), []

for ax, chi in zip(axes, CHIS):
    n = 0
    for (c_chi, code), by_level in sorted(runs.items()):
        if c_chi != chi:
            continue
        for lvl in sorted(by_level):
            try:
                d = json.load(open(by_level[lvl]))
                s = d["series"]
                t = np.array([r["t"] for r in s], float)
                m = np.array([r["mass_frac"] for r in s], float)
            except Exception as e:
                report.append("%s: %s" % (os.path.basename(by_level[lvl]), e))
                continue
            if len(t) < 4 or not np.isfinite(m[0]) or m[0] <= 0:
                continue
            o = np.argsort(t)
            lw, al = STYLE.get(lvl, (1.5, 0.6))
            ax.plot(t[o], m[o] / m[o][0], lw=lw, alpha=al, color=COL[code],
                    solid_capstyle="round")
            codes_seen.add(code)
            levels_seen.add(lvl)
            n += 1
    report.append("chi=%d: %d curves" % (chi, n))
    ax.set_title(r"$\chi = %d$" % chi, fontsize=14, weight="bold")
    ax.set_xlabel(r"$t\ /\ t_{cc}$", fontsize=12)
    ax.set_xlim(0, 5)
    ax.set_ylim(-0.02, 1.06)
    ax.grid(alpha=0.2, lw=0.6)
    ax.axhline(0.5, color="0.55", lw=0.8, ls=":", zorder=0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

axes[0].set_ylabel(r"dense mass $m(>\chi/3)\ /\ m_0$", fontsize=12)

code_handles = [Line2D([], [], color=COL[c], lw=2.4, label=NICE[c])
                for c in sorted(codes_seen, key=lambda x: NICE[x])]
lvl_handles = [Line2D([], [], color="0.25", lw=STYLE[l][0], alpha=STYLE[l][1],
                      label="level %d  (%d$^3$-equiv)" % (l, 8 * 2 ** l))
               for l in sorted(levels_seen)]
leg1 = fig.legend(handles=code_handles, loc="lower left", ncol=6, frameon=False,
                  fontsize=10, bbox_to_anchor=(0.055, -0.015))
fig.add_artist(leg1)
fig.legend(handles=lvl_handles, loc="lower center", ncol=len(lvl_handles),
           frameon=False, fontsize=9, title="resolution", title_fontsize=9,
           bbox_to_anchor=(0.52, -0.075))

fig.suptitle("Survival of cold cloud material in a Mach 2 wind: every code, "
             "every resolution\ncolour is the code, line weight is the "
             "resolution; convergence is where the weights stop separating",
             fontsize=13.5, y=0.995)
fig.subplots_adjust(left=0.055, right=0.99, top=0.845, bottom=0.30, wspace=0.06)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
fig.savefig(OUT, facecolor="white")
print("wrote", OUT)
for r in report:
    print("  ", r)
