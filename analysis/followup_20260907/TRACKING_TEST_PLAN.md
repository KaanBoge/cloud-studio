# Extended tracking validation plan

The user requested the existing conditions be preserved. This test campaign does
not change the density profile, velocity boundary, Mach=2, chi=10/100/1000,
20R x 10R x 10R domain, boundaries, equation of state or native executable.
It does not launch cooling, large production runs or any data deletion.

Tests use a separately versioned directory and preserve all native files.

| Check | Test type | Acceptance and limitation |
|---|---|---|
| Late restart, all three chi | Native integration | Final native fields agree with the retained uninterrupted trajectory within 1e-10 scaled max error |
| MPI 1 vs 4 ranks | Native integration | Short-run final fields agree within 1e-10; this is not a speed benchmark |
| Frame displacement | Every-step native history | Integrate previous frame speed over measured step times; max absolute error <=1e-10 |
| Snapshot/frame pairing | Native IO | Every native snapshot has contemporaneous high-precision frame history |
| Tracer integral | Independent field/history calculation | Volume-weighted native rho*C agrees with native history within 1e-10 relative |
| Density, pressure, tracer, IC | Field validation | Finite fields, positive density/pressure; initial conditions match unchanged analytic setup |
| L4 chi sweep to 5 t_cc | Resolution/retention integration | Count every measured snapshot, report actual times and tracer mass budget |

The existing L3 data are reused for restart comparisons and retention context.
New L4 tests resolve 128x64x64, twice the linear L3 resolution. They are NOT a
convergence demonstration or the entire paper comparison. A 1% net tracer-mass
criterion is reported as a diagnostic, not proof that zero material crossed a
boundary. A failed retention check must remain a failure; it is not waived because
the executable finished normally. No nominal frame timestamps are substituted for
native times. Frame metadata allow x_lab=x_frame+frame_x and v_lab=v_frame+frame_v.

The prototype still tracks a density-selected core. It is not the complete
tracer/upstream-buffer method in [Farber & Gronke, section 2.3](https://arxiv.org/pdf/2107.07991).
The full method and other native codes need separate work after this validation.
