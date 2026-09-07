# Enzo-E native velocity sensitivity tests

## Completed L3/L4 results

All four controls are now complete, with 101 actual native times each. A second
per-block mass sum agrees with the assembled full-grid calculation for all 404
snapshots to less than 5e-16 scaled difference. Initial density and internal
energy agree exactly; initial recovered pressure differs by at most 6.7e-16.
Results: [report](report.json), [mass plot](mass_evolution.png).

| Level | Sharp / historical wall time | Sampled peak solver RSS | Peak mass-curve difference / initial dense mass |
| --- | --- | ---: | ---: |
| 3 | 19.7s / 19.7s | 0.085 GiB | 8.21% |
| 4 | 195.0s / 195.1s | 0.161 GiB | 6.35% |

Eight native worker threads were used. No tracer retention was inferred.
These are coarse within-code sensitivity results, not proof of convergence or
permission to universally reuse old runs. The worker ended with L5 storage-held:
74.72 GiB plus 10 GiB safety reserve was required, versus 34.92 GiB available.
The records below are now completed worker records; no Enzo-E solver is active.

The paired queue was launched 8 September 2026 at 01:05 local time. Inspect
`worker_windows.json`, `worker_windows.log`, `worker_windows.err.log`, actual
processes and native `batch.json` for current status. Native root:
`/home/kaan/sensitivity_20260907/enzoe`; raw outputs are in `runs/`.
L3/L4 pairs precede the guarded L5 pair. No other native worker is duplicated.

The existing Enzo-E executable was copied and hash-verified, not rebuilt.
It runs directly with `+p8`: eight Charm++ Multicore worker threads, not MPI.
Eight root blocks use the same 3D uniform grid and layout within each pair.
The solver, density profile, PPM controls and boundaries are unchanged within
the pair. Only initial velocity and consistent kinetic energy expressions differ.
`build.json` records the native binary and source-input hashes.

The historical tanh velocity at 1.3 R is verified in the actual existing 2D
cloud-wind input. Here that radial law is extended spherically in the audited
3D setup, at fixed chi=100 and Mach=2. This is not a claim that a historical
3D production run was recovered. The corrected case has sharp velocity at
1.3 R. Native initial density and internal energy agree exactly between the
controls. Recovered pressure and velocities pass analytic checks.

## Important diagnostic limit

The existing native recipe has **no passive tracer**. No tracer was added or
invented for this pair. Density-selected mass can be compared, but tracer-based
retention cannot be measured and t=5 cannot be certified as retaining all cloud
material. `tracer_mass` is null and the limitation is explicit in each report.
The reader excludes ghost cells using native start/end indices and verifies
coverage of every uniform active cell exactly once before measuring mass.
All seven native fields, including the saved ghost regions, remain on disk.

## Validation and safeguards

Two v2 native smokes contain both t=0 and evolved outputs and passed paired
field checks. Five launcher tests passed. The first historical smoke was
rejected by Cello's expression parser because subtraction lacked whitespace:
`1.0-0.5` was read as a signed number. Spacing is corrected and regression
tested; the failed smoke and its logs remain in `smokes/`. The passing tests
are in `smokes_v2/`, recorded in `smoke_batch_v2.json`.

Production targets 101 actual native times through 5 t_cc. Missing or repeated
times are failures, not filled by duplicate frames. Seven-field HDF5 float64
output was verified in the native smoke. The disk budget includes saved ghost
cells; the L5 pair is expected to hold until enough backing-drive storage is
available. No physics, precision, output cadence or storage guard is weakened.

Scripts are machine-specific and use shared audited helpers. The launcher is
Windows-owned to keep WSL disk-check interoperability alive. Exclusive locks,
RAM and host/guest storage checks apply. No cooling, frame shifting, checkpoint
resume, destructive sweeper or application-closing behavior is enabled.
