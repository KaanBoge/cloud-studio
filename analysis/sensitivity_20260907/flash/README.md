# FLASH 4.8 native velocity sensitivity controls

## Completed results, 8 September 2026

All four L3/L4 controls are complete and analyzed, with 101 distinct full-state
times each. Every native field and time passed checks. Independent yt mass
sums agree with the direct native reader within 5.6e-16 relative difference for
all 404 checkpoints. Seven launcher and two analysis tests pass. See
[the report](report.json), [mass curves](mass_evolution.png) and [QA review](VALIDATION.md).

| Level | Sharp / historical solver wall time | Peak sampled solver-child RSS | Peak curve separation / initial dense mass |
| --- | --- | ---: | ---: |
| 3 | 36.8s / 36.8s | 13.41 GiB | 10.37% |
| 4 | 484.3s / 478.7s | 13.49 GiB | 6.17% |

Eight MPI workers were observed fully busy during L4. Timings exclude the
subsequent validation/analysis. Initial density, grid and unchanged auxiliary
fields are exact within each pair; recovered thermodynamic fields differ by
at most 7.1e-16 relatively. At L3 both final dense masses are zero despite
earlier curve separation. L4 final sharp/historical fractions are 0.04027/0.05484.
These are sensitivity differences, not accuracy errors or convergence proof.

All native checkpoint and plot data (about 17 GiB) remain saved. Actual final
times span 5.00162-5.00390 t_cc and are not relabeled. No tracer is present;
no all-material-retained claim can be made. L5 was held without launching:
153.31 GiB plus 10 GiB reserve was required, versus 35.67 GiB available.

## Completed worker records

The guarded L3/L4 queue started at 02:09 local time using eight native MPI ranks.
Both L3/L4 pairs and their four-control analysis are now complete. No FLASH
worker remains active. These experiments are not production viewer entries.
Read actual processes, Windows `worker_windows.*` and native
`/home/kaan/sensitivity_20260907/flash/batch.json` / `current.json` for live status.
The Windows-owned launcher PID was 28680; do not use a saved PID without checking.

## Native executable and unchanged conditions

This is the native FLASH 4.8 solver, not a substitute implementation. The pinned
executable `flash4_pair` has SHA256
`009ef9442480ce64a62168b1d5592a09e01181e1103b42b3db7dcc80209ec88e`.
An isolated problem unit `CloudCrushSensitivity_20260908` and separate object
directory preserve all original problem sources, objects and binaries. Their
hashes are checked in `build.json`. Existing native compile flags, block size
16x16x16, MAXBLOCKS=1200 and solver precision remain unchanged.

Both variants use the same executable and inputs except `sim_velocityIC`:
0 selects sharp velocity at 1.3 R, 1 restores the actual historical tanh law.
The latter is verified in the pre-audit source, not inferred from a paper.
Density retains the existing tanh edge of width 0.1 R. Thermal pressure and
other physical/numerical parameters are unchanged; total energy follows velocity.

Fixed chi=100, Mach=2, gamma=5/3, wind density=pressure=1. Native FLASH R=0.1,
center=(0.3,0.5,0.5), domain=[0,2]x[0,1]x[0,1], equivalent to the common
20x10x10 R wind tunnel. Therefore t_cc=0.3872983346207417 code-time units.
L3=64x32x32 with lrefine_min=lrefine_max=2; L4=128x64x64 with internal level 3;
L5=256x128x128 with internal level 4. This is uniform resolution, not active AMR.
The existing order-3 unsplit HLLC controls, CFL=0.45, limiters, dual-energy
settings, custom wind inflow and other five outflow faces are preserved.

## Native-field verification

Seven launcher/initial-condition tests and two analysis tests pass. Both native
smoke controls completed, with t=0 and an evolved full-state checkpoint. Density,
coordinates, volumes and unchanged auxiliary fields match exactly within the
pair. The velocity difference reaches 1.289 in native units. Pressure, internal
energy, temperature and effective gamma differ by at most 6.9e-16 relatively;
the energy change matches the kinetic-energy change to 8.9e-16 absolute error.
An actual invalid-mode run exits with code 1 before writing native data.

The first strict pair check incorrectly required recovered thermodynamic fields
to be bitwise identical. Its failure record is retained as
`smoke_pair_strict_check.json`; the same native datasets were rechecked, not rerun.
The validator now permits only 1e-13 relative recovery roundoff, while still
requiring exact density/grid equality. Tests reject a real pressure change.

The native HDF5 reader checks all leaf cells, full grid coverage without overlap,
cell coordinates/widths, every saved field's precision and finiteness, positive
density/pressure, the native runtime-mode echo and every actual timestamp.
Independent yt sums agree exactly for all four smoke checkpoints. Full-run yt
cross-checks and mass-curve analysis also passed for all 404 completed states.

## Data retention and an explicit output-policy change

The existing plotfiles retain their six float32 fields: density, pressure,
temperature and three velocities. No plot field or precision is reduced.
In addition, full-state float64 checkpoints are saved at every plot time,
targeting 101 distinct times through 5 t_cc, rather than only occasional restart
times. All 13 native checkpoint fields are retained, including energies,
thermodynamic and auxiliary fields. Native compute precision remains double.

`rolling_checkpoint=10000` replaces the old two-file cycling policy so this
experiment does not overwrite saved states. This is an explicit retention-policy
change applied identically to both fresh controls, not a change to the physics.
Initial and terminal forced outputs are retained too; any exact duplicate-time
files are listed separately, not counted as extra evolution or deleted.
Times are recorded from native metadata, never reassigned to nominal cadence.

The native FLASH recipe has **no passive tracer**. Density-selected mass is
measurable, but tracer-based material retention is unavailable. Do not claim
that all cloud material remains in the box at the final time. Cooling and frame
tracking are not enabled or validated by this sensitivity experiment.

## Resources and queue safety

The native eight-rank smoke uses about 13.42 GiB solver-child RSS because this
build preallocates MAXBLOCKS=1200 arrays. The launcher requires 19 GiB available
RAM before a case, plus both production/benchmark locks and host/guest storage
checks. It never launches a second heavy solver or build alongside the current one.

Measured native checkpoint-plus-plot sizes give conservative whole-pair budgets
of 2.89 GiB for L3, 19.60 GiB for L4 and 153.31 GiB for L5, each plus a 10 GiB
free-space reserve. L5 will be held with only about 35 GiB free on Windows C.
Do not reduce fields, weaken the storage budget or assume ext4 free space is
free space on the Windows VHDX backing drive. All raw data is retained.

## Files and reproduction

Windows source/scripts: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907/flash`.
Native runs: `/home/kaan/sensitivity_20260907/flash/runs`.
The `planned_inputs` directory contains L3/L4/L5 input examples, not proof that
all levels ran. Use `build_flash.py`, `test_flash.py`, `verify_setup.py`,
`test_analysis_flash.py` and `verify_yt_smokes.py` for setup and checks.
`launch_windows.ps1` owns the WSL process lifetime and keeps Windows disk checks
working. Do not relaunch it when its record already exists or resume an
uncertified checkpoint. Existing partial cases require explicit review.

After the worker ends, `analyze_flash.py` reads the actual run parameters and
levels from the recorded inputs, independently cross-checks every full-state
mass sum using yt and plots resolution overlays at native times. Dense mass is
rho>rho_cloud_initial/3 with a fixed measured initial denominator. Only the
scalar curve-separation metric interpolates to 0:0.05:5 t_cc. Coarse L3/L4
controls do not establish convergence or universally certify historical reuse.

Scripts are machine-specific and depend on the parent study's `build.py` and
`/home/kaan/verified_20260907` helpers. No email was sent. Publication covers
scripts, input examples and verification evidence, not native raw datasets.
The deployment check verifies the remote commit, Pages build and live files;
an incorrect analysis publication can be corrected without touching native data.
