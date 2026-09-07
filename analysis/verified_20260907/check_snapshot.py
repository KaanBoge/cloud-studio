"""Test native t=0 grid output against the explicit cloud-wind prescription.

Every leaf cell is tested at its own center. A coarse ray is not an IC test.
This verifies saved fields, not the solver's later accuracy or boundary fluxes.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import yt
from run_params import parse_file

yt.set_log_level(40)


def check(path, paramfile, kind, center, expected_dims, tolerance=3e-5):
    p = parse_file(paramfile)
    required = ("chi", "r_cloud", "rho_wind", "p_wind", "v_wind", "t_cc", "rv_scale")
    if not p or any(p.get(k) is None for k in required):
        raise ValueError(f"Missing required metadata: {p}")
    ds = yt.load(path)
    time = float(ds.current_time.to("code_time"))
    if not math.isclose(time, 0, abs_tol=1e-12 * p["t_cc"]):
        raise ValueError(f"Expected t=0; snapshot time is {time}")
    ad = ds.all_data()
    coords = np.stack([ad["index", ax].to_value("code_length") for ax in "xyz"], axis=1)
    rho = ad["gas", "density"].to_value("code_density")
    velocity = np.stack([ad["gas", "velocity_" + ax].to_value("code_velocity") for ax in "xyz"], axis=1)
    pressure = ad["gas", "pressure"].to_value("code_pressure")
    radius = np.linalg.norm(coords - np.array(center), axis=1)
    f = .5 * (1 - np.tanh((radius / p["r_cloud"] - 1) / .1))
    expected_rho = p["rho_wind"] * (1 + (p["chi"] - 1) * f)
    expected_v = np.zeros_like(velocity)
    axis = 1 if kind == "apk" else 0
    expected_v[:, axis] = np.where(radius > p["rv_scale"] * p["r_cloud"], p["v_wind"], 0)
    errors = {
        "density_relative_max": float(np.max(np.abs(rho - expected_rho) / expected_rho)),
        "velocity_error_over_vwind_max": float(np.max(np.abs(velocity - expected_v)) / p["v_wind"]),
        "pressure_relative_max": float(np.max(np.abs(pressure - p["p_wind"])) / p["p_wind"]),
    }
    expected_native_dims = expected_dims if kind != "apk" else (expected_dims[1], expected_dims[0], expected_dims[2])
    widths = np.stack([ad["index", "d" + ax].to_value("code_length") for ax in "xyz"], axis=1)
    spans = ds.domain_width.to_value("code_length")
    actual_dims = np.rint(spans / widths.min(axis=0)).astype(int).tolist()
    expected_spans = np.array((20, 10, 10) if axis == 0 else (10, 20, 10)) * p["r_cloud"]
    uniform = bool(np.allclose(widths, widths[0], rtol=1e-6))
    good_grid = actual_dims == list(expected_native_dims) and len(rho) == int(np.prod(expected_native_dims)) and uniform
    valid = all(np.all(np.isfinite(x)) for x in (rho, velocity, pressure))
    passed = bool(valid and good_grid and np.allclose(spans, expected_spans) and all(x < tolerance for x in errors.values()))
    return {"passed": passed, "snapshot": str(path), "parameters": p, "time_code": time,
            "cells": len(rho), "native_dimensions": actual_dims, "uniform_grid": uniform,
            "domain_width_over_R": (spans / p["r_cloud"]).tolist(), "errors": errors,
            "scope": "t=0 density, velocity, pressure, dimensions and domain; no claim of full-run validation"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--params", required=True)
    ap.add_argument("--kind", required=True)
    ap.add_argument("--center", nargs=3, type=float, default=[0, 0, 0])
    ap.add_argument("--dims", nargs=3, type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    result = check(a.snapshot, a.params, a.kind, a.center, a.dims)
    with open(a.out, "x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)
