r"""Figure 2, Braspenning+2023 style: cloud mass evolution against time.

One panel per overdensity. Each curve is one code at a fixed resolution.
The plotted quantity is the mass of gas still denser than chi/3 -- the standard
cloud-tracking threshold -- normalised to its own value at t=0, so every code
and every chi starts at 1.0 and the curves are directly comparable.
"""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DAT = "/mnt/c/Users/kaanb/CloudCrushing/studio/data"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Users/kaanb/CloudCrushing/figures/figure2_mass.png"
LEVEL = sys.argv[2] if len(sys.argv) > 2 else "L3"

NICE = {"apk": "AthenaPK", "athpp": "Athena++", "athw": "Athena 4.2", "enzo": "Enzo",
        "flash": "FLASH 4.8", "flashx": "Flash-X", "ramses": "RAMSES", "arepo": "Arepo",
        "gas": "Gasoline", "gzmfm": "GIZMO MFM", "gzmfv": "GIZMO MFV"}
COL = {"apk": "#1f77b4", "athpp": "#4c9be8", "athw": "#7fb2e5", "enzo": "#2ca02c",
       "flash": "#d62728", "flashx": "#ff7f0e", "ramses": "#9467bd", "arepo": "#8c564b",
       "gas": "#e377c2", "gzmfm": "#17becf", "gzmfv": "#0d7f8a"}
STYLE = {"gzmfv": (0, (4, 2)), "athw": (0, (5, 2)), "athpp": (0, (1, 1))}
CHIS = [10, 100, 1000]

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.9), dpi=170, sharey=True)
fig.patch.set_facecolor("white")
found_any, report = {}, []

for ax, chi in zip(axes, CHIS):
    n = 0
    for code in NICE:
        f = os.path.join(DAT, f"diag_{code}_{LEVEL}_chi{chi}.json")
        if not os.path.isfile(f):
            continue
        try:
            d = json.load(open(f))
            s = d["series"]
            t = np.array([r["t"] for r in s], float)
            m = np.array([r["mass_frac"] for r in s], float)
        except Exception as e:
            report.append(f"{os.path.basename(f)}: {type(e).__name__}")
            continue
        if len(t) < 4 or not np.isfinite(m[0]) or m[0] <= 0:
            report.append(f"{os.path.basename(f)}: unusable (n={len(t)}, m0={m[0] if len(m) else 'NA'})")
            continue
        o = np.argsort(t); t, m = t[o], m[o]
        ax.plot(t, m / m[0], lw=2.0, color=COL[code],
                linestyle=STYLE.get(code, "-"), label=NICE[code], alpha=0.92)
        n += 1
        found_any[code] = True
    report.append(f"chi={chi}: {n} codes plotted")
    ax.set_title(rf"$\chi = {chi}$", fontsize=14, weight="bold")
    ax.set_xlabel(r"$t\ /\ t_{\rm cc}$", fontsize=12)
    ax.set_xlim(0, 5); ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.22, lw=0.6)
    ax.axhline(0.5, color="0.5", lw=0.8, ls=":", zorder=0)
    ax.text(4.92, 0.515, "half the cloud", fontsize=7.5, color="0.45", ha="right")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

axes[0].set_ylabel(r"dense mass $m(>\chi/3)\ /\ m_0$", fontsize=12)
h, l = axes[0].get_legend_handles_labels()
for a in axes[1:]:
    hh, ll = a.get_legend_handles_labels()
    for x, y in zip(hh, ll):
        if y not in l:
            h.append(x); l.append(y)
order = sorted(range(len(l)), key=lambda i: l[i])
fig.legend([h[i] for i in order], [l[i] for i in order], loc="lower center",
           ncol=min(6, len(l)), frameon=False, fontsize=10.5, bbox_to_anchor=(0.5, -0.015))

lvlname = {"L3": r"level 3 ($64\times32\times32$)", "L4": r"level 4 ($128\times64\times64$)",
           "L5": r"level 5 ($256\times128\times128$)", "L6": r"level 6 ($512\times256\times256$)"}
fig.suptitle("Survival of cold cloud material in a Mach 2 wind, " + lvlname.get(LEVEL, LEVEL),
             fontsize=14.5, y=0.99)
fig.subplots_adjust(left=0.055, right=0.99, top=0.855, bottom=0.235, wspace=0.06)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor="white")
print("wrote", OUT)
for r in report:
    print("  ", r)
