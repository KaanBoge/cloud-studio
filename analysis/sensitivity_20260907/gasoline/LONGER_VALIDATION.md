# Gasoline longer output-observation test

8 September 2026. **Needs further review before full science controls.**
All81 native outputs passed finite/positive-field and independent yt mass
checks. The prospectively specified field-equivalence test did not pass.
The accepted study total remains44; these are diagnostics, not new5 t_cc
controls or production3D viewer entries. No native data was deleted.

## Experiment and result

Four fresh historical-law L3 cases used chi100, Mach2 and the original
two-worker Gasoline recipe: two untouched-binary repeats, an isolated retained-
checkpoint build with initialized output disabled, and that same build with
initialized output enabled. Each ran120 original-size steps, keeping output
interval6, checkpoint interval60, dDelta0.03227486122 and all original physics
and numerical settings. They saved20 evolved states each; the last case also
saved its actual initialized state, giving81 outputs. Actual terminal time is
3.872983346399991 code units, or1.0000000000497224 t_cc. No time was retimed.

The [original prospective protocol](LONGER_VALIDATION_PLAN.md) and
[historical-worker-count addendum](LONGER_VALIDATION_PLAN_2RANK.md) were frozen
before these runs. They require exact particle identity, mass, softening,
metals, potential and density-threshold membership, plus a one-float32-spacing
field criterion with explicitly declared characteristic floors. That criterion
is an engineering check, not a rigorous accumulated-roundoff bound or a
universal scientific significance threshold.

| Comparison | Field checks failed /20 | Failed output steps |
| --- | ---: | --- |
| Original A / Original B | 1 | 120 |
| Original A / retained output off | 0 | None |
| Original A / retained output on | 0 | None |
| Original B / retained output off | 3 | 108,114,120 |
| Original B / retained output on | 0 | None |
| Retained output off / on | 2 | 108,120 |

All six failures are density differences reaching two declared float32
spacings. The largest absolute density difference is1.52587890625e-5,
also observed between the untouched-original repeats. Position, velocity
and energy fields remain within their respective predeclared bounds.
**Every particle's density-selected membership agrees exactly at all20
matched times, so the measured dense masses agree exactly.** All81 independent
yt total/dense/color mass sums have zero reported discrepancy. This is a
limited measured result through1 t_cc, not full-trajectory equivalence.

The untouched binary is itself not bitwise repeatable, so this observation
does not establish that the output hook causes a physical change. Conversely,
we do not turn a failed field test into a pass, increase its limit after seeing
the results, or select additional repeats until a preferred result appears.
Native density routines accumulate floating-point neighbor contributions;
summation order is a plausible mechanism, not a demonstrated causal diagnosis.
No solver arithmetic, precision, floor or partition setting was changed.

The [full audit](longer_2rank_audit.json) preserves every comparison and native
state hash. [The review](longer_2rank_review.json) independently rechecks all81
raw states, their six native sidecars, all eight checkpoints, and the original
audit hash. It does not overwrite or rerun the original analysis.

## Eight-worker failure is a separate issue

The earlier120-step, eight-worker attempt failed in the **untouched binary**
entering step7: `pst.c:1254`, `nHighTot <= nUpperStore`, exit134. It saved one
native output at step6; the entire attempt remains intact. System memory was
not exhausted. Its per-partition particle capacity was exceeded. The original
saved full L3 run explicitly used two workers and completed, so the four new
diagnostics restore that worker count without changing dExtraStore0.2.
This is not evidence of an eight-worker speedup; scaling/allocation optimization
requires a separate validated test.

## Checkpoints and measured resources

The new isolated binary changes only the earlier hook build's checkpoint
filename logic: with `GASOLINE_CLOUD_KEEP_CHECKPOINTS=1`, names contain the
native step and existing targets are refused. The native checkpoint interval
and data fields are unchanged. Canonical Gasoline source/binary and both earlier
isolated builds remain preserved. New binary SHA256:
`7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3`.

Each test saved valid completed checkpoints at steps60 and120. Original
cases wrote chk0/chk1 without rotating far enough to overwrite either;
retained cases wrote distinct step filenames. The native log's success line
precedes finalization, so the read-only native FDL probe was applied after
solver exit. All eight headers have valid=1,65536 gas particles and expected
native steps/times; complete file lengths and hashes are retained. This checks
checkpoint retention and schema, not a resumed-trajectory equivalence test.

| Case | Solver seconds | Peak solver-child MiB | Median busy CPU workers |
| --- | ---: | ---: | ---: |
| Original A | 48.729 | 110.40 | 1.989 |
| Original B | 48.727 | 110.76 | 1.989 |
| Retained output off | 48.574 | 110.52 | 1.989 |
| Retained output on | 48.433 | 111.08 | 1.989 |

These are CPU-only120-step timings, excluding analysis and publishing. No
resource guard fired. They are not a full-run time promise or controlled
performance benchmark.

A full600-step L3 pair would retain101 actual states per case, including
initialized output, and ten native checkpoint generations at60..600. Measured
state sizes with all sidecars are6,661,723..6,680,426 bytes; reader-cache
allowance is909,387 bytes/state, and each checkpoint is7,869,465 bytes.
The conservative whole-pair budget is3,381,726,410 bytes (**3.15 GiB**), including
104 states and12 checkpoint slots per case, ICs,256 MiB logs per case and
25% extra margin. Separate10 GiB reserves apply to both filesystems. At review,
guest free space was16,956,719,104 bytes and Windows38,021,267,456 bytes.
**Storage fits this pair; scientific validation, not capacity, is the current
Gasoline hold.** No full runner has been enabled by these measurements.

## Reproduction and remaining checks

Native root: `/home/kaan/sensitivity_20260907/gasoline`.
`longer_validation_v1` retains the failed eight-worker attempt.
`longer_validation_2rank_v1` contains the four completed diagnostics;
`longer_2rank_audit_v1` contains the immutable81-state audit.
Audit SHA256: `3329dc075b9873cd608aa7a0ff9533ed4215c65145cc573c92190b3a23d544ff`.
The [frozen bundle](longer_2rank_bundle.json) pins native sources/builds,
the prospective protocols and six passing tests. Four audit tests and five
review tests passed; the earlier seven instrumentation tests remain pinned.
Passing software tests do not override the failed native scientific check.

Selected custom checking scripts are included here; their imports reference
the explicitly recorded, preserved local native workspace. They are not a
standalone solver distribution. Never relaunch frozen diagnostics or write an
analysis into an existing directory. Native solver sources, binaries, raw
outputs and checkpoints are not in this public analysis package.

Before full Gasoline controls: resolve the appropriate baseline-repeatability
and output-observation validation, check sharp initialization with the retained
build on the same two-worker count, then freeze/test a new guarded full runner.
No extra unchanged repeats or post-hoc tolerance adjustment is proposed here.
Original periodic boundaries, variable-mass SPH pressure variation (initial
P0.73795..6.29124 versus nominal1), and staggered pressure-field semantics
remain disclosed. Mass controls do not certify pressure uniformity, evolved
velocity timing, all-material retention, cooling or frame tracking.
