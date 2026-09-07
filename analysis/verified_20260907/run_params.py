"""Read physical parameters without silently inventing a radius or time scale.

Native units are retained. AthenaPK CGS inputs are converted with its unit block.
Missing fields remain None. Known constants in the custom Athena pgens are
explicitly recorded under assumptions; no other code inherits those defaults.
"""
import glob
import hashlib
import json
import math
import os
import re

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?"


def read_values(path):
    with open(path, encoding="utf-8", errors="strict") as f:
        raw = f.read()
    values, sections, section = {}, {}, ""
    for line in raw.splitlines():
        line = re.split(r"#|!|//", line, maxsplit=1)[0].strip()
        if not line:
            continue
        if line.startswith("<") and line.endswith(">"):
            section = line[1:-1].lower()
            continue
        if line.startswith("&"):
            section = line[1:].strip().lower()
            continue
        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*(" + NUMBER + r")(?=\s|,|/|$)", line):
            key, value = m.group(1).lower(), float(m.group(2).replace("D", "e").replace("d", "e"))
            values[key] = value
            sections[(section, key)] = value
    return raw, values, sections


def parse_file(path):
    raw, v, s = read_values(path)
    p = {"source": os.path.abspath(path), "parameter_sha256": hashlib.sha256(raw.encode()).hexdigest(),
         "assumptions": [], "gamma": v.get("gamma"), "r_cloud": None,
         "rho_wind": None, "p_wind": None, "v_wind": None, "chi": None,
         "rv_scale": None, "tmax": None, "output_dt": None, "mach": None}
    if "rho_cloud_cgs" in v:
        p["kind"] = "apk"
        length, mass, time = (v.get("code_" + name + "_cgs") for name in ("length", "mass", "time"))
        rw = v.get("rho_wind_cgs")
        p["chi"] = v["rho_cloud_cgs"] / rw if rw and rw > 0 else None
        if all(x and x > 0 for x in (length, mass, time)):
            p["r_cloud"] = v["r0_cgs"] / length if "r0_cgs" in v else None
            p["v_wind"] = v["v_wind_cgs"] * time / length if "v_wind_cgs" in v else None
            p["rho_wind"] = rw * length**3 / mass if rw else None
            helium, temp = v.get("he_mass_fraction"), v.get("t_wind_cgs")
            if helium is not None and temp is not None and rw:
                if not 0 <= helium <= 1:
                    raise ValueError("Invalid He_mass_fraction")
                mu = 1 / (helium * .75 + (1 - helium) * 2)
                # Exact constants/convention of this checkout's units.hpp and hydro.cpp.
                mh, kb = 1.007947 * 1.660538921e-24, 1.3806488e-16
                mbar_over_kb_code = mu * mh / kb * (length / time)**2
                p["p_wind"] = temp * p["rho_wind"] / mbar_over_kb_code
                p["assumptions"].append("AthenaPK checkout units.hpp constants; fully ionized H/He mu from hydro.cpp")
        p["rv_scale"] = s.get(("problem/cloud", "rv_scale"))
        p["tmax"] = s.get(("parthenon/time", "tlim"))
        p["output_dt"] = s.get(("parthenon/output1", "dt"))
        p["time_input_in_tcc"] = bool(re.search(r"rescale_code_time_to_tcc\s*=\s*true", raw, re.I))
    elif "drat" in v and "mach" in v:
        p.update(kind="athena", chi=v["drat"], mach=v["mach"], r_cloud=1.0,
                 rho_wind=1.0, p_wind=1.0, rv_scale=v.get("rv_scale"),
                 tmax=v.get("tlim"), output_dt=s.get(("output2", "dt")))
        p["assumptions"] = ["custom cloud_wind pgen fixes R=1, rho_wind=1 and P_wind=1"]
    elif "cloudwindchi" in v:
        p.update(kind="enzo", chi=v["cloudwindchi"], r_cloud=v.get("cloudwindcloudradius"),
                 rho_wind=v.get("cloudwindambientdensity"), p_wind=v.get("cloudwindambientpressure"),
                 v_wind=v.get("cloudwindvelocity"), rv_scale=v.get("cloudwindrvscale"),
                 tmax=v.get("stoptime"), output_dt=v.get("dtdatadump"))
    elif "sim_rhocloud" in v:
        rw = v.get("sim_rhoambient")
        p.update(kind="flash", chi=v["sim_rhocloud"] / rw if rw and rw > 0 else None,
                 rho_wind=rw, p_wind=v.get("sim_pambient"), r_cloud=v.get("sim_rcloud"),
                 v_wind=v.get("sim_windvel"), rv_scale=v.get("sim_rvscale"),
                 gamma=v.get("sim_gamma", v.get("gamma")), tmax=v.get("tmax"),
                 output_dt=v.get("plotfileintervaltime"))
    elif "chi" in v and "cloudwind_params" in raw.lower():
        p.update(kind="ramses", chi=v["chi"], r_cloud=v.get("r_cloud"),
                 rho_wind=v.get("rho_wind"), p_wind=v.get("p_wind"),
                 v_wind=v.get("v_wind"), rv_scale=v.get("rv_scale"),
                 tmax=v.get("tend"), output_dt=v.get("delta_tout"))
    else:
        return None
    return derive(p)


def derive(p, r_cloud=None):
    if not p:
        return None
    p = dict(p)
    # A caller may supply an explicitly documented radius, but never replace one read from file.
    if p.get("r_cloud") is None and r_cloud is not None:
        p["r_cloud"] = r_cloud
        p["assumptions"] = p.get("assumptions", []) + ["R supplied explicitly by caller"]
    gamma, pressure, rho = p.get("gamma"), p.get("p_wind"), p.get("rho_wind")
    cs = math.sqrt(gamma * pressure / rho) if all(x and x > 0 for x in (gamma, pressure, rho)) else None
    if p.get("v_wind") is None and p.get("mach") is not None and cs:
        p["v_wind"] = p["mach"] * cs
    if p.get("v_wind") is not None and cs:
        p["mach"] = p["v_wind"] / cs
    chi, radius, speed = p.get("chi"), p.get("r_cloud"), p.get("v_wind")
    if all(x is not None and math.isfinite(x) and x > 0 for x in (chi, radius, speed)):
        p["t_cc"] = math.sqrt(chi) * radius / speed
    else:
        p["t_cc"] = None
    return p


def find_params(run_dir):
    candidates = []
    for pattern in ("athinput*", "*.enzo", "flash.par", "*.nml"):
        for path in sorted(glob.glob(os.path.join(run_dir, pattern))):
            if os.path.isfile(path) and not any(x in os.path.basename(path) for x in ("backup", ".bak", ".reference", ".orig")):
                got = parse_file(path)
                if got:
                    candidates.append(got)
    if not candidates:
        return None
    reference = candidates[0]
    for other in candidates[1:]:
        for key in ("chi", "r_cloud", "v_wind", "gamma", "tmax"):
            a, b = reference.get(key), other.get(key)
            if a is not None and b is not None and not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-14):
                raise ValueError(f"Ambiguous parameter files: {reference['source']} and {other['source']} disagree on {key}")
    return reference


def report(p, expected_chi=None, expected_tcc=None, tol=1e-6):
    print(json.dumps(p, indent=2, allow_nan=False))
    if not p:
        return False
    ok = p.get("chi") is not None and p.get("t_cc") is not None
    for key, expected in (("chi", expected_chi), ("t_cc", expected_tcc)):
        got = p.get(key)
        if expected is not None and got is not None and not math.isclose(got, expected, rel_tol=tol, abs_tol=1e-12):
            print(f"PARAMETER MISMATCH: {key}: file={got:.12g}, requested={expected:.12g}")
            ok = False
    return ok


if __name__ == "__main__":
    import sys
    for directory in sys.argv[1:]:
        report(find_params(directory))
