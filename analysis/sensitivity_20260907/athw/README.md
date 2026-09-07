# Athena 4.2 continuation

The sensitivity study now includes a six-run native Athena 4.2 queue: L3, L4
and L5 at chi=100 and Mach=2, each with corrected sharp velocity and historical
tanh velocity. The density profile, pressure, tracer prescription, wind tunnel,
solver settings and resolution remain unchanged within each pair. The isolated
binary hash is `f50538d95d644f80d3dc4bbf12b737aa69a84e6afb27f6f2cf420d3a6120caef`.
No production source or executable was overwritten.

Both two-step native IC checks passed. Three launcher tests passed. The first
four full runs (both L3/L4 pairs) completed with 101 distinct native times each.
Solver-only wall times were approximately 8.9, 8.8, 105.9 and 105.6 seconds;
validation adds time. L5 is 256 x 128 x 128 and uses eight CPU MPI ranks. Its
sharp and historical runs have now both completed: 1443.7 and 1454.1 seconds
(24m04s and 24m14s). Each used eight fully busy MPI workers and peaked at about
2.68 GiB solver-child RSS; this is not total Windows memory use. All six cases
have 101 distinct native snapshots. No Athena 4.2 worker remains active.

## Validated findings

The additional analyzer checked all 606 native tracer snapshots against the
previous native density-mass sums. Initial density, tracer, coordinates and
volumes match exactly within each pair, as does stored pressure. The tracer
matches the code's conserved scalar chi*f, so concentration is chi*f/rho.
Three additional analysis tests passed. Plot and machine-readable results:
[mass and retention](mass_and_retention.png), [report](report.json).

| Level | Peak curve difference / initial dense mass | Sharp / historical final tracer retention |
| --- | ---: | ---: |
| 3 | 13.09% | 90.93% / 90.83% |
| 4 | 7.59% | 95.70% / 95.69% |
| 5 | 8.70% | 97.39% / 97.50% |

These are within-code sensitivity differences, not accuracy errors. Separation
uses linear interpolation of scalar diagnostics to 0:0.05:5 t_cc; plotted curves
retain actual native times. L5 does not make the effect disappear. Finite-box
tracer loss and resolution dependence remain caveats; no universal historical
reuse or blanket rerun decision follows. Native VTK fields remain float32,
with unchanged solver/restart precision. Full raw outputs remain on disk.

## Worker and recovery

The first Linux-detached launch failed during the Windows backing-disk check,
before starting a run: its parent WSL interoperability endpoint had exited.
That failure and its log were retained. Use the Windows-owned launcher instead:
`launch_windows.ps1`. It holds the WSL process for the lifetime of the queue.
The old `launch.py`, `/home/kaan/sensitivity_20260907/athw/worker.json` and
`worker.log` are evidence of that failed launch, not the active worker.

Completed launch record and logs are in this Windows directory:
`worker_windows.json`, `worker_windows.log`, `worker_windows.err.log`.
Native current status: `/home/kaan/sensitivity_20260907/athw/current.json`.
Native aggregate status: `/home/kaan/sensitivity_20260907/athw/batch.json`.
Native outputs: `/home/kaan/sensitivity_20260907/athw/runs`.
Inspect actual process command lines and logs before any relaunch. Existing
complete cases are skipped; partial cases require review and are never silently
restarted at t=0. Restart files are retained but checkpoint resume has not been
validated for this pgen, so do not resume them blindly.

The worker holds the shared production/benchmark locks, checks host and guest
disk capacity before each case and does not run heavy builds concurrently. It
advances after native-output validation, without waiting for a new user message.
The separate task heartbeat checks every 15 minutes and can prepare the next
safe code's tests after this worker finishes. It must not duplicate this worker.

## Output and storage

Native VTK output is float32 for the complete primitive fields; native compute
and restart precision remain unchanged. This was the existing Athena 4.2 output
format, not reduced to make the study fit. Its smaller native files allow an L5
budget of approximately 18.45 GiB plus a 10 GiB free-space reserve; the larger
Athena++/AthenaPK L5 reservations must not be weakened to match that budget.
All 101 native VTK times and all restart outputs are retained. Actual native
times are recorded; they are not relabeled as exact nominal cadence. VTK header
time precision is accounted for explicitly by the time validation tolerance.

Further analysis must compare initial tracers/fields between paired runs and
inspect retention and resolution dependence. Completed output counts alone do
not certify cross-code equality or paper-ready results.

## Cleanup performed alongside the queue

The published-artifact cleanup replaced 45 exact duplicate files with NTFS
hardlinks, freeing 245.52 MiB of duplicate storage. Both file paths and every
byte remain. The retained contents match blobs on remote main with a successful
GitHub Pages deployment. No unique raw dataset was deleted. The public repo
remained clean. The audit is `../public_artifact_dedup.json`.

Hardlinked paths share file contents. Future artifact writers should write a
new temporary file then atomically replace it, not edit a hardlinked file in
place. Removing one path does not remove the data while another link remains.

`../storage_inventory.json` records that Windows-side CloudCrushing artifacts
are about 1.6 GiB, whereas most raw simulation data lives inside WSL. Deleting
raw files in WSL increases Linux free space but does not automatically reclaim
space from the Windows VHDX file. No compaction, WSL shutdown or RAM/BIOS change
was attempted while the simulations run.
