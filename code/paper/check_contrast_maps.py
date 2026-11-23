"""Confirm that the site picture strips used for Figure 2 belong to the calculations of Figure 5.

Compares the dense fraction history stored with each picture strip with the history in
contrast_series.json, and the colour map with matplotlib's magma.
"""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib

ROOT = Path(__file__).resolve().parent
site = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
contrast = json.loads((ROOT / 'contrast_series.json').read_text())
names = {'enzo': 'Enzo', 'enzoe': 'Enzo E', 'athpp': 'Athena++'}
for run in site['runs']:
    code, _, chi = run['id'].partition('-')
    if code not in names or chi not in ('10', '1000'):
        continue
    ref = next(r for r in contrast if r['label'] == names[code] and r['chi'] == int(chi))
    t, d = np.array(run['times']), np.array(run['dense'])
    dref = np.interp(t, ref['times'], ref['dense'])
    print(f"{run['id']:12s} points {len(t)} vs {len(ref['times'])}  max |dt| {np.max(np.abs(t - np.array(ref['times'][:len(t)]))) if len(t) == len(ref['times']) else 'n/a'}"
          f"  max |d f_d| {np.max(np.abs(d - dref)):.2e}  end {d[-1]:.4f} vs {ref['dense'][-1]:.4f}")
cm = np.array(site['colormap'], dtype=float)
mag = matplotlib.colormaps['magma'](np.linspace(0, 1, 256))[:, :3]
print('colour map largest difference from magma (of 1):', float(np.max(np.abs(cm - mag))))
