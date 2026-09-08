# Flash-X analysis QA, 8 September 2026

## Overall assessment: Share with caveats

Four within-code controls at chi=100, Mach=2 and L3/L4 test historical tanh
versus sharp initial velocity. The same pinned native Flash-X binary, inputs,
density profile, geometry and solver settings are used within each pair.
Only velocity and consistent kinetic energy change. Initial density/grid and
unchanged auxiliary fields are exact; thermodynamic recovery is roundoff.

## Data and calculations

All 404 actual checkpoint times, every eleven-field float64 checkpoint, and
all original five-field float32 plotfiles passed native checks. They remain
on disk without thinning, timestamp changes or synthetic frames. Independent
yt sums agree with every native mass sum within 4.01e-16 relative discrepancy.
Seven launcher and two analysis tests pass. Input and binary hashes are saved.

Dense selection is rho>rho_cloud_initial/3 with an identical measured initial
mass denominator within each pair. No changing in-box denominator is used.
Peak scalar-curve separation is 0.101329 at L3 and 0.065430 at L4, on the
explicitly stated 0:0.05:5 t_cc scalar interpolation grid. Final fractions are
zero/zero at L3 and 0.034884/0.058855 at L4. Comparing only the last L3 state
would conceal the earlier difference.

## Visual review and limitations

The mass plot was inspected at output size. Actual native times are plotted,
including terminal overshoot. Axes are shared, resolution colors and velocity
line styles are consistent, labels readable, and no replay/duplicate invented.

These are coarse sensitivity controls, not accuracy errors, convergence proof
or a universal decision to reuse old simulations. No passive tracer exists,
so mass loss cannot be uniquely attributed to mixing rather than material
leaving the box. There is no all-material-retained terminal-image claim.
No cooling or tracking is enabled. Full-state checkpoint cadence and noncycling
retention were increased identically in both controls; precision and original
plot fields were not reduced. L5 remains storage-held. Additional resolutions
and Ryan's interpretation are needed before deciding on historical reuse.
