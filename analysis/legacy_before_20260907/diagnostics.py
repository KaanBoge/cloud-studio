"""Extract the quantitative time series every cloud-crushing paper actually plots.

The 744 GB of raw fields exists so that numbers like these can be computed. The
numbers themselves are a few kB per run, so unlike the fields they CAN be
published, and they are what makes the comparison reproducible: anyone can
re-plot the whole twelve-code study from this file without the raw data.

Per snapshot: surviving dense-gas mass fraction, centre of mass, peak density,
and mixing fraction, all in the normalised units the campaign uses.

Usage: diagnostics.py <run_id> <kind> <chi> <tcc> <files...>
"""
import glob
import json
import os
import sys

import numpy as np
import yt

yt.set_log_level(50)

RID, KIND = sys.argv[1], sys.argv[2]
CHI, TCC = float(sys.argv[3]), float(sys.argv[4])

# The run's own parameter file is authoritative. Values on the command line are
# a fallback for runs whose inputs have been swept, and are reported as such.
# Passing chi and t_cc blind is how FLASH 4.8, whose R_cloud is 0.1 rather than
# 1.0, ended up normalised by a t_cc ten times too large.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from run_params import find_params, derive, report
    _dir = os.path.dirname(os.path.abspath(sys.argv[5])) if len(sys.argv) > 5 else None
    # snapshots may sit one level below the run directory (Enzo DD####, RAMSES
    # output_#####, the particle codes' output/)
    _p = None
    for _cand in ([_dir, os.path.dirname(_dir)] if _dir else []):
        if _cand:
            _p = derive(find_params(_cand))
            if _p:
                break
    print("=== %s (%s) ===" % (RID, KIND))
    _ok = report(_p, expected_chi=CHI, expected_tcc=TCC)
    if _p and _p.get("chi"):
        CHI = _p["chi"]
    if _p and _p.get("t_cc"):
        TCC = _p["t_cc"]
    if not _ok:
        print("  [params] using the values from the parameter file, not argv")
    print("  [params] USING chi = %g, t_cc = %.6f" % (CHI, TCC))
except ImportError:
    print("=== %s (%s) ===" % (RID, KIND))
    print("  [params] run_params.py not importable; USING argv values "
          "chi = %g, t_cc = %.6f (UNVERIFIED)" % (CHI, TCC))
FILES = sys.argv[5:]
OUT = "/mnt/c/Users/kaanb/CloudCrushing/studio/data/diag_%s.json" % RID

rows = []
for fn in FILES:
    try:
        ds = yt.load(fn)
        ad = ds.all_data()
        rho = np.array(ad[("gas", "density")], dtype=np.float64)
        vol = np.array(ad[("gas", "cell_volume")], dtype=np.float64)
    except Exception as e:
        print("skip %s: %s" % (os.path.basename(fn), e))
        continue

    m = rho * vol
    mtot = float(m.sum())
    # "dense" is the standard cloud-tracking threshold: a third of the initial
    # cloud density, which follows material that is still recognisably cloud
    dense = rho > (CHI / 3.0)
    mdense = float(m[dense].sum())

    # cloud material initially carries mass chi * V_cloud; normalise by that so
    # every chi and every resolution is directly comparable
    try:
        x = np.array(ad[("gas", "x")], dtype=np.float64)
        xcom = float((m[dense] * x[dense]).sum() / mdense) if mdense > 0 else float("nan")
    except Exception:
        xcom = float("nan")

    # mixing fraction: gas at intermediate density is cloud that has been
    # stirred into the wind rather than destroyed outright
    mixed = (rho > 2.0) & (rho < CHI / 3.0)
    fmix = float(m[mixed].sum() / mtot) if mtot > 0 else 0.0

    rows.append({
        "t": round(float(ds.current_time) / TCC, 4),
        "mass_frac": round(mdense / mtot, 6) if mtot > 0 else 0.0,
        "xcom": round(xcom, 4) if xcom == xcom else None,
        "rho_max": round(float(rho.max()), 4),
        "mix_frac": round(fmix, 6),
    })
    del ad, ds, rho, vol, m

if rows:
    with open(OUT, "w") as f:
        json.dump({"run": RID, "kind": KIND, "chi": CHI, "t_cc": TCC,
                   "columns": ["t_over_tcc", "dense_mass_fraction",
                               "dense_x_centre_of_mass", "peak_density",
                               "mixed_mass_fraction"],
                   "series": rows}, f)
    print("wrote %s (%d points, %.1f kB)" % (OUT, len(rows), os.path.getsize(OUT) / 1024.0))
else:
    print("no readable snapshots for %s" % RID)
