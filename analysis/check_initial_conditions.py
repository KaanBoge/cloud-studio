"""Verify a run's initial conditions against the matched specification.

Revised after review: the wind speed used to be hardcoded as vw = 2.582, which
is the Mach 2 value and silently wrong for any other Mach number. It is now read
from the run's own parameter file, along with chi and the velocity transition
radius, and everything used is printed.

What is checked, along a ray through the cloud centre:

  density   rho = 1 + (chi - 1) * 0.5*(1 - tanh((r - R)/0.1))
            so rho should pass through its half value at r = R.

  velocity  vx  = v_wind * (1 - 0.5*(1 - tanh((r - rv*R)/0.1)))
            so vx should pass through half the wind speed at r = rv*R,
            which is deliberately OUTSIDE the density edge (rv = 1.3).

The two edges are offset on purpose: if the velocity transition sat at the
density edge, one cell would hold both cloud-density gas and full-speed wind,
and every code would resolve that differently from the first step.

usage: check_ic.py <snapshot> [run_dir]
"""
import os
import sys

import numpy as np
import yt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_params import find_params, derive, report

yt.set_log_level(50)

snap = sys.argv[1]
run_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(snap))

p = derive(find_params(run_dir)) or derive(find_params(os.path.dirname(run_dir)))
report(p)
if not p:
    sys.exit("no parameter file found next to %s; refusing to guess the wind "
             "speed, which is what the previous version of this script did" % snap)

vw = p["v_wind"]
chi = p["chi"]
rv = p.get("rv_scale") or 1.3
R = 1.0

ds = yt.load(snap)

# The initial condition can only be checked at t = 0. Reading a late snapshot
# shows a destroyed cloud and reports OUT OF SPEC for no reason, which is the
# same class of silent wrong answer as hardcoding the wind speed.
_t = float(ds.current_time)
if _t > 1e-6:
    print()
    print("  REFUSING: this snapshot is at t = %.4f, not t = 0." % _t)
    print("  The IC check is only meaningful on the first dump of a run.")
    sys.exit(2)
print("\n  domain  %s to %s" % (np.array(ds.domain_left_edge),
                                np.array(ds.domain_right_edge)))
print("  base    %s   max AMR level %d" % (ds.domain_dimensions, ds.index.max_level))
print("  effective %s" % (ds.domain_dimensions * 2 ** ds.index.max_level))

# ray outward from the cloud centre, transverse so it crosses both edges cleanly
ray = ds.ray([0.0, 0.0, 0.0], [0.0, 0.0, 5.0])
z = np.array(ray["gas", "z"])
o = np.argsort(z)
z = z[o]
rho = np.array(ray["gas", "density"])[o]
vx = np.array(ray["gas", "velocity_x"])[o]

print("\n     r      rho       vx")
for r in (0.5, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.6, 2.0):
    i = int(np.argmin(abs(z - r)))
    print("  %5.2f  %8.4f  %8.4f" % (z[i], rho[i], vx[i]))

half_rho = 0.5 * (1.0 + chi)
i = int(np.argmin(abs(rho - half_rho)))
j = int(np.argmin(abs(vx - 0.5 * vw)))
r_rho, r_v = z[i], z[j]

print("\n  density half value %.3f found at r = %.4f   expected %.3f" % (half_rho, r_rho, R))
print("  velocity half value %.3f found at r = %.4f   expected %.3f" % (0.5 * vw, r_v, rv * R))

tol = 0.12
ok = abs(r_rho - R) < tol and abs(r_v - rv * R) < tol
print("\n  separation of the two edges: %.3f R   (specification %.3f R)"
      % (r_v - r_rho, rv - 1.0))
print("  VERDICT: %s" % ("matches the specification" if ok else
                         "OUT OF SPEC, this run is not harmonised with the others"))
sys.exit(0 if ok else 1)
