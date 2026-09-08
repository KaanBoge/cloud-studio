# Gasoline: where the saved trajectories first differ

8 September 2026. **The differences already exist in native double-precision
checkpoints, not solely in TIPSY export or website conversion.** They also occur
between two runs of the untouched executable. This narrows the investigation;
it does not prove the output hook harmless or identify the first causal operation.
The failed acceptance check remains failed. No simulation was run for this review,
no Gasoline full control was added, and the overall accepted count remains46.

## Existing data, new analysis

The [read-only protocol](DIVERGENCE_REVIEW_PLAN.md) uses all80 evolved snapshots
and all eight checkpoints from the existing four120-step, two-worker cases.
The earlier initialized state remains preserved and independently checked; this
new review does not count it again. All120 snapshot pair-times and12 checkpoint
pair-times are included in [the detailed report](divergence_review.json).
Native binary, object, source, raw and previous-report hashes were verified.

The first saved differences in the two direct repeat/output-observation pairs:

| Pair | Velocity first differs | Density first differs | Position first differs | Stored energy first differs |
| --- | ---: | ---: | ---: | ---: |
| Untouched original A/B | Step6 | Step78 | Step90 | Step102 |
| Retained build, output off/on | Step6 | Step90 | Step90 | Step102 |

There is a saved output every six native steps. These are the earliest
**observed saved differences**, not the exact onset within integration.
Step6 is approximately0.05 t_cc; step120 is approximately1 t_cc. All actual
timestamps are retained. At step6 the largest velocity differences are
1.66914e-17 (original repeats) and2.19009e-17 (output off/on), in code units.
The report lists particle IDs and components for subsequent targeted tracing.
All six pairings, including their unequal-field counts, are retained in JSON.

## Double-precision checkpoint evidence

Maximum absolute selected-field differences, in code units:

| Pair and step | Position | Velocity | Internal energy |
| --- | ---: | ---: | ---: |
| Original A/B,60 | 1.68598e-12 | 1.05058e-11 | 2.59348e-12 |
| Original A/B,120 | 2.01368e-8 | 1.27459e-7 | 7.31023e-8 |
| Output off/on,60 | 1.40898e-12 | 8.89139e-12 | 1.41398e-12 |
| Output off/on,120 | 1.86277e-8 | 1.27520e-7 | 7.38541e-8 |

Mass and softening are exact across these checkpoint comparisons. For **every
particle in all eight checkpoints**, converting the selected double fields to
float32 exactly reproduces the corresponding same-step TIPSY fields, including
the parameter-derived internal-energy conversion. Thus the exported differences
are not explained by a faulty TIPSY decoder. No density is stored in these native
checkpoints, so this is not a double-precision density comparison.

The original six failed density pair-times are reproduced unchanged. At step120,
the original-repeat failure concerns particle54857; the other failures and IDs
are all listed. Every density-threshold membership remains exact. That agreement
does not supersede the failed field test or certify later evolution.

## Source path and revised hypothesis

The actual SPH density path is `SMX_DENDVDX` in `master.c`, mapped in `smooth.c`
to `DenDVDX` (`smoothfcn.c:3390`). It gathers neighbour contributions into a local
sum; `combDenDVDX` at3378 combines active flags only. A direct asynchronous
**density-cache summation** explanation is therefore not supported for this path.

The actual symmetric force path is `SMX_SPHPRESSURETERMS` / `SphPressureTermsSym`.
Its cache callback `combSphPressureTerms` (`smoothfcn.c:2246`) adds acceleration
and energy-rate contributions; local updates are in `SphPressureTerms.h`.
The MPI communication layer processes received cache flushes through that callback
(`mdl/mpi/mdl.c:692-705`), with polling in `mdlCacheCheck` at1624. Different
interleaving of remote and local floating-point additions is a concrete candidate
for the earliest tiny velocity differences. Neighbour traversal/order and other
native state changes are still alternatives. This is source-supported reasoning,
**not experimentally established causality**.

The optional initialized output uses the existing serial output routine because
the native log confirms `iBinaryOutput=0`, despite `bParaWrite=1`. That routine
temporarily swaps remote particles for writing and swaps them back. No explicit
reordering is introduced by the hook. The effect of those operations on later
execution order has not been isolated. Do not call output observation inert based
only on its intention or matching mass curves.

## Decoder verification and limits

The exact original executable's `pkdWriteCheck` disassembly confirms120-byte
records and the selected integer/double prefix stores. All three source trees
share the same `pkd.o`; their hashes and binary identities are recorded. The native
FDL probe verifies finalized headers, counts, steps and times; file lengths are
exactly `offset + 65536*120`. A separate standard-library `struct` decoder checks
three records per file, in addition to the all-particle export roundtrip.

The FDL text's old float-particle declaration is not the actual checkpoint payload
layout. Native `CHKPART` does not store density or smoothing length; the restart
reader resets them. The selected decoder ignores flags as a physical diagnostic,
cooling tails, unwritten fields and padding. In this build the final `fTimeForm`
slot is not written by `pkdWriteCheck`; whole-record byte inequality must not be
interpreted as a physical difference. No checkpoint is resumed by this checker.

Ten synthetic tests passed for IDs, selected ABI offsets, malformed files,
nonfinite values, signed zeros, spacing distances, temperature scaling, independent
decoding and preservation guards. The source report is immutable:
`/home/kaan/sensitivity_20260907/gasoline/read_only_divergence_v1/report.json`.
SHA256 `96ee1e31635feae95674bd4777a0d9e5badc288a860112cb86dc40e6ef8957b2`.
Scripts: [review](review_divergence.py), [tests](test_review_divergence.py).
They require the explicitly pinned local native workspace, not a standalone solver.

Next is a prospectively specified, bounded native trace of a concrete mechanism,
if the source review supports it. Preserve the original two-worker numerics and
all failed evidence. Do not loosen the one-spacing gate or add unchanged repeats
until one passes. Full Gasoline L3/L4 controls remain scientifically held.
