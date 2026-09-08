# Repaired MFV passes the late-onset diagnostic

8 September 2026. **The repaired historical-law Level 3 case reached 5 t_cc
with all 101 native frames finite and positive.** The old stored zero-energy
failure did not recur in this case. Terminal conserved plus pending mass
also passes the unchanged prospective accounting check.

This is one repair diagnostic, not an accepted sharp/historical comparison
pair or proof of convergence. The study total remains **44 accepted controls**.

## What was actually run

Native GIZMO MFV, chi100, Mach2, initial 64 x 32 x 32 equal-volume lattice,
65536 variable-mass elements. Both IC and parameter files were copied
byte-for-byte from the retained original historical run. The same native
periodic box, density/velocity laws, numerics, floors, precision and output
settings were kept. Only the previously tested one-assignment repair binary
was used; no further native source change or rebuild occurred.

The actual input stops at code time19.364916731037084, with interval
0.19364916731037085: 5 t_cc and 0.05 t_cc respectively. Every actual native
time remains saved, including22 frames at or after the old failure onset
near3.95 t_cc. No frame was fabricated, removed, retimed or substituted.

| Measured result | Value |
| --- | ---: |
| Native outputs | 101 |
| Nonpositive/nonfinite stored-energy states | 0 |
| Minimum stored internal energy across all times | 0.01050080545 |
| Minimum stored internal energy at5 t_cc | 0.02374329232 |
| Terminal double internal-energy minimum | 0.02374329161 |
| Initial total mass | 2425.245532028377 |
| Terminal coupled MassTrue sum | 2425.1325285823345 |
| Pending dMass sum | 0.1130034460422868 |
| Combined mass-ledger residual | -7.7169e-14 |
| Prospective engineering allowance | 0.0022435210 |
| Particles with changed conserved mass | 65536 |
| Native synchronization steps | 1985 |

The combined mass ledger includes pending transfers, as established in the
[short native test](MFV_SHORT_VALIDATION.md). Float32 predicted snapshot mass
is not substituted for that ledger. The allowance is an engineering check,
not a rigorous arbitrary-flux error bound or a physical-accuracy measure.

Initial nonvelocity fields match the original native full-run initial state
exactly. All101 direct raw mass sums agree with independent yt sums, with
zero reported discrepancy. Every raw frame and all eight terminal restart
hashes were independently rechecked after the corrected review. Final
restarts have positive finite conserved/predicted energy, pressure and mass.

## Resources and preservation

Observed solver-process wall time was126.99seconds, about2m07s. Median
sampled CPU work was8.000 busy workers across eight MPI ranks; peak summed
child RSS was582569984bytes (about0.543GiB). This native solver is CPU-only.
These are measured resources, not a universal speedup claim or Level6 ETA.

The new native directory occupies559486302bytes, including all outputs,
IC, logs and restart files. The preflight reserved1.096GiB plus separate
10GiB host/guest reserves. The600second wall cap and resource guards did not
trigger. Neither old native data nor any canonical executable was modified.

Native data: `/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/onset_native_v1`.
Frozen runner: adjacent `onset_runner_v1`. Successful read-only correction:
`onset_review_v2`. All completed/failed directories are retained; do not
relaunch them or overwrite their reports.

## Checker corrections, explicitly retained

The first audit incorrectly assumed the optional29-bit native clock. This
build automatically enables60-bit time. All snapshot checks passed, but the
terminal clock assertion failed before mass accounting. The source-derived
correction verifies the native eight-byte clock type, all terminal headers,
and a60-bit interval of1.679638783e-17. The corrected, tighter cadence
allowance is3.4433e-14 code time; maximum measured schedule offset is3.55e-15.
No simulation rerun or timestamp change was needed.

The first correction then hit a report-serialization error on a NumPy
boolean, after its numerical checks. Version2 converts report scalar types
and adds a regression test. The original plan, frozen runner, needs_review
report and partial first review remain saved. Eleven launch tests and seven
corrected-review tests pass. See [the correction record](MFV_ONSET_CLOCK_REVIEW.md).

## Next step and limits

Validate the sharp IC and paired native initial fields on this same repaired
binary, then review a guarded paired continuation. Reuse this historical
diagnostic only if its complete recipe satisfies that pair's requirements;
do not blindly rerun it. The old failed MFV cases remain separate evidence.

This one historical L3 result does not establish other-law or higher-level
success, universal quality, simultaneous saved velocities, matching pressure
or boundaries across codes, cooling, frame tracking or material retention.
These diagnostic scripts/results are not new production 3D viewer entries
and are not raw-data backups.

Files: [prospective plan](MFV_ONSET_PLAN.md), [frozen plan](onset_plan.json),
[native execution](onset_native_result.json), [original audit](onset_initial_validation.json),
[successful correction](onset_clock_review.json), [original runner](mfv_onset.py),
[read-only correction](review_mfv_onset_v2.py), [launch tests](test_mfv_onset.py),
and [clock/report tests](test_mfv_onset_clock_v2.py).
