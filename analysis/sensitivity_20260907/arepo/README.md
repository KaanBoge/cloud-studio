# Native Arepo velocity sensitivity controls

## Queue started 8 September 2026

The native L3/L4 queue started at 03:30 local on eight MPI ranks. It is not yet
a completed analysis. Windows-owned launcher PID was 2432: verify actual
processes and `worker_windows.json/log/err.log`, not a stale PID. Native status:
`/home/kaan/sensitivity_20260907/arepo/batch.json` and `current.json`; raw in
`runs/`. Do not duplicate the worker or edit its loaded `run_arepo.py`.

## Scope and important baseline limitations

This follows Ryan's request to measure velocity sensitivity within each code.
Chi=100, Mach=2, gamma=5/3, R=1, nominal ambient density=pressure=1, density
tanh width 0.1 R, velocity radius 1.3 R, seed42 and 5 t_cc. Physics that Arepo's
native parameter file does not encode is explicitly recorded in
`experiment.json`, hashed, printed in case metadata and passed to its IC writers.
Native evolution settings come from the preserved per-level `param_L*.txt`.
Gamma is the compiled default, not a fabricated native runtime parameter.

**This is not an identical-to-grid-code initial state.** Original equal-volume
lattice masses are assigned before a 5% positional jitter is converted to
actual Voronoi volumes. Native density is mass/Voronoi-volume rather than
mass/lattice-volume. The native L3 smoke has local density and pressure
deviations up to **14.4508%** from the nominal profile/uniform pressure. They
are identical within the pair. Initial native volume sums to
2000.0000000000023, consistent with the whole 20x10x10 domain.

The native x boundary remains periodic; REFLECTIVE_Y=REFLECTIVE_Z=2 is retained
on transverse faces. This is not the grid codes' wind inflow/outflow recipe.
Tracer can recirculate through x, so in-box tracer mass is not proof that no
material ever crossed a boundary. No density, pressure, jitter or boundary
change is mixed into the velocity-only pair to hide these limitations.

## Native code and input provenance

Pinned `Arepo_pair` is a byte-identical copy of native `Arepo_3d`, SHA256
`b643af182ec2c84c4f4c18c057df64c9be98b85928246d9296a4908e0aeb5bff`.
No solver was rebuilt or substituted. `build.json` records source/config hashes
and unchanged canonical files. Native HDF5 Config attributes confirm the
expected compiled flags, including double-precision input/output, one passive
scalar, LONG_X=2 and the existing mesh-motion/regularization/timestep settings.

Both real Arepo IC-writer versions are copied and pinned: corrected sharp
velocity and archived historical tanh velocity at 1.3 R. They receive identical
seed, lattice, chi and exact Mach-2 wind speed. All nonvelocity IC arrays are
bitwise identical. Historical comments are archived provenance, not endorsed
claims that tanh velocity is a published standard or a stability guarantee.

L3 means initial lattice64x32x32 (3.2 points/R); L4 means128x64x64 (6.4/R).
Each original lattice cell contains exactly one point with the original jitter
limit. Moving Voronoi resolution is not a fixed grid later in the evolution.
Existing CFL0.3, mesh regularization, precision, softening settings and native
MaxMemSize512/800 MiB per rank are preserved for L3/L4 within pairs.

## Validation before the full queue

Eight launcher/parser/IC-discovery tests and two scalar-analysis tests pass.
Both native v2 smokes contain t=0 and an evolved output. Their native initial
coordinates, centers of mass, masses, density, volumes and IDs match exactly
within pairs; tracer is exact and pressure/internal-energy recovery differs
by less than 2e-15 relatively. Native velocity differs by up to1.29085.
All eight native snapshot fields are retained and checked for finite values,
float64 physical fields, valid IDs/counts and positive density/energy.

Independent yt particle mass, density-threshold mass and tracer sums agree
for all four smoke outputs within1.88e-16 relative discrepancy. The reader
explicitly selects `ArepoHDF5Dataset` with the rectangular bounds. Automatic
yt detection selected Gadget because this public build lacks its old VORONOI
marker; its smoothing-length cache files were then mistaken for snapshots by
an overly broad glob. Native files were not changed. Numeric snapshot-name
validation now excludes only the known cache sidecars, rejects unknown names
and checks native-file hashes before/after independent reads.

The first smoke was rejected before native output because TimeMax=.001 was
shorter than native MaxSizeTimestep=.05. `smokes/`, `smoke_batch.json` and the
original launcher are preserved. V2 extends only the smoke to0.1 and passes;
full native timestep settings are unchanged. `setup_validation.json` rechecks
the same v2 data under the final validator, without rerunning a solver.

## Outputs, resources and safeguards

Target101 actual snapshot times at0.05 t_cc through5 t_cc. Output fields are
CenterOfMass, Coordinates, Density, InternalEnergy, Masses, ParticleIDs,
PassiveScalars and Velocities. Native density is used for the mass threshold,
not lattice density or a rendered mesh. Tracer is a concentration: conserved
tracer mass is Masses*PassiveScalars. Actual native times and any extra
distinct terminal time are retained; no missing frames are synthesized.

All native snapshots, logs, ICs and restart files remain saved. The native
restart interval9000seconds is unchanged. Current full cases have a7200second
external cap; a timeout preserves partial output for review and is not called
complete or silently resumed. L5 needs further runtime/restart-retention
review even if space later becomes available.

Native smoke times3.7/3.5seconds, peak child RSS1.664GiB. Current L3 workers
were observed99.8-99.9% CPU each, around1.67GiB total solver memory. These are
not total Windows usage or measured full-case durations. RAM gating budgets
the native per-rank allocation plus4GiB headroom. Both shared locks and guest
AND Windows backing-drive storage checks apply. Whole-pair retained-output
budgets: L3 3.91GiB, L4 17.25GiB, L5 124.02GiB, each plus10GiB reserve. No
raw deletion, unvalidated restart, cooling, tracking or competing heavy build.

After the worker finishes, `analyze_arepo.py` requires all four controls,
checks every native mass sum with yt and writes resolution-overlaid mass and
in-box tracer curves. It uses fixed measured initial denominators. Only scalar
curve differences interpolate to0:0.05:5 t_cc; plots retain native times.
Coarse controls do not certify convergence or universal historical reuse.

Scripts are machine-specific and use `/home/kaan/venv/bin/python`, parent
study `build.py` and audited storage helpers. Published setup/results are
separate from production viewer entries and are not raw backups. No email
was sent. Publication is verified by remote commit, Pages status and live files;
publication corrections never require modifying native datasets.
