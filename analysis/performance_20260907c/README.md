# Third performance pass: measured improvements, retained raw data

7 September 2026. The queued **AthenaPK L5** inputs now use lossless HDF5
snapshot compression level 1. In three alternating short test pairs it reduced
median wall time from **5.636 s to 5.034 s (10.7%)**, including initialization,
two full native writes and a disk flush. Every numeric dataset in the compared
final snapshots decoded exactly identically. Files were **5.9% larger**, so
this is a speed improvement, not a reduced storage reservation.

Athena++ L5 with 8 MPI ranks was slower than the existing 16-rank configuration:
17.718 s versus 16.841 s median. That candidate was rejected. The 16-rank profile
remains unchanged. The CPU solver processes used roughly 2.1 to 2.5 GiB during
these tests; there was no attempt to exhaust memory.

All tests used Mach 2, chi=100, the unchanged 256 x 128 x 128 grid, corrected
sharp velocity at 1.3 R, the existing density profile and double precision.
The endpoint was **0.6 code-time units**, not 5 t_cc. These are not universal
speedups, full production durations, better-accuracy claims, or replacement
science runs. The existing L6 settings were not changed by this pass.

## Enabled configuration and rollback

The current profiles remain in `../performance_20260907/optimized_profiles.json`.
Three untouched L5 GPU preparations were superseded by new directories:

    /home/kaan/codes/athenapk/runs/OPTIO1_sharp13_20260907_L5_chi{10,100,1000}

Only primitive snapshot compression changes. Native physics, precision, variables,
grid, timestep controls, output schedule and checkpoints remain unchanged.
The queue now points to these new preparations, with binary/input hashes checked.
Old preparations, raw outputs and source binaries were retained. The prior
profile and queue manifest are backed up under `/home/kaan/performance_20260907c`.
Rollback means deliberately restoring those records while no worker is running,
not overwriting an evolved run. The original 13 launcher tests pass.

## Storage is still a constraint

One real Athena++ L4 chi=100 snapshot at 5 t_cc was losslessly repacked using
HDF5 shuffle and gzip level 1: **25,199,200 to 12,740,951 bytes (49.4% smaller)**.
Every dataset's decoded bytes, shape, dtype and all attributes were checked.
The original was retained. This is a storage pilot only; no campaign-wide ratio
is inferred and no raw file was replaced or deleted.

Separately, 413 byte-identical MP4 copies were verified against the exact Git
commit with a successful Pages deployment. Their duplicate Windows storage was
replaced with NTFS hard links, retaining both paths and all data, saving 411.5 MiB.
Hard-linked paths now share the same local file contents; use a fresh output file
and atomic replacement when generating a replacement movie. Removing one link
does not remove the other. No raw snapshots or restart files were deleted.

This is about 0.4 GiB, not hundreds of GiB. Published movies and quantized meshes
are lossy visualizations, not archives of native fluid fields. The conservative
Windows-backed guards remain in force: approximately 48 GiB free for one L5 run
or 246 GiB for L6, including safety space. WSL's internal free space is not
automatically reclaimed on Windows by deleting a Linux file.

## Requested campaign versus verified results

`campaign_inventory.json` reconciles historical notes with current native-run
records. The baseline is 12 code families, 13 solver variants counting GIZMO MFM
and MFV separately, six integer levels, and three density contrasts: **234
requested configurations**. This is not a promise all fit the hardware, and does
not imply every historical run must be repeated.

Currently 12 corrected L3/L4 runs have passed initial-condition, finite/positive
field and 101-distinct-time checks. Twelve L5/L6 jobs are storage-held. The other
210 configurations need native-run/reuse, launcher or physics audits; they are
not silently launched. Boundary/tracer differences and material retention remain
scientific checks even for the 12 completed runs. The new raw runs have not yet
been exported to the public viewer.

The inventory also lists Mach variations, common late-time figures, mass evolution
with resolution overlays, tracking, radiative cooling, MHD and full-frame exports.
Old cooling-labelled runs had cooling disabled; those are not valid cooling
results. The density-selected tracking prototype still fails the retention
requirement at higher contrasts. Neither variant is enabled by this queue.

## Reproducibility

`probe.py` calls the isolated benchmark/comparison helpers in the preceding
performance pass. `report.json` contains all timings, hashes and field comparisons.
`lossless_probe.py` and its JSON record document the separate storage test.
`campaign_inventory.py` reads the saved run manifests, without launching jobs.
`deploy_profile.sh` and `update_queue.py` implement the guarded local profile
update. They require this PC's native checkouts and are not standalone solvers.
