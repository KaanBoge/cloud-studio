# Enzo velocity-prescription sensitivity continuation

## Completed results, 8 September 2026

Both L3 and L4 pairs are complete with **102 actual native snapshots each**.
All 408 snapshots pass native field/time checks; separate direct HDF5 dense
and tracer mass sums agree with yt to less than 9.4e-16 scaled difference.
Initial density, tracer, coordinates and volumes are exactly equal within
each pair; pressure differs by at most 6.7e-16. Two analysis tests passed.
Results: [report](report.json), [mass and retention plot](mass_and_retention.png).

| Level | Sharp / historical wall time | Peak solver-child RSS | Peak mass-curve difference / initial dense mass |
| --- | --- | ---: | ---: |
| 3 | 17.9s / 17.8s | 0.39 GiB | 23.36% |
| 4 | 185.7s / 181.9s | 0.55 GiB | 3.24% |

Eight CPU MPI ranks were used. L3 final tracer fractions are 0.85855/0.85916;
L4 fractions are 0.93231/0.92677 (sharp/historical). This loss rules out calling
t=5 an all-material-retained comparison. Density-selected mass is normalized
by its fixed initial value; native time series are plotted unchanged. Only the
scalar curve-separation metric uses interpolation to 0:0.05:5 t_cc.

The worker has ended with L5 storage-held, not failed. The entire L5 pair needs
69.8 GiB plus 10 GiB safety reserve; only about 35.1 GiB was available. No native
fields were reduced or deleted. These coarse tests do not establish convergence
or a universal decision to reuse historical runs. The active continuation is
now Enzo-E; these Enzo worker records are completed records.

## Native-code provenance

This is a native Enzo experiment, not FLASH output under another label.
The isolated executable `enzo_pair` is SHA256
`28d482af94828aba1de2b097068b66c9ec80b88b53bd6405e0ff96fbecf57900`.
Only two custom problem objects were recompiled with the existing native flags;
all other native solver objects were relinked unchanged. Canonical sources,
objects, headers and executables were hash-checked and left untouched.

Both controls run the same executable. `CloudWindVelocityIC = 0` gives sharp
velocity at 1.3 R; `= 1` restores the actual historical tanh velocity law from
the pre-audit source. Density, tracer, PPM solver settings, boundary prescription,
grid, chi=100 and Mach=2 remain unchanged within each pair. The source parser
rejects other modes and echoes the selected value in amr.out.

## Checks and queue

Both v2 smoke controls passed actual native-field checks. Density, tracer,
coordinates and cell volumes are exactly equal within the pair. Recovered
pressure agrees to roundoff, while the velocity prescription demonstrably
changes. Five launcher regression tests pass. This is initial-condition proof,
not a claim that every full Enzo control has finished.

The v2 worker was launched 8 September at 00:34 local time. Read actual logs and
processes for current status; do not infer it from this dated README. It runs
L3 and L4 pairs first, then checks space for the whole L5 pair. Eight CPU MPI
ranks are used. The L5 reservation exceeds the currently available backing-drive
space; the worker will hold that pair instead of reducing native fields.

Windows record/logs: `worker_v2_windows.json`, `worker_v2_windows.log`,
`worker_v2_windows.err.log`. Native root: `/home/kaan/sensitivity_20260907/enzo`.
Status: `batch_v2.json`, `current_v2.json`. Raw: `runs_v2/`. Validated initial
tests: `smokes_v2/`, `smoke_batch_v2.json`. Launcher: `launch_windows.ps1`.
The older worker record and batch.json describe the failed first attempt.

## Retention, cadence and pressure

All six native HDF5 fields are float64, verified from the actual files.
Use the native Enzo storage budget, not the smaller Athena 4.2 VTK budget.
Every native data dump is retained. Enzo can write one extra terminal output;
record the actual distinct time count instead of silently dropping it or
manufacturing an exact count of 101. The target cadence is 0.05 t_cc through
5 t_cc. No native frame is synthesized, retimed or deleted.

Pressure is recovered from native total energy and velocity using Gamma from
the input file. Enzo's text output rounds its displayed Gamma to 1.66667;
using that rounded value in yt would introduce a spurious 5e-6 pressure offset.
The input parameters and their hash are recorded alongside every case.

## First-attempt failure and correction

The first L3 sharp attempt ended with rc=0 after only 21 data dumps. The native
cadence gate correctly rejected it as incomplete. I had set dtRestartDump to
t_cc, incorrectly treating it as a physical-time checkpoint interval.
EvolveHierarchy.C actually compares this value to elapsed wall time, writes a
restart and exits. The v2 input restores the native disabled value (-99999),
with a regression test. Raw data, checkpoint, inputs, logs and first-attempt
script are preserved. V2 starts in new directories, without overwriting or
blindly resuming that checkpoint. Enzo checkpoint resume is not certified here.

## Reproduction and limitations

Run with `/home/kaan/venv/bin/python` under WSL Ubuntu on this machine.
`build_enzo.py` records every compile/link command and input hash. Scripts are
machine-specific: paths to the native checkout and shared audited helpers are
explicit. Do not run historical queue scripts or launch a second worker.
Storage and RAM gates, exclusive production/benchmark locks and full-field
retention stay enabled. No cooling or frame shifting is enabled by this study.
Results will be interpreted within code before any cross-code reuse decision.
