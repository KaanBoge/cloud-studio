"""Morphology figures at n = 128 and 5 t_cc from the saved column density maps.

Figure 1: the twelve methods at chi = 100. Figure 2: Athena++, Enzo and Enzo-E at chi = 10 and 1000.
Figure 7 (upper part): the AthenaPK radiative pair, cooling on and off.
Each map is the total gas column density divided by rho_c0 R, on a logarithmic scale from
0.008 to 5 with the magma colour map, edge on (looking across the wind, wind from left to
right) and face on (looking along the wind). The maps are read from the published picture
strips (one 128 pixel row per saved state; the last row is t = 5 t_cc), whose colour map and
range are stored in catalog.json next to them.

  python plot_morphology.py <folder with one subfolder per run> <site catalog.json> <site picture folder>
"""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import ListedColormap, LogNorm
from PIL import Image

ROOT = Path(__file__).resolve().parent
STAGE = Path(sys.argv[1])
SITE_CATALOG = Path(sys.argv[2])
SITE_PICS = Path(sys.argv[3])
FONT = 9
plt.rcParams.update({'font.size': FONT, 'pdf.fonttype': 42, 'ps.fonttype': 42})

TWELVE = [('athpp-100-l5', 'Athena++'), ('apk-100-l5', 'AthenaPK'), ('athw-100-l5', 'Athena 4.2'),
          ('enzo-100-l5', 'Enzo'), ('enzoe-100-l5', 'Enzo-E'), ('ramses-100-l5', 'RAMSES'),
          ('flash-100-l5', 'FLASH 4.8'), ('flashx-100-l5', 'Flash-X'), ('arepo-100-l5', 'Arepo'),
          ('mfm-100-l5', 'GIZMO MFM'), ('mfv-100-l5', 'GIZMO MFV'), ('gadget4-100-l5', 'GADGET-4*')]
CONTRAST = [('athpp-10', 'Athena++'), ('enzo-10', 'Enzo'), ('enzoe-10', 'Enzo-E'),
            ('athpp-1000', 'Athena++'), ('enzo-1000', 'Enzo'), ('enzoe-1000', 'Enzo-E')]
COOLING = [('apk-hlle-on', 'Cooling on', 0.882), ('apk-hlle-off', 'Cooling off', 0.105)]


def last_row(path, nframes):
    im = np.asarray(Image.open(path).convert('RGB'))
    assert im.shape[0] == 128 * nframes, (path, im.shape, nframes)
    return im[128 * (nframes - 1):128 * nframes]


def colourbar(fig, ax, cmap):
    sm = plt.cm.ScalarMappable(norm=LogNorm(0.008, 5), cmap=cmap)
    cb = fig.colorbar(sm, cax=ax, orientation='horizontal', extend='both')
    cb.set_label(r'$\Sigma/(\rho_{\rm c,0}R)$')


def panel_grid(entries, out, cmap, nrow, ncol_groups, size):
    fig = plt.figure(figsize=size)
    gs = fig.add_gridspec(nrow + 1, 3 * ncol_groups - 1, height_ratios=[1] * nrow + [0.13],
                          width_ratios=([2, 1, 0.1] * ncol_groups)[:-1], hspace=0.05, wspace=0.03,
                          left=0.01, right=0.99, top=0.99, bottom=0.1)
    outline = [pe.withStroke(linewidth=2.0, foreground='black')]
    for k, (edge, face, label) in enumerate(entries):
        r, g = k % nrow, k // nrow
        a = fig.add_subplot(gs[r, 3 * g])
        b = fig.add_subplot(gs[r, 3 * g + 1])
        a.imshow(edge, interpolation='nearest', aspect='equal')
        b.imshow(face, interpolation='nearest', aspect='equal')
        for ax in (a, b):
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
        a.text(0.025, 0.93, label, transform=a.transAxes, ha='left', va='top', color='white',
               fontsize=FONT, path_effects=outline)
    if ncol_groups == 1:
        cax = fig.add_subplot(gs[nrow, 0:2])
    else:
        cax = fig.add_subplot(gs[nrow, 1:3 * ncol_groups - 2])
    colourbar(fig, cax, cmap)
    fig.savefig(ROOT / 'figures' / (out + '.pdf'), dpi=300, bbox_inches='tight', pad_inches=0.03)
    fig.savefig(ROOT / 'qa' / (out + '_preview.png'), dpi=110, bbox_inches='tight', pad_inches=0.03)
    plt.close(fig)


def site_entry(runs, rid, chi):
    """Last state of a run: from its run folder when it has one, else from the site picture folder."""
    folder = STAGE / rid
    if (folder / 'entry.json').exists():
        run = json.loads((folder / 'entry.json').read_text(encoding='utf-8'))
        edge_path, face_path = folder / 'edge.png', folder / 'face.png'
    else:
        run = runs[rid]
        edge_path, face_path = SITE_PICS / f'{rid}-edge.png', SITE_PICS / f'{rid}-face.png'
    assert run['color_range'] == [0.008, 5] and run['n'] == 128 and run['chi'] == chi, rid
    assert abs(run['frames'][-1]['time'] - 5.0) < 0.01, rid
    n = len(run['frames'])
    return last_row(edge_path, n), last_row(face_path, n), run


def main():
    site = json.loads(SITE_CATALOG.read_text(encoding='utf-8'))
    table = np.array(site['colormap'], dtype=float)
    assert table.shape == (256, 3) and table.max() <= 1.0
    cmap = ListedColormap(table)
    runs = {r['id']: r for r in site['runs']}

    twelve = []
    for rid, label in TWELVE:
        entry = json.loads((STAGE / rid / 'entry.json').read_text(encoding='utf-8'))
        n = len(entry['frames'])
        assert entry['color_range'] == [0.008, 5] and n == 101 and entry['n'] == 128 and entry['chi'] == 100, rid
        assert abs(entry['frames'][-1]['time'] - 5.0) < 0.01, rid
        twelve.append((last_row(STAGE / rid / 'edge.png', n), last_row(STAGE / rid / 'face.png', n), label))
    panel_grid(twelve, 'morphology_n128', cmap, 6, 2, (6.3, 6.6))

    contrast = []
    for rid, label in CONTRAST:
        chi = int(rid.split('-')[1])
        edge, face, run = site_entry(runs, rid, chi)
        contrast.append((edge, face, rf'{label}, $\chi={chi}$'))
    panel_grid(contrast, 'morphology_contrast', cmap, 3, 2, (6.4, 3.8))

    cooling = []
    for rid, label, end in COOLING:
        edge, face, run = site_entry(runs, rid, 100)
        assert abs(run['dense'][-1] - end) < 0.001, (rid, run['dense'][-1])
        cooling.append((edge, face, label))
    panel_grid(cooling, 'cooling_morphology_maps', cmap, 2, 1, (4.6, 3.3))
    print('ok')


if __name__ == '__main__':
    main()
