# FLASH analysis QA, 8 September 2026

## Overall assessment: Share with caveats

Question: within native FLASH 4.8 at chi=100 and Mach=2, how does replacing
historical tanh velocity with sharp velocity affect density-selected mass?
This is a within-code sensitivity experiment, not a universal accuracy test.

## Source and calculation checks

Four L3/L4 controls, 101 actual native checkpoint times each, are recorded in
`batch.json`. All thirteen full-state float64 fields and all original five
primitive quantities plus temperature in float32 plotfiles remain on disk.
No raw dataset was overwritten, retimed or thinned. The pinned binary, inputs
and canonical-source preservation hashes are recorded. Initial density and
grid agree exactly within pairs; pressure differences are recovery roundoff.

The denominator is each pair's identical measured initial dense mass; the
selection is rho > rho_cloud_initial/3. It is not divided by changing total
in-box mass. All 404 direct native leaf-cell sums were checked with yt's FLASH
frontend. Maximum relative discrepancy is 5.55e-16. All times, fields and
uniform coverage passed native validation. Seven launcher tests and two
analysis tests pass, including rejection of incomplete/repeated curve times.

Peak scalar-curve separation, normalized by initial dense mass, is 0.103697
at L3 and 0.061655 at L4. This calculation explicitly linearly interpolates
scalar diagnostics to 0:0.05:5 t_cc; it does not interpolate native frames.
At the last actual output, L3 dense fractions are zero for both cases; L4
sharp/historical fractions are 0.0402735 and 0.0548356. A final-only comparison
would miss the L3 effect.

## Visual review

`mass_evolution.png` was inspected at full output size. Both resolutions use
the same time and mass axes. Color distinguishes resolution, line style
distinguishes velocity law, and all four curves have readable labels. The
plot uses unchanged actual native times and includes the slight native
timestep overshoots beyond 5 t_cc. No hidden duplicate/replay is introduced.

## Required caveats

L3/L4 have only 3.2/6.4 cells per cloud radius and do not establish convergence.
No arbitrary significance threshold was selected after seeing the results.
The native recipe has no tracer: cloud-material retention is unknown, not
zero or one. Density-threshold mass does not distinguish mixing from material
leaving the box. These terminal images are not certified as retaining all
material. Full-state checkpoint cadence was increased identically in both
fresh controls and checkpoint overwriting disabled; native solver precision
and original plot fields remain unchanged. No cooling/tracking claim follows.

L5 requires additional storage; no quality/field reduction was used to bypass
the guard. Discuss the measured sensitivity and resolution dependence with
Ryan before deciding which historical results can be reused.
