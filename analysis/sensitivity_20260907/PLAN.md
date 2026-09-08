# Velocity-prescription sensitivity study

Ryan requested a few resolutions per code at fixed chi and Mach before deciding
whether affected historical runs need replacing. This study preserves all old
and new raw data. It does not authorize a blanket replacement campaign.

## Active: repaired MFV L4 full pair

8 September15:50UTC: six new L4 diagnostics passed with16 native states,
48 retained terminal restart files, independent readers, exact paired
initial fields,60-bit timing and conserved mass checks. See
[preparation results](gizmo/MFV_L4_PREPARATION_RESULTS.md).
The separately frozen full pair now runs sharp then historical on eight
bound CPU workers. All original per-level numerics remain unchanged;
tiny timing caps apply only to the completed diagnostics.

Runner: `/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_full_runner_v1/mfv_l4_full.py`.
Plan SHA256: `2b77bb64257e2826dfe241ca6fb31eedcd5b868d73eeb4761cf96ac079430d7c`.
Raw/ledger: `C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_velocity_pair_v1`.
The Windows-owned hidden launcher keeps the sequential pair independent of
chat turns. Do not relaunch preparation, full workers, frozen tests or
completed diagnostics. Check actual processes and ledger before next work.

Full-pair retention budget12.92883GiB passed after staging, with separate
host/guest10GiB reserves and1GiB ancillary allowance. No raw data was moved
or deleted. Keep the accepted count48 until both full runs and new analysis
pass. After completion, reuse accepted repaired L3 scalar curves for a
new immutable L3/L4 analysis; do not rerun its raw analysis. The four
Gasoline controls remain scientifically held; higher levels are separate.

## Completed: Gadget-4 L4 pair and L3/L4 comparison

8 September: both missing L4 sharp/historical controls completed with
the unchanged validated native binary and eight CPU workers. The new
[storage/launch plan](gadget4/L4_DIRECT_STORAGE_PLAN.md) saves new raw data
directly on C:, with a separately tested mount/capacity mapping; it does not
move or delete completed WSL data. All 15 new wrapper tests and independent
Windows readback of both ICs, parameters and the small storage probe passed.
The full pair budget and host/guest reserves were guarded. Both controls
have 101 independently checked native states through 5 t_cc. The new
[L3/L4 analysis](gadget4/analysis_levels_v1/README.md) reuses the accepted
L3 scalar report and measures peak separation 6.954% / 4.232%. It adds
12 scalar tests, an independent interpolation check and new raw hash verification.

Runner: `/home/kaan/sensitivity_20260907/gadget4/runner_full_l4_ntfs_v1`.
Raw and live ledger: `C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1`.
Plan SHA256: `a66c291cdaf6858a0c69560a47ed137f5d026e85851af205134b5cb0d67bdba4`.
Do not relaunch preparation, tests, either case, or the frozen runner.
Accepted controls are now 48, containing 4,852 native analysis states. Six
L3/L4 controls remain: two repaired MFV L4 and four Gasoline. No Gadget-4
solver remains active after this pair. Before new native work, check live
processes and both shared locks; saved PIDs are not activity evidence.

The next-scope note below preceded the now-completed MFV preparation above:
assess repaired MFV L4 with its own IC, timing, repair and
conservation validation before a full pair. Direct C: storage requires a
separately reviewed mapping/budget for MFV; do not blindly reuse Gadget's
runner or charge its payload only to guest space. Refresh host and guest
space and retain full new raw plus reserves. Gasoline still requires its
scientific validation decision. No blanket queue is enabled, no old raw
relocation approved, and no native data deletion is needed for this result.

## Earlier immutable consolidation: resolution summary

The [resolution summary](resolution_summary_v1/README.md) collates the 23
accepted pairs from existing reports, with exact source hashes and 12 unit
tests plus scalar cross-checks for all pairs. No native reruns, raw relocation
or acceptance changes were made. At that snapshot the accepted total was 46; eight L3/L4
controls remain held, plus higher levels. The storage-relocation approval
and Gasoline scientific-repeatability decision were pending. Do not repeat
this consolidation or the completed native diagnostics on unchanged follow-ups.

## Latest completed gate: repaired MFV L3 pair

8 September: sharp preparation and the missing full control now pass on the
same isolated repaired executable as the completed historical diagnostic.
The historical case was verified and reused, not rerun. Each has101 native
frames through5 t_cc. All paired initial nonvelocity, independent mass,
60-bit cadence and terminal conservation checks pass. Peak dense-mass
separation is6.438% at this one coarse level; accepted total is46. The old
failed MFV attempts remain excluded. See [the paired evidence](gizmo/MFV_REPAIRED_PAIR_VALIDATION.md).
The dated preparation steps below remain as history. No higher MFV runner
is enabled by this result; eight L3/L4 controls remain unlaunched and larger
levels remain additional guarded work.

The [Gasoline read-only divergence review](gasoline/DIVERGENCE_REVIEW.md) now
locates the first saved differences and verifies all eight selected checkpoint
prefixes against their same-step TIPSY exports. Differences already exist in
native doubles, including original-binary repeats. The actual density callback
is gather-only; symmetric force/energy cache accumulation is a candidate for
further tracing, not a proven cause. No new solver was run or tolerance changed.
Gasoline remains scientifically held and the accepted total stays46.
The later [serial-output buffer test](gasoline/SERIAL_OBSERVER_VALIDATION.md)
passed three exact byte/count checks in a new six-step, two-worker diagnostic.
Both real states and the finalized checkpoint are retained. Its initial failed
preparation is preserved separately. This tests direct buffer mutation only,
not calculation-order or trajectory equivalence; no full control is enabled.
The subsequent [native force-order study](gasoline/FORCE_ORDER_RESULTS.md)
now reproduces27 selected paired force-sum differences from identical inputs
in different recorded orders. All three planned six-step traces completed;
four actual states and three checkpoints remain saved. The read-only comparison
and independent rational replay pass. Changed-input cases remain distinct and
the previous density gate remains failed. No further traces or full Gasoline
controls are enabled without a scientific acceptance decision and the remaining
same-executable sharp-IC validation.

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

Gasoline's historical-source and native-IC checks are measured. Its longer
output-observation test failed the predeclared field criterion, including
original-binary repeats, despite identical dense masses through1 t_cc.
Complete checkpoint retention and full L3 storage budgeting are now measured;
the output-observation review remains before a full paired launcher. Gadget-4 L3 is now
complete and independently checked; L4's own native checks now pass, but its
full pair is storage-held. GIZMO's L3
setup and separate MFM L4 checks are validated; MFV's later L3 energy failure
remains a separate blocker. Particle sampling
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
whole-pair retention budget plus reserve. There are now 44 analyzed controls.
FLASH 4.8's four L3/L4 controls are complete with 101 full-state times each;
all 404 checkpoint mass sums pass independent yt checks. Its native setup
has no tracer, so retention is unavailable. The unchanged native plotfiles are
supplemented with full-state double-precision checkpoints at every plot time;
the old rolling-two-checkpoint policy is replaced with a 10000-file span.
This explicit retention-policy change applies to both controls, preserves all
native fields and avoids overwriting states. Other within-pair settings stay
identical except velocity and its consistent energy. L5 needs 153.31 GiB per
full retained pair plus reserve and is guarded, not promised runnable.
Flash-X now has a separate native build and passed paired initial-condition,
invalid-mode and independent yt smoke checks. Its L3/L4 queue started at
02:47 local time on 8 September with eight MPI ranks. Native eleven-field
float64 checkpoints are retained at every comparison time, alongside all
original five-field float32 plotfiles. No tracer is available. Its L5 pair
needs 129.79 GiB plus reserve and is guarded. All four Flash-X L3/L4 controls
and their 404 actual times now pass independent yt mass checks. Full analysis
is complete and L5 storage-held.
Arepo's native L3/L4 paired queue started at 03:30 local on 8 September after
native and independent initial/evolved checks. Nonvelocity IC fields and native
initial density/geometry are exact within pairs, but original Voronoi pressure
perturbations (up to 14.45% at L3) and periodic x boundaries remain. This is
within-Arepo sensitivity, not certification of a matched grid-code baseline.
All four Arepo L3/L4 controls and their 404 native times are now complete and
analyzed, with independent yt mass-sum agreement within 6.2e-16. Peak curve
separation is 2.81% at L3 and 2.70% at L4. The full native files remain saved.
The L5 pair needs 124.02 GiB plus reserve and remains separately guarded.
GIZMO MFM L4 is complete and analyzed. Gadget-4's native L3 preparation and
independent checks now pass, and its full L3 pair is complete and analyzed,
with 101 native times per case and 6.95% peak curve separation. Its SPH
initial pressure peaks at 3.9003 times nominal, identically
within the pair: this is not a uniform-pressure grid-code baseline. The existing
native smoothing-length patch is retained, not introduced as another change.
See [Gadget-4 scope and validation](gadget4/README.md). Gasoline's diagnostic
preparation now includes95 independent output checks, exact paired initial
nonvelocity fields and native pressure-stage diagnosis. Both the original
bitwise and separate prospective field-equivalence tests failed; all failed
checks and original-binary repeats remain retained. The new81-state test
keeps exact dense membership at every compared time through1 t_cc. All eight
checkpoints are valid and retained; the full pair's3.15 GiB storage budget
plus reserves fits, but full controls remain scientifically held.
See [Gasoline's longer validation audit](gasoline/LONGER_VALIDATION.md).
Gadget-4 L4 now passes per-level IC, initial/evolved native-field, scheduler
and independent-reader checks on four short-test outputs. Its full-pair
budget is 7.30 GiB plus a 10 GiB reserve on both filesystems; WSL had only
16.66 GiB free. No full L4 worker has been launched and the accepted total
remains 44. See [the L4 storage hold](gadget4/L4_VALIDATION.md).
No higher-level queue is claimed before per-level initial-field,
timing and identical within-pair particle sampling checks are verified.
Four GIZMO L3 smokes now pass independent mass checks. Eight small native tests
confirmed that their t=0 velocities are staggered after the first half-step
kick: halving the timestep halves the offset, and zero-step extrapolation
recovers the IC to float32 precision. No native field is rewritten. The mass
study must document this native output convention; velocity-at-header-time
analysis remains unvalidated. A frozen L3-only full runner subsequently passed
15 tests, checked whole-pair storage (1.80 GiB MFM / 2.01 GiB MFV plus the
separate 10 GiB reserve), and launched native controls sequentially on eight
MPI ranks. Native numerical settings and restart interval remain unchanged;
an external 6000-second cap bounds retained restart generations. No restart
is automatically resumed. All raw data and native actual times are preserved.
Both MFM L3 controls completed with 101 states and independent yt mass checks;
peak curve separation is 3.98% of initial dense mass. They add two accepted
controls. Both MFV L3 controls reached 101 states but fail positive stored
energy checks, first at t=3.95 t_cc. These two are NOT counted as validated
controls. The original stopped ledger and separate historical diagnostic
control remain intact; neither is a runnable continuation queue. Do not
change floors or filter invalid states to turn a failure into a completion.

Read-only MFV restart diagnosis now explains the terminal export zeros: all
internal conserved/predicted energies remain positive; three final particle
values underflow float32 and one is flushed from a subnormal to zero by native
FTZ. Exact executable DWARF and independent decoders verify the terminal state.
This does not validate the extreme thermal-energy decline or diagnose every
earlier zero from a contemporaneous restart. Further native energy/limiter
review is required before an isolated instrumentation test or larger MFV pair.
No floor, native field, build, acceptance gate or raw file changed. See
[the evidence and limitations](gizmo/MFV_RESTART_DIAGNOSIS.md).

Further source tracing found an uninitialized local timestep used to integrate
MFV mass flux, confirmed by a warning-only compiler check. All terminal
conserved masses equal their IC values despite nonzero flux derivatives.
Read [the repair-validation plan](gizmo/MFV_TIMESTEP_REPAIR_PLAN.md) before
any isolated source change or test. The exact causal effect on thermal decline
is not yet established; existing native data/binaries and44accepted controls remain.
The isolated reference/repaired builds now compile, nine synthetic exchange
tests pass, and selected native ABI/toolchain checks pass. A new guarded short
native runner and prospective conservation/output-stage checks were then
completed. The two short native cases now pass on four actual outputs, with
reference arrays exactly reproducing the retained original and repaired mass
accounting preserved. A later-onset extension remains separately planned, not
launched. See [short validation](gizmo/MFV_SHORT_VALIDATION.md).

The separately frozen later-onset historical diagnostic has now completed
through5 t_cc. All101 native states and terminal conserved-plus-pending mass
checks pass. The first checker used the wrong clock width; a source-derived
60-bit audit corrected it without a native rerun. A subsequent report-scalar
serialization error was corrected separately with a regression test. All
failed checks remain saved. Next: sharp-IC and within-pair initial validation
on the same repaired binary, then a guarded paired continuation that can
reuse the completed historical case if its recipe is identical. No new full
pair is accepted yet. See [the longer evidence](gizmo/MFV_ONSET_VALIDATION.md).

MFM L4 subsequently passed its own two short evolved controls and four tiny
velocity-timing diagnostics: all16 native outputs independently checked, with
unchanged nonvelocity initial fields. Nine L4 unit tests pass. Its measured
full-pair retention budget is10.25GiB plus10GiB reserve; this fits current
guest and Windows capacity. A separate immutable L4 runner launched the full
sharp/historical pair at07:50 local on8 September using eight ranks. Native
per-level settings remain unchanged, including MaxMemSize1500MiB/rank,
MaxSizeTimestep0.05 and restart interval3600seconds. Tiny diagnostic timestep
caps do not enter production. Both full controls are now complete: 101 native
times each, all 202 states independently checked. The new L3/L4 analysis
rechecked all 404 native mass sums and hashes, retains fixed per-level initial
denominators, and overlays actual native times. Peak separation is 3.979% at
L3 and 0.955% at L4. Six analysis tests pass. These two controls are included
in the 44 accepted total; MFV failures remain excluded. No native outputs
were deleted, retimed, substituted or changed.

## Validation and analysis

Unit tests reject wrong velocity modes, extra parameter differences and incorrect
native ICs. Each real run is checked for positive finite fields and all native
timestamps. Saved t=0 fields must reproduce the selected analytic velocity law
where native output is synchronized; GIZMO's explicitly validated half-step
velocity output is a documented exception, not a relaxed IC tolerance.

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
