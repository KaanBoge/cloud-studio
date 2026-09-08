# Flash-X native velocity sensitivity controls

## Completed results, 8 September 2026

All four L3/L4 controls are now complete and analyzed, with 101 distinct native
times each. Every saved field/time passed checks. Independent yt sums agree
with all 404 native checkpoint mass sums within 4.1e-16 relative discrepancy.
Seven launcher tests and two analysis tests pass. See [report](report.json),
[mass curves](mass_evolution.png) and [QA review](VALIDATION.md).

| Level | Sharp / historical solver wall time | Peak sampled solver-child RSS | Peak curve separation / initial dense mass |
| --- | --- | ---: | ---: |
| 3 | 34.6s / 34.2s | 11.34 GiB | 10.13% |
| 4 | 440.5s / 435.2s | 11.47 GiB | 6.54% |

Eight MPI workers were observed at 99.9% CPU each during L4. Timings exclude
subsequent validation/analysis. Native density/grid/auxiliary fields match
exactly within each initial pair; thermodynamic recovery differences remain
below 6.9e-16. Actual terminal times span 5.00005-5.00294 t_cc, not relabeled.
Final dense fractions are zero for both L3 cases and 0.03488/0.05886 at L4.
These are sensitivity differences, not accuracy errors or convergence proof.

All native raw (about 14 GiB) is retained. There is no tracer, so material
retention is unknown. The worker ended with L5 storage-held: 129.79 GiB plus
10 GiB reserve was needed, versus 35.58 GiB available. No raw was thinned.

## Completed worker records

The Windows-owned L3/L4 queue started at 02:47 local time using eight MPI
ranks. L5 follows only if its entire retained pair fits the storage budget.
L3/L4 full analysis is complete and no Flash-X worker remains active. Check native
`/home/kaan/sensitivity_20260907/flashx/batch.json` and `current.json`, not a
stale saved PID. Windows launcher/logs are `worker_windows.json/log/err.log`;
the launch PID was 4064. Do not relaunch or edit the loaded worker while active.

## Native solver and controlled difference

This executable is built from `/home/kaan/codes/flashx`, not FLASH 4.8.
The custom CloudWind problem uses Flash-X's native tile-based API and existing
boundary routine. An isolated `CloudWindSensitivity_20260908` problem unit and
`object_sensitivity_20260908` build preserve canonical sources and binaries;
all existing problem/build files were hash-checked unchanged in `build.json`.

Pinned `flashx_pair` SHA256:
`e1e6f29b890a1843575984915061147aff677fd444f0d928b7ac3ce7e4192746`.
Existing build flags are retained: 3D, PARAMESH, parallel HDF5, 16x16x16 blocks,
MAXBLOCKS=1200, native double precision. Build commands and hashes are recorded.
The launcher and HDF5 validation scaffold are adapted from the FLASH tests,
but native field sets, geometry, parameters and executable are Flash-X's own.

Within a pair the same executable and parameter file are used, except for
`sim_velocityIC`: 0 sharp velocity at 1.3 R, 1 the actual historical tanh
velocity law recovered from the pre-audit Flash-X source. Total energy follows
the selected kinetic energy at unchanged pressure. The historical tanh law is
source-proven, not attributed to a paper. Density retains its tanh width 0.1 R.

Both cases use chi=100, Mach=2, gamma=5/3, R=1, wind density=pressure=1 and
v_wind=2*sqrt(5/3). The box is [-3,17]x[-5,5]x[-5,5], with cloud at zero.
L3 is 64x32x32 (internal level 2), L4 is 128x64x64 (internal level 3), and
L5 is 256x128x128 (internal level 4). Min/max refinement levels are equal.
The existing order-3 unsplit HLLC solver, CFL=0.4, MC limiter, dual-energy
settings, wind inflow and five outflow faces remain identical within pairs.

## Checks before the full queue

Seven launcher/IC tests and two curve-analysis tests passed. An actual invalid
mode run exits with code 1 before any HDF5 output. Both native smoke cases
have t=0 and an evolved full-state checkpoint. Initial density, coordinates,
volumes and unchanged auxiliary fields are exact within the pair. Recovered
pressure/internal-energy/temperature/effective-gamma differences are below
6.9e-16 relative; consistent kinetic-energy difference error is below 8.9e-16.
The selected velocity law matches actual native fields and differs between
cases by up to 1.289 in native velocity units.

The reader checks complete cubic-grid coverage without gaps/overlap, native
runtime mode, every saved field's precision/finiteness, positive density and
pressure, and actual times. Independent yt mass sums agree for all four smoke
checkpoints within 1.88e-16 relative discrepancy. yt uses its FLASH-format
frontend to read Flash-X's compatible HDF5 output; it is not the solver.

## Full data, times and limitations

All eleven native checkpoint fields are float64: dens, eint, ener, gamc, game,
pres, shok, temp, velx, vely, velz. Original five-field float32 plotfiles retain
dens, pres and all three velocities. Neither native compute nor saved-field
precision is reduced. All native blocks and auxiliary fields remain stored.

Both fresh controls explicitly save full-state checkpoints at every plot time
(0.05 t_cc through 5 t_cc) and use `rolling_checkpoint=10000` so previous
states are not overwritten. This output-retention change is identical in the
pair. Actual native times and forced duplicate-time files remain untouched;
duplicates are listed separately, not counted as extra evolution. There is no
synthetic frame interpolation or replay. Target: 101 distinct native times.

This native recipe has no passive tracer. Tracer retention is null and final
in-box cloud-material retention cannot be certified. Density-selected mass
uses rho>rho_cloud_initial/3 and the fixed measured initial mass denominator.
The future analysis plots actual native times and explicitly interpolates
only scalar curve-difference metrics to 0:0.05:5 t_cc. L3/L4 are coarse tests,
not proof of convergence, a universal reuse decision or complete paper figures.
Cooling and frame shifting are not enabled by this experiment.

## Resources, safeguards and reproduction

Native smoke solver times were 2.42s/2.38s, with sampled solver-child RSS
11.29/11.32 GiB. These are not total Windows RAM measurements or full-run ETAs.
The worker keeps its conservative 19 GiB MemAvailable preflight, exclusive
production/benchmark locks and both guest and Windows backing-drive guards.
No competing heavy worker/build, legacy sweeper or unvalidated restart runs.

Whole-pair budgets from actual checkpoint+plot sizes, 103 output slots and
30% headroom: L3 2.52 GiB, L4 16.66 GiB, L5 129.79 GiB, each plus 10 GiB free
reserve. L5 is expected to be held with about 35 GiB free on Windows C.
No native output is deleted or thinned to defeat that storage constraint.

Scripts are machine-specific. Run with `/home/kaan/venv/bin/python` in WSL:
`test_flashx.py`, `test_analysis_flashx.py`, `verify_setup.py` and
`verify_yt_smokes.py`. `build_flashx.py` refuses existing isolated build paths.
`launch_windows.ps1` preserves Windows interoperability for disk checks.
After the full worker ends, `analyze_flashx.py` requires all four L3/L4 cases
and independently checks every mass sum with yt before writing plots/reports.
Dependencies include the parent study `build.py` and audited
`/home/kaan/verified_20260907` helpers. No other code's native result is reused.

Native raw directory: `/home/kaan/sensitivity_20260907/flashx/runs`.
Windows source: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907/flashx`.
Published setup/analysis packages are separate from production viewer entries.
Scripts and proofs are published, not raw datasets. Nothing has been emailed.
Publication verifies remote main, Pages status and live URLs; a publication
correction does not modify raw simulation data.
