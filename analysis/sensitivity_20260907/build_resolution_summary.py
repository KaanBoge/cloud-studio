"""Summarize existing accepted reports only; never open native data or launch a solver.

Python standard library only. Outputs must be new, so prior evidence is not overwritten.
Metric values are copied from source reports, not refitted or pooled across codes.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


SOURCES = [
    ("athpp", "Athena++", "analysis/report.json", "pilot", [3, 4]),
    ("apk", "AthenaPK", "analysis/report.json", "pilot", [3, 4]),
    ("athw", "Athena 4.2", "athw/report.json", "grid", [3, 4, 5]),
    ("enzo", "Enzo", "enzo/report.json", "grid", [3, 4]),
    ("enzoe", "Enzo-E", "enzoe/report.json", "grid", [3, 4]),
    ("ramses", "RAMSES", "ramses/report.json", "grid", [3, 4]),
    ("flash", "FLASH 4.8", "flash/report.json", "grid", [3, 4]),
    ("flashx", "Flash-X", "flashx/report.json", "grid", [3, 4]),
    ("arepo", "Arepo", "arepo/report.json", "grid", [3, 4]),
    ("mfm", "GIZMO MFM", "gizmo/mfm_levels_report.json", "mfm", [3, 4]),
    ("gadget4", "Gadget-4 SPH", "gadget4/l3_report.json", "gadget", [3]),
    ("mfv", "GIZMO MFV (repaired)", "gizmo/mfv_repaired_pair.json", "mfv", [3]),
]

PENDING = [
    {"code": "Gadget-4 SPH", "level": 4, "controls": 2,
     "hold": "Full-pair storage gate; proposed raw relocation not yet approved. Full runner still needs freezing and review. Existing L4 validation must not be repeated."},
    {"code": "GIZMO MFV (repaired)", "level": 4, "controls": 2,
     "hold": "Full-pair retention budget and L4 initial-condition/timing/repair validation remain pending."},
    {"code": "Gasoline", "level": 3, "controls": 2,
     "hold": "Scientific repeatability decision required; existing field-equivalence gate failed. Do not relax it or rerun completed traces."},
    {"code": "Gasoline", "level": 4, "controls": 2,
     "hold": "Same scientific hold as L3; same-executable sharp initial-condition validation and full runner remain pending."},
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"Nonfinite or nonnumeric {label}")
    return float(value)


def physics_check(physics):
    require(physics["chi"] == 100 and physics["mach"] == 2,
            "This summary accepts fixed chi=100, Mach=2 only")


def series_info(rows, expected_count, pointer):
    require(len(rows) == expected_count, f"Unexpected native state count at {pointer}")
    times = [finite(x["t_over_tcc"], "time") for x in rows]
    masses = [finite(x["dense_mass"], "dense mass") for x in rows]
    require(all(b >= a for a, b in zip(times, times[1:])),
            f"Native times not ordered at {pointer}; do not silently sort")
    require(abs(times[0]) <= 1e-12 and 4.99 <= times[-1] <= 5.02,
            f"Incomplete or unexpected native time span at {pointer}")
    require(masses[0] > 0 and all(m >= 0 for m in masses), "Invalid mass denominator/data")
    for row, mass in zip(rows, masses):
        if "dense_mass_over_initial" in row:
            ratio = finite(row["dense_mass_over_initial"], "normalized dense mass")
            require(math.isclose(ratio, mass / masses[0], rel_tol=1e-12, abs_tol=1e-12),
                    "Report normalization changed within a run")
    return {"source_json_pointer": pointer, "native_states": len(rows),
            "first_t_over_tcc": times[0], "last_t_over_tcc": times[-1],
            "equal_header_intervals_retained": sum(a == b for a, b in zip(times, times[1:])),
            "initial_dense_mass": masses[0], "final_dense_fraction": masses[-1] / masses[0]}


def make_pair(code, name, level, source, digest, fraction, metric_pointer,
              series, expected_count, method, caveats):
    require(set(series) == {"sharp", "historical"}, "Exactly two velocity laws required")
    fraction = finite(fraction, "peak fraction")
    require(fraction >= 0, "Negative absolute peak separation")
    info = {law: series_info(rows, expected_count, pointer)
            for law, (rows, pointer) in series.items()}
    require(math.isclose(info["sharp"]["initial_dense_mass"],
                         info["historical"]["initial_dense_mass"],
                         rel_tol=1e-12, abs_tol=0), "Pair initial denominators disagree")
    require(isinstance(method, str) and "interp" in method.lower(),
            "Source must disclose scalar alignment")
    return {"code_id": code, "code": name, "level": level,
            "dimensions_streamwise": [2 ** (level + 3), 2 ** (level + 2), 2 ** (level + 2)],
            "resolution_meaning": "initial lattice, not fixed evolved resolution"
            if code in {"arepo", "gadget4", "mfm", "mfv"} else "grid dimensions",
            "initial_elements_per_cloud_radius": 2 ** (level + 3) / 20,
            "chi": 100, "mach": 2,
            "historical_velocity_law": "constant outer momentum" if code == "apk" else "tanh velocity at 1.3R",
            "sharp_velocity_law": "zero through 1.3R; constant wind outside",
            "peak_dense_mass_separation_fraction": fraction,
            "peak_dense_mass_separation_percent": 100 * fraction,
            "metric_source_json_pointer": metric_pointer,
            "metric_method_verbatim": method, "variants": info,
            "source_report": source, "source_sha256": digest,
            "source_caveats_verbatim": caveats,
            "reuse_decision": "undecided; within-code sensitivity evidence only"}


def extract(root):
    pairs, files, reports = [], {}, {}
    for code, name, source, kind, levels in SOURCES:
        if source not in reports:
            data = (root / source).read_bytes()
            reports[source] = json.loads(data)
            files[source] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        report = reports[source]
        digest = files[source]["sha256"]
        caveats = report.get("caveats", report.get("required_caveats", report.get("limitations")))
        require(caveats and all(isinstance(x, str) for x in caveats), "Missing source caveats")
        if kind not in {"pilot", "mfv"}:
            require(report["status"] == "share_with_caveats", "Unaccepted report")
        if kind in {"grid", "mfm"}:
            physics_check(report)
        if kind == "mfv":
            require(report["status"] == "passed_repaired_mfv_L3_pair", "Unrepaired/unaccepted MFV")
            physics_check(report["physics"])
        if kind == "gadget":
            require(len(report["cases"]) == 2, "Gadget pair count")
            for case in report["cases"]:
                physics_check(case["physics"])
        selected = []
        if kind in {"pilot", "grid"}:
            for index, pair in enumerate(report["pairs"]):
                if kind == "pilot" and pair["code"] != code:
                    continue
                level = pair.get("level", pair.get("initial_lattice_level"))
                selected.append(level)
                if kind == "pilot":
                    physics_check(pair)
                    require(pair["same_binary_and_only_velocity_input_differs"] is True,
                            "Pilot control identity check failed")
                    metric_key = "max_abs_curve_delta_in_units_initial_dense_mass"
                    sharp = f"{code}_L{level}_chi100_sharp13"
                    historical = f"{code}_L{level}_chi100_{pair['historical_law']}"
                    method = pair["scalar_curve_alignment"]
                    declared = pair["native_frames_per_variant"]
                else:
                    metric_key = "peak_curve_difference_over_initial_mass" if code == "arepo" else "max_abs_curve_delta_over_initial_mass"
                    sharp, historical = f"L{level}_chi100_sharp13", f"L{level}_chi100_tanh13"
                    method = report["methodology"]
                    declared = pair["frames_per_variant"]
                count = 102 if code == "enzo" else 101
                require(declared == count or declared == [count, count], "Frame metadata inconsistency")
                series = {law: (report["series"][key], f"/series/{key}")
                          for law, key in [("sharp", sharp), ("historical", historical)]}
                pairs.append(make_pair(code, name, level, source, digest, pair[metric_key],
                                       f"/pairs/{index}/{metric_key}", series, count, method, caveats))
        elif kind in {"mfm", "gadget"}:
            metrics = report["levels"] if kind == "mfm" else [dict(report["metrics"], level=report["level"])]
            for index, metric in enumerate(metrics):
                level = metric["level"]
                selected.append(level)
                cases = [(i, c) for i, c in enumerate(report["cases"]) if c["level"] == level]
                require(len(cases) == 2 and {c["mode"] for _, c in cases} == {0, 1}, "Missing/duplicate particle law")
                series = {}
                for i, case in cases:
                    require(case["cadence"]["native_snapshots"] == 101, "Particle cadence count")
                    series["sharp" if case["mode"] == 0 else "historical"] = (case["series"], f"/cases/{i}/series")
                key = "peak_curve_difference_over_initial_mass"
                pointer = f"/levels/{index}/{key}" if kind == "mfm" else f"/metrics/{key}"
                method = report["metric"] if kind == "mfm" else report["metric_definition"]
                pairs.append(make_pair(code, name, level, source, digest, metric[key], pointer,
                                       series, 101, method, caveats))
            require(report["native_states"] == sum(len(c["series"]) for c in report["cases"]),
                    "Particle native state total disagrees")
            require(report["controls"] == len(report["cases"]), "Particle control total disagrees")
        else:
            selected = [3]
            series = {}
            for law in ("sharp", "historical"):
                key = f"{law}_outputs"
                rows = []
                for output in report[key]:
                    require(output["errors"] == [], "MFV state rejected")
                    rows.append({"t_over_tcc": output["time_code"] / report["physics"]["t_cc"],
                                 "dense_mass": output["dense_mass"]})
                series[law] = (rows, f"/{key}")
            comparison = report["mass_comparison"]
            pairs.append(make_pair(code, name, 3, source, digest,
                                   comparison["maximum_absolute_separation_fraction"],
                                   "/mass_comparison/maximum_absolute_separation_fraction",
                                   series, 101, comparison["method"], caveats))
        require(sorted(selected) == levels, f"Unexpected accepted levels for {code}")
    require(len({(p['code_id'], p['level']) for p in pairs}) == len(pairs), "Duplicate code-level pair")
    states = sum(v["native_states"] for p in pairs for v in p["variants"].values())
    require(len(pairs) == 23 and states == 4650, "Frozen accepted-scope count changed; review before updating")
    return {"schema": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Completed native-code velocity sensitivity controls only; fixed chi=100, Mach=2. Not a new simulation or cross-code accuracy ranking.",
            "accepted_pairs": len(pairs), "accepted_full_controls": 2 * len(pairs),
            "native_states_in_accepted_analysis": states,
            "new_native_runs": 0, "blanket_replacement_queue": "inactive; not changed by this script",
            "sources": files, "pairs": pairs, "pending_L3_L4": PENDING,
            "pending_L3_L4_full_controls": sum(p['controls'] for p in PENDING),
            "higher_levels": "Additional storage-held work, excluded from the eight pending L3/L4 controls.",
            "verification_scope": "Report schema/count/time/normalization checks only. Earlier native validation is cited, not rerun. Raw files are not opened or modified."}


def markdown(result):
    out = ["# Velocity sensitivity: resolution summary", "",
           "## What the completed tests show", "",
           "46 accepted full controls (23 velocity-law pairs) at chi=100 and Mach=2 are represented here. "
           "They contain 4,650 native states used in the accepted analyses. No simulations were rerun to build this summary.", "",
           "The blanket replacement queue remains inactive. The effect varies by code and resolution; "
           "no historical run is automatically approved for reuse or selected for replacement.", "",
           "## Peak separation of paired dense-mass curves", "",
           "Each entry is `100 * max_t |M_dense,sharp(t) - M_dense,historical(t)| / M_dense(0)`. "
           "Dense means rho > initial cloud density / 3. Each resolution pair has its own fixed measured "
           "initial dense-mass denominator. Values are percentages of that initial mass, not exact-solution "
           "errors, statistical significance, or a ranking of codes.", "",
           "All source methods explicitly use linear interpolation of scalar mass diagnostics onto "
           "0:0.05:5 t_cc for this descriptive peak. Native states and their actual timestamps are unchanged. "
           "Equal nominal cadence does not make every native header time identical.", "",
           "| Native code | L3 | L4 | L5 | Accepted controls |",
           "| --- | ---: | ---: | ---: | ---: |"]
    for code, name, source, _, _ in SOURCES:
        rows = [p for p in result["pairs"] if p["code_id"] == code]
        values = {p["level"]: f"{p['peak_dense_mass_separation_percent']:.3f}%" for p in rows}
        out.append(f"| [{name}](../{source}) | {values.get(3, 'Pending')} | {values.get(4, 'Pending')} | {values.get(5, 'Not tested')} | {len(rows)*2} |")
    out += ["| Gasoline | Held | Held | Not tested | 0 |", "",
            "L3 = 64 x 32 x 32 (3.2 initial elements/R); L4 = 128 x 64 x 64 (6.4/R); "
            "L5 = 256 x 128 x 128 (12.8/R). Particle/moving-mesh labels describe the initial lattice, "
            "not fixed evolved spatial resolution. L6 would be 512 x 256 x 256, not 512 cubed; it is not tested here.", "",
            "## Decision limits", "",
            "Athena 4.2 changes from 13.09% to 7.59% to 8.70% across L3/L4/L5: "
            "even the available three-level sequence is not monotonically declining. "
            "The smaller L4 differences in other codes do not establish convergence, negligible impact, "
            "or validity at a different chi, Mach, resolution or numerical recipe.", "",
            "AthenaPK's historical prescription was constant outer momentum, not tanh velocity. "
            "The other accepted pairs compare historical tanh velocity with a sharp boundary at 1.3R. "
            "Within each pair, the completed source reports validate the retained native-code setup; "
            "they do not certify identical pressure and boundary conditions across codes.", "",
            "This narrow summary addresses dense-mass evolution. It does not validate simultaneous velocity "
            "diagnostics, cooling, magnetic fields, Galilean tracking, or an all-material-retained final figure. "
            "A reuse decision needs a prospective, science-specific tolerance agreed with Ryan and a "
            "provenance match to each historical run. No universal cutoff is introduced here.", "",
            "## Remaining work and unchanged holds", "",
            "Eight full L3/L4 controls remain, in addition to higher storage-held levels:", ""]
    for pending in result["pending_L3_L4"]:
        out.append(f"* {pending['code']} L{pending['level']} ({pending['controls']} controls): {pending['hold']}")
    out += ["", "Existing Gasoline diagnostic states are not one accepted 101-frame run. "
            "The original failed MFV controls are excluded; only the validated repaired MFV pair appears above.", "",
            "No raw relocation/deletion, new solver launch, threshold change or production-viewer entry "
            "is performed by this summary. Movies, meshes and these reports are not raw-data backups.", "",
            "## Source-specific caveats", ""]
    for code, name, _, _, _ in SOURCES:
        pair = next(p for p in result["pairs"] if p["code_id"] == code)
        out += [f"### {name}", ""]
        out += [f"* {text}" for text in pair["source_caveats_verbatim"]]
        out += [""]
    out += ["## Reproducibility and scope of this consolidation", "",
            "[Machine-readable summary](summary.json) preserves full-precision metrics, source-file SHA256 hashes, "
            "exact JSON pointers, actual time endpoints, counts and initial denominators. "
            "[Validation record](validation.json) records report-only tests and the scalar cross-check. "
            "[Extractor](../build_resolution_summary.py) and [tests](../test_resolution_summary.py) "
            "use Python's standard library and never open native outputs or invoke a simulation.", "",
            "To make a separately named new snapshot from the reports (existing output folders are refused):", "",
            "```text", "python build_resolution_summary.py --study-root STUDY_DIRECTORY --output-directory NEW_SUMMARY_DIRECTORY", "```", "",
            "Enzo contributes 102 native states per accepted case, including its extra terminal state; "
            "all other accepted cases contribute 101. The total counts analysis states, not every auxiliary "
            "plotfile or checkpoint present in the raw directories. Earlier source validations are referenced, "
            "not claimed to have been rerun by this extractor.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.study_root)
    result["extractor_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output_directory.mkdir(parents=False, exist_ok=False)
    (args.output_directory / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_directory / "README.md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("accepted_pairs", "accepted_full_controls", "native_states_in_accepted_analysis", "new_native_runs", "pending_L3_L4_full_controls")}))


if __name__ == "__main__":
    main()
