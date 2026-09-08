# Next native stage: repaired MFV L4 preparation

Prospective plan, 8 September 2026. No L4 MFV native case has been admitted
by this document. Gadget-4 L4 is complete and must not be relaunched.
The accepted total is 48 controls; six L3/L4 controls remain, plus higher
levels. The blanket replacement campaign stays inactive.

## Fixed scope

Use only the existing isolated repaired GIZMO MFV executable:
`/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/repaired/GIZMO_repaired`.
SHA256: `4784336422c25db4714c6f56ef95337347f4be18dfd622e2b7e9acf7e1fe3d3c`.
No new rebuild or change to the repair, original failed executable or
completed L3 experiments. Read MFV_REPAIRED_PAIR_VALIDATION.md first.

L4 means 128 x 64 x 64 = 524288 initial equal-volume elements, 6.4 per
cloud radius. Fix chi100, Mach2, gamma5/3, nominal rho/P1, R1, density
tanh width0.1R, velocity radius1.3R and the original fully periodic
20 x 10 x 10 box. Preserve original per-level numerical parameters,
including MaxMemSize1500, PartAllocFactor2.5, MaxSizeTimestep0.05,
MinSizeTimestep1e-12, MinGasTemp0, DesNumNgb32 and restart interval3600s.
Derive t_cc and output times from the pinned native IC/parameter metadata,
not a label or manually supplied level. Changing output paths/times for
isolated diagnostics must not alter the full-run numerical prescription.

## New code must be level-aware

The completed L3 modules hardcode65536 IDs in their readers and terminal
checks. Do not monkeypatch their globals, suppress their failed checks or
reuse their L3 verdict as L4 evidence. Create separately named versioned
L4 readers/runners and tests, reusing only appropriate pure functions.
The older mfv_onset.py scheduler assumes29bits and must not be used;
the actual executable uses a60-bit integer clock, verified in its ABI.

Before native execution, tests must reject changed counts/IDs, wrong
field dtypes, wrong law, changed nonvelocity fields, a wrong clock width,
invalid mass accounting, missing host measurements, wrong output mount,
insufficient host/guest budgets, stale ownership and existing destinations.
Freeze new code, tests, plan, native executable, source and IC/input hashes.
Do not repeat completed repair-build tests or L3 native experiments.

## Six short native diagnostics, not full science controls

For each of sharp13 and historical tanh13, use one original-timestep smoke
to code time0.1, then two timing diagnostics to0.00004 with diagnostic-only
MaxSizeTimestep1e-5 and5e-6. Retain every actual native output and terminal
restart; do not discard nearly duplicate terminal times. Both ICs must be
checked against the L4 lattice and density/thermal construction. The
historical law must reproduce the actual archived L4 IC arrays. Nonvelocity
IC fields and corresponding native initial fields must match between laws.

Read all native states with direct HDF5 and independent yt GizmoDataset.
Check all524288 unique IDs, schema/precision, finite positive density,
mass, energy and smoothing length, periodic bounds and actual header times.
Report initial kernel-density/pressure deviations instead of correcting
them silently. Native velocities remain half-kick staggered: for EACH law,
test the existing half-step ratio gate (within0.002 of0.5), a discriminating
nonzero offset and zero-step recovery within the existing four-float32-eps
scale bound. No extrapolated quantity may replace a saved field or time.

Read all eight terminal restart prefixes using the exact executable ABI.
Check IDs, native60-bit endpoint/clock, recipe and finite positive fields.
Use conserved MassTrue plus pending dMass, not predicted snapshot mass, for
the global mass ledger. Independently cross-check the struct mass sum.
Retain the existing short engineering gate: n=32*N*(K+1), binary64 unit
roundoff u=2^-53, K<=256, n*u<0.01 and allowance n*u/(1-n*u) times the
absolute ledger scale. Require a discriminating mass-flux response where
the original short test requires it. A failed criterion requires review,
not post-hoc tolerance widening. This is not a physical-accuracy theorem.

## Storage and resource admission

Last read-only snapshot after Gadget-4: about14.29GiB guest free and
29.56GiB on C:. These are NOT launch-time admission measurements.
The old repaired MFV L4 full-pair screen of13.177GiB is only an estimate
from L3 and is NOT an actual L4 retention measurement. Include the SIX
short-case outputs/restarts, full-pair reservation if claimed, working
files and logs in any capacity decision. Measure true L4 sizes after
short validation before admitting a full pair.

If new raw is written directly on C:, review a separate MFV-specific
Windows mount/capacity mapping. Gadget's successful mapping is evidence
about the filesystem, not authorization to use its code-specific runner.
Keep source/executable on ext4, write new raw only to a fresh validated
directory under C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907,
and verify independent Windows byte readback. Charge all new payload to
C: plus a guest ancillary allowance charged to both guest and backing host.
Require10GiB reserves on BOTH filesystems. Never count guest capacity as
additional host free space, delete raw or move old data to make a gate pass.

Acquire both benchmark.lock and production.lock and check actual live
solvers/builds before native work. Use eight bound MPI workers with
single-threaded OMP/BLAS. Require at least12GiB available RAM before each
case and2GiB live; measure allocation rather than filling RAM artificially.
Use a180s diagnostic cap and native stop with bounded grace, followed only
by signals to a verified owned process group. No auto-resume or stale-PID
signalling. The CPU-only executable cannot use the GPU without a different
solver. Fan noise and intentional desktop lag are not throughput targets.

## Separate full-pair gate

Only after every L4 preparation check passes, write a new full-pair plan
using actual L4 snapshot/IC/restart sizes. Budget104 snapshots, retained
restart generations plus original margin and logs for EACH law, full raw
retention and both reserves. Keep unchanged full-run timestep/physics,
restore metadata-derived5t_cc and0.05t_cc outputs, and use the existing
full engineering mass step envelope K<=32768. The short diagnostics do
not prove the old late thermal failure is absent at L4; that requires
checking both full native trajectories, including late energy positivity.

Validate and analyze in a new immutable directory. Overlay the accepted
L3 scalar curves without rerunning or reanalyzing L3 raw. Publish reviewed
custom scripts, native provenance and scalar plots only after validation;
require successful Pages and live hash checks. No failed controls enter
the accepted count, no blanket historical reuse/replacement decision,
no cooling/frame-tracking/all-material-retained claim, and no new
production3Dviewer entry implied by an analysis publication.
