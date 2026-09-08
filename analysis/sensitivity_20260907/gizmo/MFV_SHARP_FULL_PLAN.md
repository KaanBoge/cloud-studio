# Missing repaired sharp MFV L3 control

8 September 2026, after sharp preparation passed and before full launch.
Preparation validation41933e9cee047882a0008fe9505e7790151daa7abcef3c619fc03a4699ba97da
contains eight native states from three new sharp diagnostics. Initial
nonvelocity arrays match the retained repaired historical short/full states
exactly. Sharp half-kick scaling is0.50013555 and zero-step error2.3842e-7,
below the unchanged float32 bound1.2312e-6. Sixteen runner tests pass.

Launch ONLY one new full sharp control. Copy the retained original sharp IC
and parameter file byte-for-byte; use the exact same repaired binary as the
completed historical diagnostic. Eight MPI ranks, no source/build/numerical
changes. End19.364916731037084 code (5t_cc), interval0.19364916731037085
(0.05t_cc), initial64x32x32 lattice. Native periodic boundaries and all original
kernel-pressure deviations remain. Short diagnostic timestep caps are absent.

Recheck historical evidence and every raw hash before launch. The historical
full native run is reused, not rerun; its one-assignment repaired executable,
input schedule, nonvelocity ICs and launch recipe satisfy this within-code
pair. Original uninitialized-timestep MFV runs remain excluded and retained.

Budget104 snapshots,3 restart sets,IC and256MiB logs plus25% margin, in
addition to separate10GiB guest/host reserves. Require12GiB free guest RAM
preflight and2GiB live. Both shared locks, no competing solver/build,600s
external cap below3600s native restart interval,30s native-stop grace then
bounded stop of the owned process group. No raw deletion or automatic resume.

Validate every native state and independent yt mass sum, initial paired
nonvelocity arrays,60-bit native output schedule and all eight terminal
restart prefixes. Full conservation gate uses the unchanged prospective
onset model with K<=32768 and pending dMass included. Require positive finite
energy/density/mass/pressure and a detected mass response. Hash-check inputs,
binary, outputs and restarts after validation. Keep failures; do not loosen
criteria. Prefix parsing is not authorization to resume a checkpoint.

Only after both controls pass, compute dense mass at rho>initialcloudrho/3,
normalized by the SAME measured initial dense mass. Keep native times for
both curves. For a descriptive peak separation only, explicitly interpolate
scalar masses onto0:0.05:5t_cc; do not interpolate or retime3Dframes.
This is one coarse resolution, not convergence, exact-solution error or a
universal reuse decision. No tracer retention, cooling, tracking or identical
cross-code boundary/pressure claim. Full accepted total can increase44to46
only after paired validation; publication requires separate live verification.
