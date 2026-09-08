# Native GIZMO sensitivity: validated L3 setup, full controls pending

Updated 8 September 2026. Four short native smokes (MFM/MFV, sharp/historical
velocity) and eight isolated timestep-scaling diagnostics have passed. They
are **not** full 5 t_cc science controls and do not increase the study's count
of 38 completed, analyzed controls. No full GIZMO queue has been launched.

## Scope and provenance

Chi100, Mach2, gamma5/3, R1, nominal wind density/pressure1, tanh density edge
0.1R and velocity radius1.3R, regular equal-volume lattice, variable masses,
seed42, eight MPI ranks. Both native variants retain their original fully
periodic 20x10x10 domain. This is not the grid codes' inflow/outflow baseline.
L3 is64x32x32 with3.2 initial points per cloud radius, not a convergence test.

The actual current sharp and archived tanh IC writers are pinned separately.
All IC arrays except velocity are exactly equal within each pair. Metadata
not represented by the native parameter file is explicitly hashed in
`experiment.json`; it is not inferred from filenames or positional arguments.
Native per-level parameter templates, config flags and source/binary hashes
are in `build.json`. Historical comments are provenance, not an endorsement
of their scientific claims. The native MFM/MFV executables are byte-identical
copies of GIZMO_MFM_3D_PER/GIZMO_MFV_3D_PER. No solver code was modified or rebuilt.

MFM binary SHA256:
`ad6787e8666f92e1ac5162eec1aa717277920c51c52b7b04277d0b53295c6011`.
MFV binary SHA256:
`b7634f844d98ceef246d66e2243827f0c5774c9997b92bd8ffeedfdf940eed91`.
Native code logs identify GIZMO2022, master:a828c4b, with the expected method,
BOX_PERIODIC, BOX_LONG_X=2, SELFGRAVITY_OFF and EOS_GAMMA=(5.0/3.0).
There is no cooling, magnetic field, tracking or passive material tracer.
Particle-ID mass is not a material-retention diagnostic for MFV, which permits
mass flux between elements. No tracer retention claim is made.

## The t=0 velocity discrepancy: diagnosed, not hidden

The original strict validator rejected the native first snapshot: positions,
mass, internal energy and particle IDs exactly matched the IC, but velocity
did not. The largest native velocity offsets were0.2291/0.09877 (MFM sharp/tanh)
and0.4644/0.2406 (MFV sharp/tanh), despite header Time=0.

The native source explains the ordering. `run.c` calls
`do_first_halfstep_kick()` before `find_next_sync_point_and_drift()`, which
writes the scheduled initial snapshot. `kicks.c` advances conserved velocity
to the half-step. `io.c` deliberately writes P.Vel rather than a velocity
reconstructed to the snapshot's header time. Thus this field is staggered;
it is not a direct copy of the input velocity at t=0.

This was tested, not merely inferred. Eight tiny native diagnostic runs use
identical original ICs/binaries and only diagnostic timestep caps1e-5/5e-6
with a common stop time4e-5. In all four method/law combinations, halving the
timestep halves the velocity offset (norm ratios0.499983 to0.500760).
Extrapolating the diagnostic velocities to zero step recovers the IC within
2.3842e-7, below the float32 rounding bound1.2312e-6. Initial nonvelocity
fields match the original smoke exactly. These extrapolated values are a
validation check only: no native snapshot is rewritten, retimed or replaced.

`snapshot_timing_report.json` records all eight diagnostics and source hashes.
The corrected validator requires and recomputes this evidence for the exact
binary, law and IC. It does not simply relax the velocity tolerance. Native
velocity-at-header-time diagnostics remain unvalidated and require explicit
treatment of the staggering; the present checks support mass diagnostics.

## Native field and independent-reader checks

All four original smokes contain two native outputs at code times0 and0.1,
with65536 elements. Positions, IDs, masses, initial density, internal energy
and smoothing length are identical within pairs. Native initial density and
pressure differ from the nominal lattice/uniform target by at most0.09156%,
identically within pairs. This small measured deviation is retained, not erased.

Coordinates are float64. Density, internal energy, masses, smoothing length
and fluid velocities are float32; particle IDs, child IDs and generation IDs
are uint32. MFV additionally outputs float32 ParticleVelocities. All fields
are retained, finite and checked; density, mass, energy and smoothing length
are positive. `experiment.json`'s abbreviated float32-output wording refers
to the scalar/velocity fields, not the native float64 coordinates.

Explicit yt GizmoDataset reads all eight original smoke outputs with the
rectangular bounds. Its Gadget-HDF5 I/O handler must also be registered because
this installed yt Gizmo API does not import it automatically. This is an I/O
implementation shared by compatible file formats, not a different solver.
Float64 total and density-threshold mass sums match the direct HDF5 checks
with zero reported discrepancy. Native hashes are unchanged by the reads.
See [verification](verification.json) and [smoke ledger](smoke_batch.json).
Nine tests pass, including rejection of a fixed IC error masquerading as a
half-step effect and a missing/incorrect scaling signal.

## Resources, retained attempts and next gate

Original native smokes took0.8-1.2seconds each on eight MPI ranks, with sampled
child RSS below0.52GiB. These are short test costs, not full-case runtime estimates.
Both shared locks and the existing RAM/guest/Windows-backed storage guards
apply. All original and diagnostic outputs, logs, ICs and restart files remain
saved. No app, native dataset or solver binary was deleted or altered.

The first timing audit wrongly required exactly two outputs; the native code
wrote an extra terminal state at3.9999999999999996e-5 then4e-5. Both actual
times are preserved. A subsequent JSON-serialization failure was repaired;
already completed diagnostic cases were rechecked and collected without
rerunning them. The original strict validator is retained as
`verify_gizmo.pre_timing.py`, but is superseded by `verify_gizmo.py`.

Next: build/test the full retained-pair launcher, validate per-level evolved
initial fields (including L4), establish whole-pair disk budgets and native
runtime/restart behavior, then launch safe fresh controls sequentially. Native
MaxSizeTimestep, precision, CFL and other production numerics must stay at their
original settings; the tiny diagnostic timestep caps are never production inputs.
L5 parameter copies are provenance, not evidence of an enabled or validated L5 queue.

Scripts are machine-specific: Windows source is
`C:/Users/kaanb/CloudCrushing/sensitivity_20260907/gizmo`; native root is
`/home/kaan/sensitivity_20260907/gizmo`, using `/home/kaan/venv/bin/python`.
Existing setup/smoke/audit directories must not be overwritten or blindly rerun.
Shared study/storage helpers are required. This publication contains custom
scripts, configs and diagnostic evidence, not native binaries, raw snapshots,
new production viewer entries, or a completed all-code comparison.
