# Gasoline force-order trace: prospective design

8 September 2026. **Design only: no trace build, runner or native cases exist
yet.** This follows the completed serial-output buffer test, not another
repetition of that test. The existing failed field-equivalence gate remains
failed. No full control is enabled by this document.

## Question and fixed selection

Can the order of local symmetric-force updates and returned remote cache
contributions explain differences in selected native force accumulators?
Distinguish changes in the contribution values, contribution population and
addition order. A difference in addition order alone is not a causal result.

Use the existing immutable `divergence_review.json`, SHA256
`96ee1e31635feae95674bd4777a0d9e5badc288a860112cb86dc40e6ef8957b2`.
Take the union of the first listed particle ID and largest-difference ID in
each of its six earliest saved velocity comparisons, plus density-failure
particle 54857. The resulting fixed IDs are:

`13729, 20518, 23013, 36578, 54857, 63924, 64579`.

Derive and test this selection before running; do not replace targets after
seeing traces. They identify existing saved discrepancies, not necessarily
the first causally affected particles in the integrator.

## Source-specific observations

The retained native tree is
`/home/kaan/sensitivity_20260907/gasoline/native_retained/gasoline`.
Its executable is pinned as
`7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3`.

`smooth.c` selects `SphPressureTermsSym`, `initSphPressureTermsParticle`,
`initSphPressureTerms` and `combSphPressureTerms` for
`SMX_SPHPRESSURETERMS`. The original-particle initializer clears energy-rate
terms but does NOT clear acceleration. The cached-copy initializer also
clears acceleration. Therefore a replay must retain the actual owner baseline,
not assume that every accumulation begins at zero.

`SphPressureTerms.h` updates both active endpoints, including a target appearing
as q when the smoothed p is not a target. Trace both roles in all three macro
expansions. `smoothfcn.c` defines `ACCEL(p,j)` as the native `a[j]` field;
`floattype.h` defines FLOAT as double. The remote combine callback adds all
three accelerations and the PdV, artificial-viscosity and diffusion energy
rates. Capture its actual input subtotal, not an inferred per-neighbor value.

`smInitialize` initializes particles before opening `mdlCOcache`.
`smFinish` calls `mdlFinishCache` before its postprocessing and context release.
A pressure-phase trace must open before initialization and remain open until
all final returned contributions are processed. Log native rank, phase,
time, activity and explicit cache lifetime. Verify owner/cache-instance
identity against the actual structures; do not assume that a particle ID or
pointer alone uniquely identifies an accumulator across cache lifetimes.

## Required implementation gates

Use a separate copied native tree and new runner/case directories. Preserve all
original arithmetic statements, traversal, MPI messages and numerical settings.
Observation may read fields and copy bytes into a bounded private trace, but
must not sort neighbors, replace accumulations, insert MPI barriers, change
compiler precision or use a new summation algorithm in the solver.

Record exact binary floating-point values before and after every selected
local update and remote combine, including the operands needed to replay it.
Include initializations, both local endpoint roles and final owner states.
Track a monotonic per-rank event sequence and explicit phase boundaries.
Do not claim an ordered complete ledger if events are missing, overflowed,
unmatched to cache lifetimes or observed outside an active phase.

Avoid formatting or disk flushing in each arithmetic operation. Buffer records
and write after the observed phase; this still has instrumentation effects.
Check the generated code's multiply/add/subtract contraction and rounding
before choosing the independent replay operations. Extra reads or compiler
spills can change execution even without an explicit solver-field write.

Freeze and hash the instrumented source, isolated executable, runner, tests,
input files, selection, schema and resource plan before any native trace.
Review the actual insertion points and exact source diff first. This design
does not certify an implementation that has not been written.

## Bounded initial experiment

Three new six-step historical-law diagnostics on the SAME isolated trace
binary: initialized output off A, off B and on. Each uses the original two
MPI workers, single-threaded numerical libraries and unchanged L3 chi100/Mach2
recipe. Only duration is shortened from the preserved 120-step input; output
interval 6, checkpoint interval 60, timestep and all other numerics stay fixed.
Retain the original checkpoint-schema environment and every native output.

No extra repeats are automatically authorized. The completed serial observer
is not rerun or folded into this build. Record trace timing overhead, but do
not call the resulting timings a solver optimization benchmark.

Budget at most 128 MiB trace data per case and 1 GiB for this complete new
stage, plus independent 10 GiB host and guest reserves. Validate the host mount,
take both existing native-work locks, require 12 GiB available RAM before
launch and 2 GiB while running. Use a 60-second limit per native case, then
the reviewed owned-process-group stop/grace policy. Overflow or incomplete
termination is a retained failure, not permission to drop records or raise caps
after inspecting results. No deletion, automatic restart or stale-PID signals.

## Validation and interpretation

Synthetic tests must cover owner versus cache initialization, both endpoint
roles, inactive endpoints, signed zero, repeated cache lifetimes, unequal
subtotals, changed order with identical operands, malformed/missing events,
overflow, exact ID selection and refusal to overwrite earlier stages.
Independent arithmetic replay must reproduce each observed addition/subtraction
and the recorded terminal accumulator in native order, at verified precision.

Compare all three cases. Separate exact input-multiset differences from order
differences. A counterfactual reordered replay is an ANALYSIS result only; it
must never replace native outputs. Claim an order-dependent contribution only
when identical starting values and operands with different observed orders
reproduce the corresponding different endpoints. Otherwise report the first
unresolved input/population/state difference without labeling it roundoff.

Check actual native states, timestamps, hashes and independent mass sums using
the existing validated readers. A trace can identify a mechanism within its
instrumented cases, not prove why a particular untouched historical repeat
diverged. It also cannot certify the subsequent velocity kick without tracing
that separately verified integration path, or clear the later density gate.

Do not change the one-spacing acceptance threshold. If further progress needs
a scientific repeatability/acceptance decision rather than a new concrete
diagnostic, present the preserved evidence and request that decision instead
of running an indefinite succession of traces.
