"""Read the physical setup back out of a run's own parameter file.

Written in response to review feedback: chi and t_cc were being passed on the
command line, so a typo produced a silently wrong normalisation. Everything that
can be read from the run directory is now read from it, and whatever a script
ends up using is printed so an inconsistency is visible rather than silent.

Each code writes its own format, so each gets its own small parser:

  Athena++ / Athena 4.2   athinput*        Mach, drat, rv_scale, tlim
  AthenaPK                athinput         v_wind_cgs, rho_cloud_cgs, tlim
  Enzo                    *.enzo           CloudWindVelocity, CloudWindChi
  FLASH / Flash-X         flash.par        sim_windVel, sim_rhoCloud, tmax
  RAMSES                  *.nml            (namelist; boxlen, tend)

Usage as a module:
    from run_params import find_params, derive
    p = find_params("/path/to/run/dir")
    print(p["chi"], p["v_wind"], p["t_cc"])
"""
import glob
import math
import os
import re

GAMMA = 5.0 / 3.0
# ambient state is rho = 1, P = 1 by construction, so c_s = sqrt(gamma)
C_S = math.sqrt(GAMMA)


def _grep(path, pattern, cast=float):
    try:
        with open(path, "r", errors="ignore") as fh:
            for line in fh:
                m = re.match(pattern, line.strip(), re.IGNORECASE)
                if m:
                    return cast(m.group(1))
    except OSError:
        return None
    return None


def _athena(path):
    """Athena++ and Athena 4.2 both take Mach and drat."""
    mach = _grep(path, r"^Mach\s*=\s*([0-9.eE+-]+)")
    chi = _grep(path, r"^drat\s*=\s*([0-9.eE+-]+)")
    rv = _grep(path, r"^rv_scale\s*=\s*([0-9.eE+-]+)")
    tlim = _grep(path, r"^tlim\s*=\s*([0-9.eE+-]+)")
    if mach is None or chi is None:
        return None
    return {"mach": mach, "v_wind": mach * C_S, "chi": chi,
            "rv_scale": rv, "tmax": tlim, "source": path}


def _athenapk(path):
    v = _grep(path, r"^v_wind_cgs\s*=\s*([0-9.eE+-]+)")
    chi = _grep(path, r"^rho_cloud_cgs\s*=\s*([0-9.eE+-]+)")
    tlim = _grep(path, r"^tlim\s*=\s*([0-9.eE+-]+)")
    if v is None or chi is None:
        return None
    return {"mach": v / C_S, "v_wind": v, "chi": chi,
            "rv_scale": None, "tmax": tlim, "source": path}


def _enzo(path):
    v = _grep(path, r"^CloudWindVelocity\s*=\s*([0-9.eE+-]+)")
    chi = _grep(path, r"^CloudWindChi\s*=\s*([0-9.eE+-]+)")
    rv = _grep(path, r"^CloudWindRvScale\s*=\s*([0-9.eE+-]+)")
    tmax = _grep(path, r"^StopTime\s*=\s*([0-9.eE+-]+)")
    if v is None or chi is None:
        return None
    return {"mach": v / C_S, "v_wind": v, "chi": chi,
            "rv_scale": rv, "tmax": tmax, "source": path}


def _flash(path):
    v = _grep(path, r"^sim_windVel\s*=\s*([0-9.eE+-]+)")
    rho_c = _grep(path, r"^sim_rhoCloud\s*=\s*([0-9.eE+-]+)")
    rho_a = _grep(path, r"^sim_rhoAmbient\s*=\s*([0-9.eE+-]+)") or 1.0
    rv = _grep(path, r"^sim_rvScale\s*=\s*([0-9.eE+-]+)")
    tmax = _grep(path, r"^tmax\s*=\s*([0-9.eE+-]+)")
    if v is None or rho_c is None:
        return None
    return {"mach": v / C_S, "v_wind": v, "chi": rho_c / rho_a,
            "rv_scale": rv, "tmax": tmax, "source": path}


PARSERS = [
    ("athinput.cloud_wind", _athena),
    ("athinput", None),            # decided below: AthenaPK vs Athena
    ("*.enzo", _enzo),
    ("flash.par", _flash),
]


def find_params(run_dir):
    """Locate and parse whichever parameter file this run directory holds."""
    # AthenaPK and the Athena family share the name "athinput"; tell them apart
    # by which keys are present rather than by directory naming.
    for name in ("athinput.cloud_wind", "athinput"):
        p = os.path.join(run_dir, name)
        if os.path.isfile(p):
            got = _athenapk(p) or _athena(p)
            if got:
                return got
    for pat, fn in (("*.enzo", _enzo), ("flash.par", _flash)):
        for p in sorted(glob.glob(os.path.join(run_dir, pat))):
            if p.endswith(".reference"):
                continue
            got = fn(p)
            if got:
                return got
    for p in sorted(glob.glob(os.path.join(run_dir, "*.nml"))):
        chi = _grep(p, r".*chi\s*=\s*([0-9.eE+-]+)")
        if chi:
            return {"mach": None, "v_wind": None, "chi": chi,
                    "rv_scale": None, "tmax": None, "source": p}
    return None


def derive(p, r_cloud=1.0):
    """t_cc = sqrt(chi) * R_cloud / v_wind, added in place."""
    if p and p.get("chi") and p.get("v_wind"):
        p["t_cc"] = math.sqrt(p["chi"]) * r_cloud / p["v_wind"]
    return p


def report(p, expected_chi=None, expected_tcc=None, tol=1e-3):
    """Print what will actually be used, and flag any disagreement."""
    if not p:
        print("  [params] no parameter file found; using values passed on the "
              "command line, which are NOT verified against the run")
        return False
    print("  [params] read from %s" % p["source"])
    for k in ("mach", "v_wind", "chi", "rv_scale", "tmax", "t_cc"):
        if p.get(k) is not None:
            print("  [params]   %-9s = %.6g" % (k, p[k]))
    ok = True
    if expected_chi is not None and p.get("chi"):
        if abs(p["chi"] - expected_chi) > tol * max(1.0, expected_chi):
            print("  [params] MISMATCH: chi in file is %g, script was told %g"
                  % (p["chi"], expected_chi))
            ok = False
    if expected_tcc is not None and p.get("t_cc"):
        if abs(p["t_cc"] - expected_tcc) > tol * max(1.0, expected_tcc):
            print("  [params] MISMATCH: t_cc from file is %.6g, script was "
                  "told %.6g" % (p["t_cc"], expected_tcc))
            ok = False
    return ok


if __name__ == "__main__":
    import sys
    for d in sys.argv[1:]:
        print(d)
        report(derive(find_params(d)))
