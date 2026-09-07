"""Generate small 3D ICs with each code's own writer and check every element.

This verifies input fields on the initial lattice. It does not certify SPH
kernel density, later adaptive resolution, or equivalence of boundary conditions.
"""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
import h5py
import numpy as np

ROOT = Path("/home/kaan/ic_audit_20260907/particle_tests")
ROOT.mkdir(parents=True, exist_ok=True)
PY = sys.executable
VW = 2 * math.sqrt(5 / 3)
NX, NY, DX = 64, 32, 20 / 64
spec = importlib.util.spec_from_file_location("gasoline_ic", "/home/kaan/codes/gasoline/ics/make_gasoline_cloudwind.py")
gasmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gasmod)
results = []
for kind in ("arepo", "gizmo", "gadget4", "gasoline"):
    for chi in (10, 100, 1000):
        run = ROOT / f"{kind}_chi{chi}"
        run.mkdir(exist_ok=False)
        ic = run / ("IC.std" if kind == "gasoline" else "IC.hdf5")
        if kind == "arepo":
            cmd = [PY, "/home/kaan/codes/arepo/runs/make_ic_cloud.py", str(run), str(chi), str(NY), "--ndim", "3", "--v-wind", repr(VW)]
        elif kind == "gizmo":
            cmd = [PY, "/home/kaan/codes/gizmo/scripts/make_cloudwind_ic.py", "--chi", str(chi), "--level", "3", "--ndims", "3", "--mass-mode", "volume", "--fname", str(ic)]
        elif kind == "gadget4":
            cmd = [PY, "/home/kaan/codes/gadget4/ics/make_g4_cloudwind.py", "--chi", str(chi), "--dim", "3", "--nx", str(NX), "--out", str(ic)]
        else:
            cmd = [PY, "/home/kaan/codes/gasoline/ics/make_gasoline_cloudwind_3d.py", "--chi", str(chi), "--dx", repr(DX), "--mass-mode", "variable", "--out", str(ic)]
        with open(run / "generate.log", "x") as out:
            subprocess.run(cmd, check=True, stdout=out, stderr=subprocess.STDOUT)
        if kind == "gasoline":
            header, gas = gasmod.read_tipsy(ic)
            pos, vel, mass, energy = gas["pos"].astype(float), gas["vel"].astype(float), gas["mass"].astype(float), gas["temp"].astype(float)
            center = (-7, 0, 0)
        else:
            with h5py.File(ic) as f:
                g = f["PartType0"]
                pos, vel, mass, energy = (g[k][:] for k in ("Coordinates", "Velocities", "Masses", "InternalEnergy"))
            center = (3, 5, 5)
        r = np.linalg.norm(pos - np.array(center), axis=1)
        expected_rho = 1 + (chi - 1) * .5 * (1 - np.tanh((r - 1) / .1))
        expected_vel = np.zeros_like(vel)
        expected_vel[:, 0] = np.where(r > 1.3, VW, 0)
        rho_lattice = mass / DX**3
        err = {"velocity_over_vwind": float(np.max(abs(vel - expected_vel)) / VW),
               "lattice_density_relative": float(np.max(abs(rho_lattice - expected_rho) / expected_rho)),
               "pressure_from_lattice_density": float(np.max(abs((5 / 3 - 1) * rho_lattice * energy - 1)))}
        result = {"code": kind, "chi": chi, "elements": len(mass), "file": str(ic),
                  "errors": err, "passed": len(mass) == NX * NY * NY and max(err.values()) < 5e-5,
                  "scope": "generated IC fields, equal-volume initial lattice only"}
        results.append(result)
        print(json.dumps(result), flush=True)
with open(ROOT / "results.json", "x") as f:
    json.dump(results, f, indent=2)
raise SystemExit(0 if all(x["passed"] for x in results) else 1)
