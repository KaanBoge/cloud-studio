# Native MFM L4 test plan

8 September 2026. Scope: MFM only, level4 = 128x64x64 initial elements,
chi100/Mach2, historical versus sharp velocity. No MFV, cooling, tracking,
new boundary recipe, numerical-floor change, or checkpoint restart is admitted.

## Unit tests

Nine L4 tests cover unchanged original full-run numerical settings, exclusion
of tiny diagnostic timestep caps from production, exact nonvelocity arrays,
schema mismatches, refusal of existing directories/invalid modes, refusal of
L3 timing and storage evidence, and original dependency hashes. The frozen L3
helper bundle remains unchanged and has its existing15 tests. Neither suite
is a substitute for native evolved-output checks.

## Native integration tests

Run two L4 smokes to code time0.1 with original MaxSizeTimestep0.05. For each
law, run two isolated output-timing diagnostics to code time0.00004 with caps
0.00001 and0.000005. The small caps apply ONLY to these diagnostics. Preserve
all actual native terminal states, even if near-identical or extra.

Read every snapshot with direct native HDF5 and explicit yt GizmoDataset.
Verify 524288 unique elements, native field names/precision, finite positive
thermodynamic fields, periodic box bounds, input hashes and actual header times.
Initial coordinates/masses/IDs/internal energy must match the IC exactly;
all nonvelocity native fields must be identical within the pair and across
the corresponding timestep diagnostics. Report native kernel density/pressure
deviations from the nominal target rather than erasing them.

For each law, halving the diagnostic timestep must halve the native initial
velocity offset, and zero-step extrapolation must recover the IC within the
stated float32 rounding bound. Recompute this with L4 arrays, not L3 evidence.
The extrapolation validates an output convention only: no native velocity,
snapshot time, or scientific result is replaced by extrapolated values.

## Full-pair admission

Measure actual L4 snapshot, IC and eight-rank restart-set sizes. Budget104
snapshots, two retained restart generations with50% restart margin, IC and
256MiB logs per case, with15% overall margin. Reserve an additional10GiB
on BOTH the guest filesystem and Windows backing volume. Require native
8x1500MiB allocation plus4GiB available RAM before launch. The original native
restart interval3600seconds is unchanged. An external6000second limit and
60second checkpoint-stop grace bound retained generations; no auto-resume.

The frozen runner admits one sequential pair only after all L4 tests pass.
It rechecks input, executable, script, evidence and raw validation hashes.
All raw outputs, logs and restarts remain retained. Low memory/storage or a
runtime limit requests a native stop, not deletion of earlier results.

## Full-run acceptance and remaining gaps

Native exit0 alone is insufficient. Verify all actual output times through
5tcc, independent mass sums and positive fields, and recheck the paired
initial state. Only then analyze under a NEW directory, plot L3/L4 resolution
overlays with fixed initial mass denominators, and publish with verified live
hashes. The study accepted count remains40 until additional full controls
are validated and analyzed.

This plan does not certify no material crossed the periodic boundary or a
well-resolved/converged solution. There is no passive material tracer.
MFV's L3 stored-energy failure remains a separate unresolved issue.
