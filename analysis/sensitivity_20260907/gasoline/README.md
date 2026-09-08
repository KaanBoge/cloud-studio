# Gasoline native velocity-control preparation

8 September 2026. **No full Gasoline controls are accepted; the study now has
46 accepted controls from other codes.** The [read-only divergence review](DIVERGENCE_REVIEW.md)
finds differences already present in double-precision checkpoints, including
untouched-executable repeats. All selected checkpoint fields reproduce their
TIPSY exports exactly. The cause and output-observation acceptance remain under
review; no additional simulation or changed tolerance was used.
Four longer diagnostic runs have now completed on the historical
two-worker count, producing81 actual native states through approximately
1 t_cc. All independent mass checks pass, but the predeclared field-equivalence
test fails in six of120 comparisons, including untouched-binary repeats.
See [the new results, exact failed checks and retention budget](LONGER_VALIDATION.md).
The earlier14-state evidence remains in [VALIDATION.md](VALIDATION.md).

This compares the actual archived tanh velocity law with the current sharp
boundary at 1.3 R, at fixed chi100/Mach2 in Gasoline's own existing recipe.
Both versions of the two-module IC generator are isolated. Equal-volume,
variable-mass lattice sampling, the native periodic box, numerical settings
and original adiabatic thermodynamics must remain identical within each pair.

The original positive-step solver does not save its fully initialized t=0
state. The historical recipe counted its input IC plus 100 evolved outputs.
An input IC is not an initialized native SPH density/pressure measurement.
The native zero-step diagnostic path writes selected arrays, not a complete
TIPSY state. An isolated optional output-only hook is being tested; no
canonical native sources, objects or executable are modified.

## Required tests before any full control

1. Hash all copied native sources, existing objects, binary and generators.
2. Reconstruct the historical IC exactly and verify equal nonvelocity fields.
3. Verify the XDR TIPSY schema and parameter-derived energy conversion.
4. Compare original binary, isolated hook disabled and hook enabled at the
   same evolved times. The original exact-field test failed and remains a
   failed record. The separate prospectively defined longer test also failed;
   neither is retroactively passed by changing a tolerance.
5. Check native initialized state, density/pressure, particle identity mapping,
   finite positive fields, and independent yt mass sums.
6. Measure all retained snapshot/sidecar/restart sizes and whole-pair budget;
   keep separate 10 GiB guest and host free-space reserves.
7. Freeze and test a guarded runner before full science runs. Never overwrite
   existing output folders or resume checkpoints automatically.

An isolated filename-only change now retains checkpoints by native step,
without changing their interval60 or fields. All eight checkpoints from the
longer tests have valid finalized native headers and unchanged hashes.
No outputs, including native ion fraction sidecars, may be deleted. Output
instrumentation is not a change to cooling, gravity, boundaries or timesteps.
The stored TIPSY `temp` field is converted using the native input's dGasConst,
gamma and mean molecular weight; it must not be assumed to be Kelvin.
SPH reconstructed pressure and boundary mismatches must be reported rather
than concealed to claim a matched grid-code baseline. These controls remain
separate from production viewer entries and do not add to the current46.

The untouched original binary, rebuilt hook-off and hook-on tests agree exactly
in native density, mass, positions, energy, softening, metals and potential at
the two evolved test times. They do not agree bitwise in tiny velocities:
hook-off/on differences reach 5.6843e-14, versus 2.8422e-14 among three runs of
the original binary. This is not a passed exact-equivalence test or evidence
of a scientifically significant effect. No tolerance or native data was
changed to turn the failed check into acceptance.

Fourteen native outputs now have independent yt raw-field mass checks. The
two initialized states agree in every nonvelocity field and exactly recover
their respective IC velocities. Their SPH pressure spans 0.73795 to 6.29124
at nominal pressure one. This original sampling/kernel limitation is retained,
not silently corrected within a velocity-only study.
