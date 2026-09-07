# RAMSES velocity sensitivity continuation

## Completed results

All four L3/L4 controls completed with 101 distinct native snapshots each.
Every saved field and time passes the native checks. Initial density, tracer,
coordinates and volumes match exactly within each pair; pressure differs by
at most 1.3e-15. The second mass aggregation agrees within 8.9e-15 scaled error
across all 404 outputs. Eight launcher tests and two analysis tests pass.
See [the report](report.json) and [mass/retention plot](mass_and_retention.png).

| Level | Sharp / historical solver wall time | Peak sampled solver-child RSS | Peak mass-curve separation / initial dense mass |
| --- | --- | ---: | ---: |
| 3 | 11.6s / 11.7s | 0.99 GiB | 7.47% |
| 4 | 168.1s / 169.9s | 1.00 GiB | 4.18% |

Eight MPI workers were observed at 99.7-99.8% CPU usage each during L4.
Validation adds time beyond the solver timings above. All native outputs,
about 14 GiB, remain on disk. The worker ended normally with L5 storage-held:
172.49 GiB plus 10 GiB reserve was required, versus 34.77 GiB then available.

Both variants have zero mass above the density threshold at the last output,
but their earlier curves differ. Final tracer fractions are 0.84085/0.84325
at L3 and 0.92250/0.92096 at L4 (sharp/historical). Final actual times span
5.00031-5.00422 t_cc; these native overshoots are recorded, not relabeled.
This is not an all-material-retained comparison or proof of convergence.

Prepared and launched 8 September 2026 at 01:44 local time. Inspect native
`/home/kaan/sensitivity_20260907/ramses/batch.json`, `current.json`, Windows
`worker_windows.json/log/err.log` and actual processes for current status.
Those worker records now describe completed work. This is a within-code
experiment, not a blanket rerun or a production
viewer entry. Nothing has been emailed.

## Native source and controlled difference

The actual pre-audit 3D-capable RAMSES problem source contains the historical
tanh velocity law at 1.3 R. The paired native executable selects that law with
`velocity_ic=1`, or sharp velocity with `velocity_ic=0`. Density remains tanh
with width 0.1 R in both cases. Consistent kinetic energy follows velocity.
All other pair inputs, precision, solver, density, tracer and boundaries match.

The native MUSCL/HLLC executable is SHA256
`52b822af90d1aa32899c7f860cf60e9826281d182f7ee91e8d83d41ad98922d7`.
It was built with the existing native flags, NDIM=3, NPRE=8, NPSCAL=1, MPI=1,
in a separate build directory. The rectangular read_params patch is unchanged.
Canonical sources, build objects and binaries were hash-checked unchanged.
Historical-source and build hashes are in `build.json`.

The domain is [0,20] x [0,10] x [0,10], with the cloud at (3,5,5), equivalent
to the study's cloud-centered coordinates. Fixed chi=100, Mach=2, gamma=5/3,
R=1, ambient density=pressure=1, CFL=0.4. L3 means 64x32x32 and internal
RAMSES levelmin=levelmax=5; L4 means 128x64x64 and internal level 6. The mesh
is uniform, not an adaptive-resolution comparison. Existing six-face inflow/
outflow conditions and conserved tracer rho*f remain unchanged within pairs.

## Validation before launch

Eight launcher/IC/coverage tests pass. Both native eight-rank smoke runs save t=0 and an
evolved snapshot. Initial density, tracer, coordinates and volumes match
exactly within the pair, with pressure difference <=8.9e-16. Velocity differs
by up to 1.289 in native units. An actual invalid-mode test exits with code 2
before any native hydro output. Its input/log are retained as evidence.

The corrected smoke was also compared with the earlier audited native build.
Coordinates/velocity match exactly; density relative difference is <=5.6e-15,
tracer difference <=2.3e-16 and pressure difference <=1.3e-15. This extra
cross-build check permits 1e-13 roundoff. The new within-binary pair still
requires exact initial density/tracer/grid equality. See `setup_validation.json`.

The special native reader is necessary: stock yt drops part of this rectangular
coarse mesh. It checks all eight rank files, six float64 primitive fields, full
grid coverage without overlaps, coordinates, cell widths, finite fields and
positive density/pressure. The analysis performs an additional unsorted-record
mass aggregation, but this shares the native decoder and is not an independent
parser validation. Two synthetic analysis tests check volumes and thresholds.

## Queue, times and retention

`launch_windows.ps1` holds a Windows-owned WSL worker alive. It runs L3/L4
pairs, then checks whether the entire L5 pair fits. Both shared production/
benchmark locks and RAM/guest/Windows storage guards apply. No competing builds,
unvalidated checkpoint resumes, cooling, tracking or destructive sweepers run.

Target output cadence is 0.05 t_cc through 5 t_cc. RAMSES saves when a timestep
crosses an output time, so the native time may be slightly later. Every actual
time is retained, checked and plotted; none is reassigned to nominal t. The
normal evolution and timestep policy were not changed to force exact timestamps.
All native mesh, hydro and restart data remain saved. MP4s/meshes are not raw
backups. No raw file has been deleted or thinned.

The measured eight-rank L3 smoke output is about 10.28 MiB per snapshot. The
conservative whole-pair budgets include 103 outputs, 30% headroom and metadata:
L3 3.19 GiB, L4 22.00 GiB, L5 172.49 GiB, each plus a 10 GiB free-space reserve.
L5 cannot fit the currently available backing-drive space. Smoke solver times
were below half a second, shorter than the original RSS sampler interval;
their recorded zero sample is unavailable memory measurement, not zero RAM use.

## Reproduction and interpretation

These scripts target this machine's WSL paths. Run them with
`/home/kaan/venv/bin/python`. Shared helpers are in
`/home/kaan/verified_20260907`; build hashing uses the parent study `build.py`.
`build_ramses.py` refuses to overwrite its isolated build. Do not relaunch an
existing worker or silently restart partial run folders.

Native outputs: `/home/kaan/sensitivity_20260907/ramses/runs`.
Source and scripts: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907/ramses`.
Use `test_ramses.py`, `test_analysis_ramses.py` and, after the worker finishes,
`analyze_ramses.py`. The latter reads run metadata, not a manually supplied level.
Dense mass is rho>rho_cloud_initial/3 with a fixed native initial denominator.
Only scalar curve-separation metrics interpolate to 0:0.05:5 t_cc. Tracer mass
is measured separately; do not assume all material remains at the final time.
Coarse L3/L4 results do not establish convergence or a universal reuse decision.

## Test and publication checklist

Native tests and invalid-input rejection precede full runs. Every completed
snapshot and paired initial field must pass before interpreting results.
Publish scripts, hashes and checked analyses separately from production viewer
entries. Verify the remote commit, Pages deployment and actual report URLs.
If published diagnostics fail verification, correct the analysis package without
touching native datasets; retain the prior commit as the publication rollback.
