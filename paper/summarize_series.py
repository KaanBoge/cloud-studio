"""Print the numbers quoted in the text from plot_series.json and boundary_control_series.json."""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / 'plot_series.json').read_text())
order = ['athpp', 'apk', 'athw', 'enzo', 'enzoe', 'ramses', 'flash', 'flashx', 'arepo', 'mfm', 'mfv', 'gadget4']
grid = order[:8]
S = {(r['code'], r['level']): (np.array(r['times']), np.array(r['dense'])) for r in rows}


def at(code, level, t):
    x, y = S[(code, level)]
    return float(np.interp(t, x, y))


print('f_d at 5 t_cc (n = 32, 64, 128) and at 1, 2, 3, 4 t_cc (n = 128)')
for c in order:
    e = [at(c, l, 5.0) for l in (3, 4, 5)]
    m = [at(c, 5, t) for t in (1, 2, 3, 4)]
    print(f'{c:8s} ' + ' '.join(f'{v:.4f}' for v in e) + '   |  ' + ' '.join(f'{v:.4f}' for v in m))

print('\nlargest |f_d(n=128) - f_d(n=64)| over the history, percentage points, and its time')
for c in order:
    x5, y5 = S[(c, 5)]
    x4, y4 = S[(c, 4)]
    keep = x5 <= min(x4[-1], 5.0)
    d = np.abs(y5[keep] - np.interp(x5[keep], x4, y4))
    i = int(np.argmax(d))
    print(f'{c:8s} {100 * d[i]:6.2f} at {x5[keep][i]:.2f} t_cc')

print('\nspread across methods at n = 128 (min, max, max-min) at fixed times')
for t in (1, 2, 3, 4, 5):
    v = {c: at(c, 5, t) for c in order}
    g = [v[c] for c in grid]
    o = [v[c] for c in order if c not in ('mfm',)]
    print(f't = {t}: all {min(v.values()):.3f} to {max(v.values()):.3f} ({min(v, key=v.get)}, {max(v, key=v.get)});'
          f' grid {min(g):.3f} to {max(g):.3f}; all but MFM {min(o):.3f} to {max(o):.3f}')
for lvl in (3, 4, 5):
    g = [at(c, lvl, 5.0) for c in grid]
    print(f'grid methods at 5 t_cc, level {lvl}: {min(g):.3f} to {max(g):.3f}')

print('\ntime at which f_d first falls below 0.5 at n = 128')
for c in order:
    x, y = S[(c, 5)]
    below = np.where(y < 0.5)[0]
    if len(below):
        i = below[0]
        t = x[i - 1] + (0.5 - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1])
        print(f'{c:8s} {t:.2f}')
    else:
        print(f'{c:8s} stays above 0.5 (minimum {y.min():.3f} at {x[int(np.argmin(y))]:.2f})')

print('\nAthenaPK against Athena++ at n = 128: largest difference',
      float(np.max(np.abs(S[("apk", 5)][1] - np.interp(S[("apk", 5)][0], *S[("athpp", 5)])))))

b = json.loads((ROOT / 'boundary_control_series.json').read_text())
B = {(r['n'], r['box']): r for r in b}
print('\nboundary control, f_d at 1..5 t_cc and dense velocity at 5 t_cc')
for n in (32, 64, 128):
    for box in ('open', 'p3', 'px'):
        r = B[(n, box)]
        x = np.array(r['times'])
        v = [float(np.interp(t, x, r['dense'])) for t in (1, 2, 3, 4, 5)]
        vel = np.array([np.nan if q is None else q for q in r['dense_velocity']], dtype=float)
        print(n, box, ' '.join(f'{q:.4f}' for q in v), ' vel(5) %.3f' % float(np.interp(5.0, x, vel)),
              ' mass(5)/mass(0) %.4f' % r['total_mass'][-1],
              ' P_up min %.3f at %.2f' % (min(r['upstream_pressure']), x[int(np.argmin(r['upstream_pressure']))]),
              ' rho_up min %.3f' % min(r['upstream_density']))
