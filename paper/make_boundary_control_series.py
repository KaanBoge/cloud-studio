"""Collect the boundary control histories from the per snapshot reductions.

Input: the reduction of the nine Athena++ calculations (three boundary treatments at
n = 32, 64 and 128), one record per saved state. Output: boundary_control_series.json
next to this script, in the units used by the figures (times in cloud crushing times).
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1])  # the per snapshot reduction (series.json) of the nine calculations

data = json.loads(SOURCE.read_text())
t_cc = data['constants']['t_cc']
v_w = data['constants']['v_w']
boxes = {'open': 'inflow and outflow', 'p3': 'periodic on all faces', 'px': 'periodic along the wind'}
out = []
for level, n in ((3, 32), (4, 64), (5, 128)):
    for key, label in boxes.items():
        s = data['runs'][f'{key}_L{level}']['series']
        out.append({
            'code': 'athpp', 'n': n, 'box': key, 'label': label,
            'times': [t / t_cc for t in s['time']],
            'dense': s['f_d'],
            'dense_velocity': s['dense_vx_over_vw'],
            'total_mass': [m / s['mass'][0] for m in s['mass']],
            'upstream_density': s['up_rho_mean'],
            'upstream_pressure': s['up_press_mean'],
            'upstream_velocity': [v / v_w for v in s['up_vx_mean']],
        })
(ROOT / 'boundary_control_series.json').write_text(json.dumps(out, indent=1))
print(len(out), 'series written')
