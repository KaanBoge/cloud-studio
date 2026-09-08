# Native GIZMO sensitivity: MFM L3 complete, MFV L3 needs review

Updated 8 September 2026. The two full **MFM L3** controls are validated and
analyzed, raising the study total to **40 accepted controls**. Each has 101
distinct native snapshots through 5 t_cc. The two **MFV L3** attempts also
reached 101 snapshots, but both failed positive-energy checks and are excluded
from that total. No simulation is currently running in this L3 batch.

## Full L3 findings

| Native method and velocity law | Snapshots | Solver time | Peak child RSS | Outcome |
| --- | ---: | ---: | ---: | --- |
| MFM sharp | 101 | 82.37 s | 0.489 GiB | Validated for mass diagnostics |
| MFM historical tanh | 101 | 82.13 s | 0.488 GiB | Validated for mass diagnostics |
| MFV sharp | 101 | 128.34 s | 0.544 GiB | Zero stored energy in 15 snapshots |
| MFV historical tanh | 101 | 127.96 s | 0.544 GiB | Zero stored energy in 16 snapshots |

All four cases used eight MPI workers. Median sampled busy CPU cores were
7.996-8.000; these are CPU simulations, not GPU runs. Solver times exclude
the subsequent validation and publication work. RAM figures are solver-child
RSS, not total Windows/WSL memory or an allocation target.

MFM's peak absolute mass-curve separation is **3.979% of the fixed initial
dense mass**. Final dense fractions are 0.97111 (sharp) and 0.97910 (historical).
All 202 native mass sums were independently checked with yt, with zero reported
relative discrepancy. Fresh pre-publication raw hashes and direct sums also
match. Density selection is rho > rho_cloud_initial/3. The plot uses every
actual time; the scalar peak uses explicitly stated interpolation onto
0:0.05:5 t_cc. No 3D frame is interpolated or repeated.

![Native MFM L3 mass evolution](mass_mfm_L3.png)

This is **one coarse resolution**, not a resolution-overlay Figure 2 or a
universal decision to reuse historical runs. See [the full MFM series](mfm_l3_report.json)
and [pre-delivery validation](VALIDATION.md).

## MFV failure evidence: preserved, not certified

In both laws, the first zero `InternalEnergy` occurs at native snapshot079,
t=3.95 t_cc: particle ID109 in sharp and ID99 in historical. There are 15 and
16 affected snapshots respectively. Both native solvers exited normally;
that is not sufficient for valid science output. All other stored fields are
finite, and mass, density and smoothing length remain positive in this audit.

The pinned native `io.c` writes `max(MinEgySpec, InternalEnergyPred)` for this
field. Zero stored energy therefore does not, by itself, prove the conserved
energy is zero or establish the numerical root cause. The failure occurs in
both prescriptions, so it cannot be attributed solely to the sharp boundary.
No floor, timestep, native field, file, or acceptance criterion was changed.

The original runner stopped on the sharp-case validation error. The historical
case was then launched explicitly from its already prepared, never-started
directory as an unchanged failure-comparison control, not a checkpoint restart.
See [all 202 native field audits](mfv_pair_audit.json), the
[original stopped batch](full_l3_batch.json), and the separate
[historical-control record](mfv_failure_control.json). Failed MFV states are
not pooled into the MFM mass result or represented as valid viewer entries.

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
Nine setup/timing tests pass, including rejection of a fixed IC error masquerading as a
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

The frozen `runner_l3_v1` full runner adds six tests (15 total, all passing).
Its launch-time proof is [full_l3_bundle.json](full_l3_bundle.json). That proof
describes readiness at launch, not the subsequent outcome. Current outcomes
are the stopped batch, MFV audit and accepted MFM report linked above.
The runner budgets both complete raw pairs, including ICs, logs and retained
restart generations, plus 10 GiB free space on both guest and Windows drive.
Measured budgets were 1.80 GiB per MFM pair and 2.01 GiB per MFV pair.
The native 3600-second restart interval is unchanged; the external 6000-second
limit bounds the retained current/backup generations. Low memory or storage
requests a native checkpoint/stop, with a bounded grace period. No native
restart is auto-resumed. The guard was not triggered in these four short runs.

Next: validate MFM L4 native initial/evolved fields and level-specific velocity
timing, then measure its whole-pair retained disk budget before enabling a
separate frozen L4 runner. MFV requires further diagnosis before larger runs.
Gadget-4 and Gasoline remain unprepared. Neither L4 nor L5 is launched here. Native
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
