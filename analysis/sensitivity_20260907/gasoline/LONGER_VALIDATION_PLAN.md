# Prospective finite-precision and checkpoint validation

8 September 2026. Recorded before the longer native tests; these have not run.

The original strict bitwise velocity test remains failed, including between
repeated runs of the untouched binary. The maximum of three original repeats
is not a guaranteed bound on future floating-point variation. We will not
relabel that test as passed or expand its tolerance. A separate, longer
diagnostic asks whether observations change the actual mass experiment at
the native saved-field precision. This is a different, explicitly limited
claim, not a proof of bitwise or mathematical trajectory equivalence.

## Independent prospective test

Use four new native L3 historical-law controls, each120 original-size steps,
at the original output interval6: two untouched-binary repeats, one isolated
binary with the initial-output hook off, one with it on. Same IC, eight ranks,
native timesteps, SPH settings and physics throughout. This reaches about one
cloud-crushing time,20 evolved states each, plus one initialized native state
for the hook-on case. No native saved time or field is edited. These are
diagnostics, not completed5t_cc sensitivity controls.

Report strict bitwise comparisons separately regardless of outcome. For the
new finite-precision diagnostic, require at every corresponding actual time:

* Exactly identical IDs, masses, softening, metals and potential.
* Exactly identical density-threshold membership for every particle and thus
  identical density-selected mass, not just a visually similar curve.
* Density and stored energy differences no greater than one float32 spacing
  at the larger absolute compared value, with nominal wind density and the
  original cloud specific energy as respective nonzero reference floors.
* Position differences no greater than one float32 spacing at the larger
  absolute compared coordinate, floored by the original lattice spacing.
  Report direct and minimum-periodic-image differences separately; no saved
  positions are wrapped or rewritten by the analysis.
* Velocity-component absolute differences no greater than one float32 spacing
  at the larger compared speed or the prescribed wind speed, whichever is
  larger. This is a nondimensional field-accuracy check relative to the wind,
  not an assertion of one local ULP for near-zero transverse velocities.
* All native fields finite, density/internal energy positive, all actual
  timestamps present and identical among controls. Independent yt raw-field
  mass checks verify every output. No failed state may be discarded.

The spacing rules derive from the actual native TIPSY float32 serialization,
not the observed6-step differences. They do not alter solver precision. They
are an engineering criterion for this mass diagnostic, not a rigorous forward
error bound, a convergence criterion, or a universal scientific significance
cutoff for the historical-versus-sharp effect. If any condition fails, retain
and report the full results and investigate; do not adjust it after seeing
the longer results. Exact initial within-pair checks remain unchanged.

## Native checkpoint preservation

Copy the isolated source/build into a new native-retention tree. Under a
separate opt-in environment flag, change only checkpoint filenames to include
the native step. Preserve original interval60 and every native checkpoint
field. No canonical source or frozen initial-output build is modified. The
original-binary120-step diagnostics write only chk0 and chk1, so neither slot
is overwritten. The retained-name build must produce completed checkpoints
at60 and120, with identical native step/time/count/schema and all fields.

The native success log line precedes not_corrupt_flag=1 and FDL_finish, so it
is not a safe archival-completion signal. Verify checkpoint headers with the
native read-only FDL library after each solver exits. For longer production,
unique names preserve generations without racing a polling/copying watcher.
Reject duplicate targets; fresh output folders and both shared locks remain
mandatory. Raw, restarts, sidecars and failed attempts all remain retained.

Measure the complete four-test output budget before launch, with margin and
the separate10GiB reserves on both guest and Windows. Freeze source/config
hashes, this protocol and regression tests. No full science runner is enabled
by this plan alone. All-code matched-pressure/boundary certification, cooling,
tracking and evolved pressure-stage diagnostics remain outside this test.
