# Updated resolution-summary review

8 September 2026. **Assessment: share with caveats.** This is a report-only
extension, not a new native simulation or a repetition of prior analysis.

## Verified scope

The previous immutable summary has23 pairs/46 controls/4,650 native states.
All23 entries are preserved exactly. The two newly accepted level-4 pairs
(Gadget-4 and repaired MFV) add4 controls/404 native states, giving25 unique
code/level pairs,50 controls and5,054 native analysis states. Four Gasoline
L3/L4 controls remain validation-held; higher levels are additional work.

All13 scalar-source reports match their recorded SHA256 hashes. Both new
source reports have existing live-publication proofs. The merge validates
unique keys, exactly two velocity laws, matching within-pair physics,
parameters and binary hashes, fixed measured initial denominators, native
state counts, final fractions, preserved times and percentage units.
The reused L3 baselines match the newer source reports exactly.

Twelve new tests pass. They reject duplicate pairs, incorrect dimensions,
changed physical scope, missing laws, shifted denominators, wrong percent
units, truncated new series, unaccepted sources and changed binaries.
Regression tests preserve the actual non-identical native terminal times
and reject data outside the existing report-only endpoint envelope.

## Correction made before creating the summary

The first new merge check incorrectly required all endpoints to be within
1e-10 of5 t_cc. Its positive test failed on already accepted timestep-crossing
outputs (for example RAMSES L3 sharp ends at5.0042174855). The code now uses
the SAME report-only4.99..5.02 envelope as the existing summary extractor,
while preserving exact original entries. Code-native cadence validation
remains upstream and unchanged. No simulation, raw field, timestamp or
native acceptance criterion was altered to clear this summary bug.

## Methodology and presentation

Every table value links to its source report. Percentages refer to peak
paired dense-mass separation divided by the fixed initial dense mass for
that pair, not exact-solution error or a shared denominator across codes.
Native header times remain in the JSON; scalar interpolation is explicitly
labeled. Enzo's102 states per case are counted, not coerced to101.

The displayed native-code order is not sorted by numerical result, and
the table is not an accuracy ranking. AthenaPK's historical constant-outer-
momentum law remains distinguished from tanh velocity. Pressure deviations,
periodic boundaries, tracer availability, evolving particle resolution,
velocity staggering and restart-resume limitations accompany the results.
Two coarse resolutions do not establish convergence. Athena4.2's available
three-level sequence is non-monotonic, illustrating why a blanket
historical reuse/replacement decision is unwarranted.

No native outputs were opened and no old extractor/native tests were run.
The new script only reads scalar reports and publication proofs. All old
and new raw data remains retained. These tables are not raw backups or
new production3Dviewer entries; cooling/tracking and other Mach studies
are not certified here.

## Publication gate

Publish only the new custom extension/test/publisher scripts, summary,
validation, review and navigation links. Verify the precise staged paths,
byte hashes, relative links, a new matching local/remote commit and its
successful Pages deployment. Every changed live file must match its local
SHA256 before publication is claimed. Old immutable reports/proofs remain
untouched. A mismatch or failed deployment blocks the claim and requires
a corrective commit, not data deletion or history rewriting.
