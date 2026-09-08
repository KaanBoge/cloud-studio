"""Unit and report-integration checks. No native data is read and no solvers run."""
import argparse
import bisect
import copy
import hashlib
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path

import build_resolution_summary as build


class SummaryUnitTests(unittest.TestCase):
    def rows(self):
        return [{"t_over_tcc": 0, "dense_mass": 10, "dense_mass_over_initial": 1},
                {"t_over_tcc": 5, "dense_mass": 2, "dense_mass_over_initial": .2}]

    def test_finite_series(self):
        self.assertEqual(build.series_info(self.rows(), 2, "/test")["native_states"], 2)

    def test_missing_native_frame_fails(self):
        with self.assertRaisesRegex(ValueError, "state count"):
            build.series_info(self.rows()[:1], 2, "/test")

    def test_reversed_times_not_silently_sorted(self):
        with self.assertRaisesRegex(ValueError, "not ordered"):
            build.series_info(self.rows()[::-1], 2, "/test")

    def test_duplicate_terminal_header_is_retained(self):
        rows = self.rows()
        rows.append(copy.deepcopy(rows[-1]))
        result = build.series_info(rows, 3, "/test")
        self.assertEqual(result["native_states"], 3)
        self.assertEqual(result["equal_header_intervals_retained"], 1)

    def test_nan_is_not_accepted(self):
        rows = self.rows()
        rows[1]["dense_mass"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            build.series_info(rows, 2, "/test")

    def test_zero_initial_mass_fails(self):
        rows = self.rows()
        rows[0]["dense_mass"] = 0
        with self.assertRaisesRegex(ValueError, "denominator"):
            build.series_info(rows, 2, "/test")

    def test_changed_normalization_fails(self):
        rows = self.rows()
        rows[1]["dense_mass_over_initial"] = .25
        with self.assertRaisesRegex(ValueError, "normalization"):
            build.series_info(rows, 2, "/test")

    def test_truncated_time_coverage_fails(self):
        rows = self.rows()
        rows[-1]["t_over_tcc"] = 4
        with self.assertRaisesRegex(ValueError, "time span"):
            build.series_info(rows, 2, "/test")

    def test_mach_variants_cannot_mix(self):
        with self.assertRaisesRegex(ValueError, "fixed chi"):
            build.physics_check({"chi": 100, "mach": 4.5})

    def test_chi_variants_cannot_mix(self):
        with self.assertRaisesRegex(ValueError, "fixed chi"):
            build.physics_check({"chi": 10, "mach": 2})

    def test_pair_denominators_must_match(self):
        other = self.rows()
        for row in other:
            row["dense_mass"] *= 2
        with self.assertRaisesRegex(ValueError, "denominators disagree"):
            build.make_pair("x", "x", 3, "report", "hash", .1, "/metric",
                            {"sharp": (self.rows(), "/sharp"), "historical": (other, "/old")},
                            2, "Linear interpolation", ["test caveat"])

    def test_interpolation_contract(self):
        self.assertEqual(interpolate([0, 1, 1, 2], [0, 1, 3, 4], 1), 3)
        self.assertEqual(interpolate([0, 2], [1, 3], 1), 2)


def pointer(document, path):
    for key in path.strip("/").split("/"):
        document = document[int(key)] if isinstance(document, list) else document[key]
    return document


def interpolate(times, values, t):
    """Separate scalar cross-check: same rightmost-equal and endpoint convention as numpy.interp."""
    i = bisect.bisect_right(times, t)
    if i == 0:
        return values[0]
    if i == len(times):
        return values[-1]
    a, b = i - 1, i
    return values[a] + (values[b] - values[a]) * ((t - times[a]) / (times[b] - times[a]))


def integration_checks(root, summary_path):
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    documents = {}
    for source, pin in summary["sources"].items():
        data = (root / source).read_bytes()
        build.require(hashlib.sha256(data).hexdigest() == pin["sha256"] and len(data) == pin["bytes"],
                      f"Source changed: {source}")
        documents[source] = json.loads(data)
    checks = []
    native_total = 0
    for pair in summary["pairs"]:
        report = documents[pair["source_report"]]
        metric = pointer(report, pair["metric_source_json_pointer"])
        build.require(metric == pair["peak_dense_mass_separation_fraction"], "Metric copying error")
        build.require(100 * metric == pair["peak_dense_mass_separation_percent"], "Percent conversion error")
        curves, outside = {}, []
        for law, info in pair["variants"].items():
            rows = pointer(report, info["source_json_pointer"])
            native_total += len(rows)
            build.require(len(rows) == info["native_states"], "Native count mismatch")
            times = [row["t_over_tcc"] if "t_over_tcc" in row
                     else row["time_code"] / report["physics"]["t_cc"] for row in rows]
            values = [row["dense_mass"] / info["initial_dense_mass"] for row in rows]
            build.require(times[0] == info["first_t_over_tcc"] and times[-1] == info["last_t_over_tcc"],
                          "Time endpoint changed")
            build.require(values[-1] == info["final_dense_fraction"], "Terminal fraction changed")
            # Small header-vs-nominal endpoint differences are disclosed, never retimed.
            outside.append({"law": law, "scalar_grid_queries_before_native_start": sum(i / 20 < times[0] for i in range(101)),
                            "scalar_grid_queries_after_native_end": sum(i / 20 > times[-1] for i in range(101)),
                            "maximum_endpoint_distance_tcc": max(0, times[0], 5 - times[-1])})
            curves[law] = [interpolate(times, values, i / 20) for i in range(101)]
        observed = max(abs(a - b) for a, b in zip(curves["sharp"], curves["historical"]))
        error = abs(observed - metric)
        build.require(error <= 1e-12, f"Stored scalar peak differs for {pair['code']} L{pair['level']}: {error}")
        checks.append({"code": pair["code"], "level": pair["level"], "copied_metric_exact": True,
                       "scalar_peak_recheck": observed, "absolute_recheck_difference": error,
                       "scalar_endpoint_handling": outside})
    build.require(len(checks) == 23 and native_total == 4650, "Population changed")
    build.require(summary["accepted_full_controls"] == 2 * len(checks), "Control count mismatch")
    build.require(sum(x["controls"] for x in summary["pending_L3_L4"]) == 8, "Pending count mismatch")
    build.require(summary["new_native_runs"] == 0, "No new simulations belong in this artifact")
    # Guard against accidentally publishing the old original MFV result or calling APK a tanh control.
    apk = [p for p in summary["pairs"] if p["code_id"] == "apk"]
    build.require(all(p["historical_velocity_law"] == "constant outer momentum" for p in apk), "Wrong APK law")
    mfv = [p for p in summary["pairs"] if p["code_id"] == "mfv"]
    build.require(len(mfv) == 1 and mfv[0]["source_report"] == "gizmo/mfv_repaired_pair.json", "MFV provenance")
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--summary-directory", type=Path, required=True)
    args = parser.parse_args()
    runner = unittest.TextTestRunner(verbosity=2)
    outcome = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(SummaryUnitTests))
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    summary_path = args.summary_directory / "summary.json"
    checks = integration_checks(args.study_root, summary_path)
    report = {"status": "passed_report_only_checks", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "unit_tests_passed": outcome.testsRun, "code_level_pairs_crosschecked": len(checks),
              "native_states_counted_from_stored_reports": 4650, "new_native_runs": 0,
              "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
              "test_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "maximum_scalar_peak_recheck_difference": max(c["absolute_recheck_difference"] for c in checks),
              "checks": checks,
              "limits": ["Checks use previously analyzed scalar reports, not raw fields or a new native validation.",
                         "The 1e-12 recheck tolerance tests scalar arithmetic agreement only, not physical insignificance.",
                         "Scalar interpolation holds endpoints and selects rightmost equal timestamps; native frames are never dropped or retimed.",
                         "No historical-reuse threshold, native acceptance rule, queue or raw file was changed."]}
    target = args.summary_directory / "validation.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "unit_tests_passed", "code_level_pairs_crosschecked", "maximum_scalar_peak_recheck_difference")}))


if __name__ == "__main__":
    main()
