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

RID, KIND, CHI, TCC = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
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
