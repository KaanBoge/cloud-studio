# Gasoline initial-output and repeatability audit

8 September 2026, approximately 10:27 Istanbul time.
**Preparation evidence with limitations; no full Gasoline controls completed.**

Later update: [LONGER_VALIDATION.md](LONGER_VALIDATION.md) reports the new81-state,
two-worker prospective diagnostic and complete checkpoint retention. Its
field-equivalence criterion failed, including original-binary repeats; all
mass checks passed. The earlier evidence below remains unchanged in meaning.

## Completed native work

The existing original Gasoline binary was copied byte-for-byte, SHA256
`c7645e1774fb4a18fc68bac615ba03f24c83d06dfe4addfbbbc7df2cc4930bb5`.
Native tracked source commit is `ef8f8491afb55ea20a3c63bc0553bafd779f2cfa`.
The canonical source, objects and executable remain unchanged. An isolated
build copied the existing object files and changed only `main.c`, its object
and the linked executable. All other copied hashes remain identical.
Hook binary SHA256 is
`7f3018e12f821fe9f74ae2617d80b11cf1e7f7feedd8040ceafc01822a21789e`.

The optional `GASOLINE_CLOUD_INITIAL_OUTPUT=1` hook writes the initialized state
after native `msrInitSph`, without explicitly reordering particles or changing
physical/numerical settings. It is disabled by default. Native iOrder and
pressure sidecars are explicitly enabled in every short-test input, including
the original-binary controls. They identify particles and expose native field
semantics. The standard positive-step executable otherwise writes no complete
initialized t=0 state; the old input IC is not such a state.

Four six-step runs compared original/hook-off/hook-on historical inputs and
hook-on sharp inputs. Two additional fresh original-binary repeats tested
baseline variability. All used eight MPI ranks, L3 (65536 gas particles on a
64 x 32 x 32 equal-volume lattice), chi100 and Mach2, original dDelta,
KDK, nSmooth64, CFL0.4, periodic boundaries, adiabatic gas and no gravity.
Their only output-time changes were six total steps and interval three.
All native sidecars and final checkpoints remain retained.

The actual archived two-module generator reproduces every field of the saved
old L3 IC exactly, including its full file hash. Its separate sharp counterpart
has identical nonvelocity arrays. Each module pair was isolated to prevent
Python import caching from mixing the velocity laws. No equal-mass substitution.

## Evidence and acceptance boundaries

Seven unit tests pass, also run from the frozen instrumentation bundle. They
cover schema, duplicate parameters, conversion conventions, invalid fields,
truncated/extra payloads and accidental report overwrite. The six native
short runs produced 14 actual outputs: two per original/off/repeat case,
three per hook-on law including initialization. All 14 raw-field mass sums
were checked independently with yt. Native timestamps were retained exactly:
0 where enabled, 0.09682458365999999 and 0.19364916732 code time.

Native initial nonvelocity fields are exactly equal between sharp and
historical laws after iOrder mapping. Initial coordinates, masses, velocities,
stored energy and metals recover their respective IC fields exactly. Native
SPH density differs substantially from the analytic lattice density. Pressure
at initialization spans **0.7379456 to 6.2912392**, identically in both laws,
versus nominal one. Initial pressure recovery agrees within 5.94e-8 relative
difference, within the unchanged float32 recovery bound. The fixed measured
initial dense mass is 409.907982349396; color-weighted mass is368.730141946053.

At the two evolved times, original/off/on outputs agree exactly in density,
mass, positions, stored energy, softening, metals and potential. They fail
strict bitwise velocity equivalence. The maximum hook-off/on difference is
5.684341886080802e-14 in code velocity, while the maximum among the three
original-binary runs is2.842170943040401e-14. The original itself is not
bitwise repeatable in those tiny velocities. The hook difference is not
contained within the maximum measured original repeat range, so neither
strict equivalence nor a demonstrated no-effect bound is claimed. No
additional repetitions were selected to hide this result. Further review of
this roundoff-scale observation is required before enabling a full runner.

These short tests are not a full-trajectory equivalence proof, a speed
benchmark, a resolution-convergence study or a new production-viewer entry.
Original/hook-off/hook-on historical and hook-on sharp solver timings were
1.664/1.512/1.664/1.665 seconds, with peak summed child RSS approximately
0.288/0.281/0.290/0.289 GiB. Timing excludes analysis and publication.

## Pressure-stage diagnosis and preserved failed checks

The first verifier incorrectly equated evolved `.pres` with pressure recovered
from the TIPSY energy. Its 1.65% discrepancy is preserved in
`validation_v1/partial_report.json`. Native `pkdGasPressureParticle` and
`pkdGasPressure` use `uPred` to cache `PoverRho2`; `OUT_PRES_ARRAY` writes
rho squared times that cached value. `msrTopStepKDK` then calls the closing
kick, changing energy before `pkdWriteTipsy` writes `duTFac*p->u`. These are
different integration-stage quantities, not interchangeable pressure fields.
The unchanged precision check still applies at initialization, where uPred=u.
No evolved pressure-at-header-time or velocity-synchronization certification
is claimed. Mass diagnostics read native density/mass, not a reconstructed
SPH kernel or the cached-pressure field.

The second verifier preserved this distinction but failed because importing
yt's data-structure module alone did not register its TIPSY I/O handler.
`validation_v2/partial_report.json` remains intact. Version3 imports the native
frontend API, checked all ten original short outputs independently, then
failed strict velocity equivalence. That partial report is retained too.
Two later original-binary negative controls added four independent checks;
they did not rerun or overwrite any earlier case. The final repeatability
audit reports the exact failure and all measurements, without raising a
tolerance or rewriting data.

## Preserved artifacts and next steps

Native root: `/home/kaan/sensitivity_20260907/gasoline`.
`instrumentation_v1` holds the four first cases, `repeatability_v1` holds two
new negative controls, and `repeatability_audit_v1/report.json` records all
measurements. Its SHA256 is
`b26dbfa39c8571b172d58b74bd9138d4f80b40e6ce724921301bc82cb7b0d665`.
No native data, checkpoint, sidecar or failed report was deleted.

Before a full L3 pair: complete output-hook review, measure complete retention
including **every** rotating native checkpoint generation, freeze/test a new
guarded full runner, and verify both filesystem budgets with 10 GiB reserves.
No old runner, frozen short-test runner or existing case may be relaunched.
L4 requires its own native/independent validation. The full accepted study
count remains44, with eight L3/L4 controls unlaunched across the remaining codes.

These are preparation and failure evidence, not accepted full controls.
Publication is verified separately; web analysis artifacts are not native raw backups.
