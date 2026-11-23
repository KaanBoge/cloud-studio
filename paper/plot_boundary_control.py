"""Plot the boundary control: one solver, three treatments of the domain faces.

Reads boundary_control_series.json (saved reductions) and writes
figures/boundary_control.pdf. Run with Python 3 and matplotlib.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 11,
                     'pdf.fonttype': 42, 'ps.fonttype': 42})

STYLE = {'open': ('#222222', '-', 'Inflow and outflow'),
         'px': ('#3a7ebf', '-.', 'Periodic along the wind'),
         'p3': ('#a63a2a', '--', 'Periodic on all faces')}


def main():
    series = json.loads((ROOT / 'boundary_control_series.json').read_text())
    fig, axs = plt.subplots(2, 3, figsize=(10, 5.4), sharex=True, sharey='row', layout='constrained')
    for col, n in enumerate((32, 64, 128)):
        top, low = axs[0, col], axs[1, col]
        for box in ('open', 'px', 'p3'):
            row = next(r for r in series if r['n'] == n and r['box'] == box)
            color, style, label = STYLE[box]
            top.plot(row['times'], row['dense'], color=color, ls=style, lw=1.7, label=label)
            low.plot(row['times'], row['upstream_pressure'], color=color, ls=style, lw=1.7)
        top.text(0.96, 0.93, f'$n={n}$', transform=top.transAxes, ha='right', va='top')
        top.set(xlim=(0, 5), ylim=(0, 1.1))
        low.set(xlim=(0, 5))
        low.margins(y=0.06)
        for ax in (top, low):
            ax.grid(alpha=.18)
    axs[0, 0].set_ylabel(r'$M_{\rm d}/M_{\rm d}(0)$')
    axs[1, 0].set_ylabel(r'$P_{\rm up}/P_{\rm w,0}$')
    axs[0, 2].legend(loc='lower left', frameon=False, handlelength=2.6)
    fig.supxlabel(r'$t/t_{\rm cc}$')
    fig.savefig(FIG / 'boundary_control.pdf', bbox_inches='tight')
    fig.savefig(ROOT / 'qa' / 'boundary_control_preview.png', dpi=130, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
