# Gasoline: native force addition order affects selected sums

8 September 2026. **Share with the limitations below. No full Gasoline control
is accepted or enabled.** The study still has46 validated full controls;
eight full L3/L4 controls remain pending, plus higher levels.

In27 paired accumulator comparisons, identical starts and recorded
contributions in different native orders reproduce different force or
energy-rate endpoints. This identifies an addition-order mechanism within
these instrumented cases. It does NOT explain every discrepancy, prove the
output hook harmless, or clear the earlier one-spacing density failure.

## What actually ran

Three six-step historical-law diagnostics on the same isolated Gasoline
executable: initialized output disabled A, disabled B, and enabled. All use
the original two MPI workers, chi=100, Mach=2 and existing L3 recipe
(64 x 32 x 32 initial elements). Only the120-step diagnostic duration was
shortened; timestep, output interval6 and checkpoint interval60 remain.
The original checkpoint-schema environment and retention hook were retained.
No production queue or canonical solver source changed.

| Case | Native wall time | Median busy CPU workers | Peak summed solver RSS | Real native states | Finalized checkpoints |
| --- | ---: | ---: | ---: | ---: | ---: |
| Output off A | 3.373 s | 1.963 | 99.16 MiB | 1 | 1 |
| Output off B | 3.375 s | 1.961 | 99.46 MiB | 1 | 1 |
| Output on | 3.321 s | 1.962 | 102.59 MiB | 2 | 1 |

These are observed short runtimes, not an optimization benchmark or Level6
forecast. No GPU or resource-guard stop occurred. All runs ended at code
time0.19364916732, approximately0.05 t_cc; output-on also writes the initialized
native state at t=0. All four actual TIPSY states pass finite/positive field
and independent yt mass checks. Total mass2425.245532028377 and selected dense
mass409.90798234939575 agree exactly between direct and yt sums in each state.
The initialized selected IC fields match exactly. All three step6 checkpoints
have valid version8 headers, correct time/count/length and retained hashes.
This is not checkpoint-resume validation. Sidecars are retained, but not every
sidecar quantity is independently checked.

The four states bring the cumulative independently checked Gasoline
**diagnostic-state count to101 across different short tests**. This is NOT
a101-frame full Gasoline simulation and adds zero full science controls.

## Trace implementation and checks

The [core checks](FORCE_TRACE_CORE_VALIDATION.md) and
[native design](FORCE_ORDER_TRACE_DESIGN.md) preceded this work. Their earlier
status statements describe those completed stages at writing time; this
report describes the subsequent completed native implementation and analysis.

The adapter preserves every original line in the three instrumented native
source files, inserting observations around original statements. It tracks
owners, reused cache lifetimes, original baselines, native resets, local
updates, incoming subtotals and final states. Buffered records flush outside
each pressure phase. No numerical setting, arithmetic statement, neighbor
order or MPI barrier changed. Tracing/recompilation can still affect timing
or compiler behavior.

Both synthetic adapter streams passed (292/238 records); four runner tests
passed. The completed core had15 Python tests plus C transport/overflow checks.
Selected compiled functions contain scalar-double operations, with no detected
fused or x87 arithmetic in those functions. The recorder requires binary64
round-to-nearest. This is not a global compiler-equivalence proof; exact
native recorded-operation replay is the decisive selected-operation check.

All six rank streams finalized, covering13 pressure phases and the seven IDs
selected before running. Every selected native factor/add/subtract and
owner/cache continuity check passed.

| Case | Rank0 records | Rank1 records |
| --- | ---: | ---: |
| off A | 24,136 | 18,745 |
| off B | 24,135 | 18,744 |
| on | 24,135 | 18,744 |

## Read-only comparison

The [comparison protocol](FORCE_COMPARISON_PLAN.md) was frozen before analysis.
All13 phases x7 IDs x6 fields give546 owner accumulators per case and1,638
paired comparisons across all three case pairs. Alignment uses exact native
time bits, phase, ID and field, not rank or rounded time. No records were
dropped or interpolated. The actual post-initialization start is used while
retaining pre-initialization values and reset counts. Strict contribution
multisets include operation, exact operand, local/remote kind, partner ID,
factor bits and activity. A remote term is its actual incoming subtotal,
not a full remote-neighbor reconstruction or sending-rank identification.

| Pair | Tested sums | Different endpoints | Identical inputs: order explains endpoint | Changed starts | Changed contributions |
| --- | ---: | ---: | ---: | ---: | ---: |
| off A / off B | 546 | 69 | 7 | 28 | 34 |
| off A / on | 546 | 133 | 13 | 59 | 61 |
| off B / on | 546 | 114 | 7 | 50 | 57 |

The last three columns partition different endpoints, not all546 sums.
Changed-input cases that happen to end identically also remain in the
[complete comparison](force_comparison_report.json). These27 are paired
field/phase comparisons, not27 particles or independent statistical samples;
one accumulator can appear in two pairs.

The first selected difference for off A/off B and off A/on is particle23013's
artificial-viscosity energy rate at phase3, time0.03227486122. Its operands
already differ, so it is NOT explained by order alone. Endpoint separation is
8.536284483939527e-44 in code units.

For off B/on, the first selected difference is particle36578's streamwise
acceleration at the same phase/time. Its146 contributions and zero start match
as a strict multiset; different orders reproduce endpoints
`0xbce2400000000000` and `0xbcde6c0000000000`, separated by
3.37403716077489e-16 in code units. This example also occurs for off A/on.
Off A/off B first meets the strict order condition at phase11, time
0.1613743061, for particle36578's streamwise acceleration (125 contributions).

Thirteen comparison tests pass. A separate reader importing neither the main
parser nor comparator independently checks all27 positive order claims:
54 owner sums replay exactly using rational addition/subtraction rounded to
binary64 at every native operation. All1,638 summary counts reconcile.
See [independent review](force_comparison_review.json). This independently
checks every positive order claim, not every changed-input classification.

## Limitations and next decision

This is not proof about the later velocity kick, unobserved state, untouched
original trajectories, output-observer effects or physical insignificance.
It does not establish that all differing inputs are merely roundoff. Original
SPH pressure and periodic-boundary limitations remain. The previous
field-equivalence gate is still failed.

A scientific decision is now needed on whether and how to assess measured
repeatability for Ryan's dense-mass comparison. Do not silently replace the
failed threshold. After that decision, sharp-IC validation on the same chosen
executable and a separately guarded full runner remain required. No more
traces or threshold changes are automatically scheduled to avoid that choice.

## Reproducible files and retained evidence

Custom scripts: [core](force_trace_core.h), [replay](force_trace_replay.py),
[adapter](force_trace_native.h), [build preparation](prepare_force_native.py),
[native runner](run_force_order.py), [comparison](compare_force_order.py),
[independent review](review_force_comparison.py). Tests/plans are alongside.
They depend on the documented local native tree; the site does not host the
upstream native source, executable or raw files. Entry points refuse completed
directories. Do not rerun completed stages; new work needs a new reviewed plan.

Native root: `/home/kaan/sensitivity_20260907/gasoline`. Completed directories:
`force_trace_core_v1`, `force_order_native_v1`, `force_order_prepare_v1`,
`force_order_runner_v1`, `force_order_cases_v1`, `force_order_compare_v1`,
`force_order_review_v1`. Every native state/checkpoint/trace, original binary
and failed earlier attempt remains local. Website analysis is not a raw backup
or a new production3D viewer run.

| Evidence | SHA256 |
| --- | --- |
| Trace executable | `789dd4625f9ef2f3ed32bd731be207b617d5b723e66ae4d6300846af8adb686b` |
| [Native report](force_native_report.json) | `94ed097aa774b930c065bb1710d2c4f4f9d4cf618adcf09c52b23debf8822b97` |
| [Comparison](force_comparison_report.json) | `5c78fd85a3f5dc35800443a200955a883ecd97dce512b1bc7af665c48c66f7ef` |
| [Independent review](force_comparison_review.json) | `a20b4b4a746a83d701bd528e1958c40eb287321a4c5b988d2d6e8f6c3c1c453b` |

[Build evidence](force_native_build.json), [native plan](force_native_plan.json)
and [comparison plan](force_comparison_plan.json) preserve source/input hashes.
