# GIZMO L3 delivery validation

8 September 2026. **Share MFM with caveats; MFV needs review.**

## Methodology and calculation checks

The question is within-code sensitivity to the historical versus sharp
velocity prescription, at fixed chi100/Mach2 and initial L3 resolution.
Identical nonvelocity input arrays, binary, parameters and seed are enforced
within each method's pair. The fully periodic boundary recipe is retained;
this is not certification of the grid codes' inflow/outflow setup.

Both MFM controls have 101 actual native times. All 202 states passed native
schema/finite/positive-field checks and independent yt mass sums. A fresh
pre-delivery read verifies every native hash and repeats direct mass sums,
normalization and the scalar peak calculation. The direct mass recheck and
recorded independent sums have zero reported relative discrepancy. This does
not imply exact physical accuracy: the stored scalar fields are float32.

The denominator is the same measured initial dense mass in both controls,
with rho > rho_cloud_initial/3 at every time. The peak separation is
0.039790264893005745 of that denominator, using stated scalar interpolation
onto 0:0.05:5 t_cc. The plot itself uses the actual native times. It is visibly
labeled as a single-resolution pilot, uses zero-based mass axes and distinct
colors/line styles, and was visually inspected. No resolution convergence or
all-material-retained terminal image is asserted.

All 15 frozen setup/timing/runner unit tests pass. Native snapshot-velocity
staggering is supported by separate timestep-scaling evidence; simultaneous
velocity-at-header-time analysis remains outside this validation.

See [delivery_validation.json](delivery_validation.json),
[mfm_l3_report.json](mfm_l3_report.json) and [full_l3_tests.json](full_l3_tests.json).

## High-priority failure: MFV stored energy

Both native MFV runs exited zero and wrote 101 distinct native states through
5 t_cc. The independent field audit still rejects the pair: InternalEnergy
is zero in 15 sharp-case and 16 historical-case snapshots, first at3.95 t_cc.
Mass, density and smoothing length remain positive; all stored fields are
finite. All affected IDs and original times are recorded, not clipped out.

Native I/O saves a floor-clamped predicted internal energy. The exact cause
of the zero predictor/output is unresolved, and conserved internal energy
was not inferred from the output. Occurrence in both laws is evidence against
blaming only the newly sharp boundary, not proof of a universal MFV defect.
No floors, solver settings or output values were modified. The MFV pair does
not count toward the 40 accepted controls, and no favorable subinterval is
substituted for the complete failed experiment.

See [mfv_pair_audit.json](mfv_pair_audit.json) for all 202 native states.

## Scope, retention and deployment

L3 has only 3.2 initial elements per R. L4 requires new per-level checks.
There is no passive material tracer; periodic in-box material is not a
no-boundary-crossing diagnostic. Native kernel density/pressure deviations
and the documented velocity staggering remain limitations.

All raw data, ICs, logs, restarts and failed attempts remain local and unchanged.
The public package contains custom scripts, configuration, hashes, scalar
diagnostics and the plot. It is not a raw backup or a set of production 3D
viewer entries. Publication must verify an advanced remote commit, successful
Pages deployment and matching live report/plot bytes. Roll back only the
publication commit if its links or data differ; do not touch native runs.
