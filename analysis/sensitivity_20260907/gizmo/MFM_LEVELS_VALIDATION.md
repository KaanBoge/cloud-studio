# Native GIZMO MFM L3/L4 delivery validation

8 September 2026. **Share with caveats.** Four completed MFM controls, 404
distinct native states. The two newly accepted L4 controls bring the study
total to 42; the failed MFV controls are not included.

## Question and comparison

At fixed chi=100 and Mach=2, compare the actual historical tanh velocity law
with the sharp velocity boundary, separately at each initial resolution.
L3 is 64 x 32 x 32 (3.2 elements/R); L4 is 128 x 64 x 64 (6.4 elements/R).
Within a pair, nonvelocity IC arrays, binary, physical metadata and native
parameters are identical. Across levels, only MaxMemSize and the six
resolution-scaled softenings differ in the parameter files. L4 softenings
are half the L3 values. Original CFL, precision, method and timestep cap
are unchanged; diagnostic tiny-step caps never entered full runs.

## Verified calculations

All four cases have 101 distinct native header times from 0 to 5 t_cc.
All 404 native states passed schema, finite/positive-field and independent
yt mass-sum checks. The combined analyzer freshly verified every raw hash,
count, time and direct mass sum against those ledgers, with zero reported
relative discrepancy. This validates these calculations, not exact physics.

Dense mass selects rho > rho_cloud_initial/3. The denominator is the same
measured initial dense mass within each pair, fixed for every timestep:

| Initial level | Initial dense mass | Peak separation / initial mass | Final sharp fraction | Final historical fraction |
| --- | ---: | ---: | ---: | ---: |
| L3 | 409.90798235 | 3.97902649% | 0.97111140 | 0.97909955 |
| L4 | 398.48968780 | 0.95497179% | 0.96486376 | 0.96951694 |

The plotted curves use all actual native times. Only the scalar peak uses
declared linear interpolation onto 0:0.05:5 t_cc, first peaking at 0.75 and
2.1 t_cc respectively. No simulation frame was retimed or interpolated.
Each resolution has its own measured initial denominator, never a new one
at each time. The zero-based, labeled plot was visually inspected.

Six analysis tests cover the fixed denominator, mismatched initial masses,
missing terminal time, unchanged source rows, contradictory equal-time
diagnostics, and rejection of incomplete/failed L4 batches. The separate
L4 preparation passed nine unit tests and 16 native validation outputs;
the original 15 helper/runner tests also passed.

## Resource measurements

L4 sharp/historical solver times were 794.8416/791.1622 seconds. Each used
eight MPI workers, with median sampled busy CPU 8.0002 workers. Peak summed
solver-child RSS was 1.6258/1.6361 GiB. This is not total host memory.
Solver times exclude validation and publication. These native builds are
CPU-only. Eight versus sixteen workers has not yet been benchmarked here;
no speedup or higher-quality result is claimed from additional RAM usage.

## Required limitations

Two coarse resolutions do not establish convergence or a universal rule for
reusing historical runs. The smaller L4 difference is not an accuracy error
against an exact solution. Original fully periodic boundaries, variable
particle masses and kernel-derived density/pressure are retained, so this
is not a matched grid-code inflow/outflow baseline. Initial kernel pressure
deviation is at most about 0.09215% and identical within each pair.

The conserved native output velocity is staggered relative to its header
time. Separate per-level timestep tests support that convention; no stored
velocity was altered. Simultaneous velocity diagnostics remain unvalidated.
There is no passive material tracer or all-material-retained image claim.
Both MFV L3 attempts have invalid stored-energy states and remain separately
documented, never filtered into this accepted MFM comparison.

## Reproducibility and publication

[The report](mfm_levels_report.json) contains all scalar series, native file
hashes, resource measurements, source ledger hashes and the analysis/plot
hashes. [The completed L4 ledger](mfm_l4_batch.json) records full native
checks. [The analyzer](analyze_mfm_levels.py) and
[six tests](test_mfm_levels_analysis.py) are supplied with the result.

Native data remains at `/home/kaan/sensitivity_20260907/gizmo`; the immutable
new analysis is `analysis_mfm_l3_l4_v1`. Existing output directories must
not be overwritten or rerun. All raw data, ICs, logs, restart generations and
failed attempts are retained. This public analysis package is not a raw
backup and does not add production entries to the 3D viewer.

Before claiming publication, require an advanced matching remote commit,
successful Pages deployment, and live SHA256 verification of every changed
file. If publication differs, correct or revert only the publication commit;
do not alter native simulation data.
