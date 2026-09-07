# Velocity-prescription sensitivity study

Ryan requested a few resolutions per code at fixed chi and Mach before deciding
whether affected historical runs need replacing. This study preserves all old
and new raw data. It does not authorize a blanket replacement campaign.

## Fixed pilot design

Chi = 100, Mach = 2, gamma = 5/3, cloud radius = 1, ambient density = pressure = 1,
the existing tanh density edge of width 0.1 R, the existing 20 x 10 x 10 R wind
tunnel, no cooling, magnetic field or frame shifting. Wind-axis orientation is
code-native and reordered only for visualization. No tracer or boundary changes
are mixed into the within-code velocity experiment.

Run both historical and corrected prescriptions at L3 (64 x 32 x 32), L4
(128 x 64 x 64), then L5 (256 x 128 x 128) when raw-retention storage permits.
L3/L4 are a pilot, not well-resolved edge/convergence certification.

Athena++ historical law is reconstructed from `cloud_wind.cpp.tanh_backup`:
`vx = vwind * (1 - 0.5*(1 - tanh((r - 1.3*R)/(0.1*R))))`.
AthenaPK's actual pre-audit law was different: zero momentum through 1.3 R,
constant wind momentum outside, so velocity in the density tail was
`rho_wind*vwind/rho`, not constant velocity and not a tanh velocity law.
The corrected case in each code is zero velocity through 1.3 R and constant
wind velocity outside. The energy follows the chosen velocity at fixed pressure.

Every pair uses the same isolated executable, source/build evidence, rank count,
grid/block layout, reconstruction, Riemann solver, CFL, boundaries and outputs.
Only `velocity_ic` changes in the input. Initial density/tracer/grid fields must
match exactly; pressure may differ only by floating-point recovery roundoff.

## Preservation and scope

Eight small native runs form the first pilot: two codes x two levels x two laws.
Fresh controls are intentional, to test both laws in the identical executable
instead of introducing uncertain historical binaries/settings as confounders.
These are not full replacements of the old campaign. Each targets 101 full-field
native outputs through 5 t_cc plus unchanged restart settings. No raw file is
deleted or thinned, and the live viewer is not relabeled with these experiments.

The remaining code families/variants need historical-source and native-IC checks
before their paired launchers are enabled: FLASH 4.8, Flash-X,
Arepo, GIZMO MFM, GIZMO MFV, Gadget-4, Gasoline. Particle sampling
and random seeds must be identical within a pair. This is pending work, not an
already runnable all-code queue.

As of 8 September, Athena 4.2 has completed and validated its L3/L4/L5 pairs.
Enzo's isolated native build and paired initial-condition tests pass, and its
v2 launcher advances L3/L4 then checks whether the entire L5 pair fits storage.
Enzo's first attempt stopped on a mistakenly set wall-clock restart trigger;
that attempt is retained separately and is not counted as a full control.

Enzo L3/L4 is now complete with all 102 actual native times per case, and all
408 outputs were independently cross-checked with direct HDF5 sums. L5 is held
by the whole-pair raw-retention budget. Enzo-E's paired 3D IC checks now pass;
its historical radial law is sourced from the existing 2D input and extended
spherically in the audited 3D setup. Density, method, grid layout and boundaries
remain identical within this pair. The existing Enzo-E recipe has no tracer:
report that limitation instead of claiming that material retention was measured.

Enzo-E L3/L4 is now complete as well: 404 native snapshots, per-block versus
assembled-grid mass checks, unchanged paired initial fields, no tracer diagnostic.
Its L5 pair is also storage-held. RAMSES now has four completed L3/L4 controls
with 101 actual times each, exact paired initial density/tracer/grid and
pressure agreement to roundoff. All 404 outputs pass checks; its extra
unsorted-record aggregation agrees within 8.9e-15 but shares the native decoder.
Native timestep-crossing times are preserved. L5 is held by the 172.49 GiB
whole-pair retention budget plus reserve. There are now 26 analyzed controls.
Next safe code families remain FLASH 4.8,
Flash-X, Arepo, GIZMO MFM/MFV, Gadget-4 and Gasoline; no runnable queue
for those is claimed before native historical-law and initial-field checks.

## Validation and analysis

Unit tests reject wrong velocity modes, extra parameter differences and incorrect
native ICs. Each real run is checked for positive finite fields and all native
timestamps. Saved t=0 fields must reproduce the selected analytic velocity law.

Measure density-selected mass (`rho > rho_cloud_initial/3`) with the same measured
initial dense-mass denominator within each pair, plus tracer mass in the box,
dense centroid and density-field differences. Show resolution overlays. Native
times are preserved; any scalar-curve interpolation onto common times is stated.
3D density is also rendered as matching-time 2D central-slab images with common
coordinates, normalization and color scale. These are not independent 2D runs.

Independent yt checks verify direct HDF5 mass sums at initial/final L3 snapshots.
Assess time/resolution dependence; do not choose a universal significance cutoff
after seeing the results. Finer tests and each code's uncertainty/convergence are
needed before a reuse decision. T=5 is a common terminal time, not proof that all
cloud material remained in the box. Cooling and tracking validation remain separate.

## Commands and artifacts

Source/scripts: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907`.
Native working area: `/home/kaan/sensitivity_20260907`.
Use `/home/kaan/venv/bin/python` under WSL for `build.py`, `test_pairs.py`,
`run_pairs.py --run` and `analyze.py`. Builds/outputs fail closed on unexpected
state and preserve failed attempts. Runs take the existing benchmark/production
locks and check both Windows backing-volume and WSL space.
