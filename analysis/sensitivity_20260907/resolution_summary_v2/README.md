# Velocity sensitivity: updated resolution summary

8 September 2026. **Share with the caveats below.** This summary covers 50 accepted full controls (25 velocity-law pairs) at chi=100 and Mach=2, containing 5,054 native analysis states.

It adds the newly completed Gadget-4 and repaired MFV level-4 pairs to the [previous immutable summary](../resolution_summary_v1/README.md). No simulation or old raw analysis was rerun to make this update.

## Peak paired dense-mass separation

Each value is `100 * max_t |M_dense,sharp(t) - M_dense,historical(t)| / M_dense(0)`. Dense selection is rho > initial cloud density/3, with one fixed measured initial dense-mass denominator within each resolution pair. Values are percentages of initial mass, not exact-solution errors, statistical significance, or a ranking of codes.

Source analyses use explicitly labeled linear interpolation of scalar curves onto 0:0.05:5 t_cc for the descriptive peak. All actual native frame times are retained; requested cadence does not make every native timestamp identical.

| Native code | L3 | L4 | L5 | Accepted controls |
| --- | ---: | ---: | ---: | ---: |
| Athena++ | [8.145%](../analysis/report.json) | [6.801%](../analysis/report.json) | Not tested | 4 |
| AthenaPK | [5.947%](../analysis/report.json) | [1.139%](../analysis/report.json) | Not tested | 4 |
| Athena 4.2 | [13.085%](../athw/report.json) | [7.591%](../athw/report.json) | [8.695%](../athw/report.json) | 6 |
| Enzo | [23.356%](../enzo/report.json) | [3.236%](../enzo/report.json) | Not tested | 4 |
| Enzo-E | [8.211%](../enzoe/report.json) | [6.348%](../enzoe/report.json) | Not tested | 4 |
| RAMSES | [7.471%](../ramses/report.json) | [4.179%](../ramses/report.json) | Not tested | 4 |
| FLASH 4.8 | [10.370%](../flash/report.json) | [6.165%](../flash/report.json) | Not tested | 4 |
| Flash-X | [10.133%](../flashx/report.json) | [6.543%](../flashx/report.json) | Not tested | 4 |
| Arepo | [2.811%](../arepo/report.json) | [2.699%](../arepo/report.json) | Not tested | 4 |
| GIZMO MFM | [3.979%](../gizmo/mfm_levels_report.json) | [0.955%](../gizmo/mfm_levels_report.json) | Not tested | 4 |
| Gadget-4 SPH | [6.954%](../gadget4/l3_report.json) | [4.232%](../gadget4/analysis_levels_v1/report.json) | Not tested | 4 |
| GIZMO MFV (repaired) | [6.438%](../gizmo/mfv_repaired_pair.json) | [2.072%](../gizmo/mfv_analysis_levels_v1/report.json) | Not tested | 4 |
| Gasoline | Validation-held | Validation-held | Not tested | 0 |

L3 = 64 x 32 x 32 (3.2 initial elements/R); L4 = 128 x 64 x 64 (6.4/R); L5 = 256 x 128 x 128 (12.8/R). Particle/moving-mesh levels describe initial sampling, not a fixed evolved spatial resolution. L6 would be 512 x 256 x 256, not 512 cubed, and is not tested in this sensitivity summary.

## What can and cannot be concluded

Gadget-4 peak separation is 6.954% at L3 and 4.232% at L4; repaired MFV is 6.438% and 2.072%. Their newly completed higher-resolution controls narrow the observed paired differences, but do not establish convergence or universal insignificance.

Athena 4.2 is 13.085%, 7.591%, then 8.695% at L3/L4/L5: even the available three-level sequence does not decline monotonically. This evidence does not justify automatically reusing or replacing every historical run, or extrapolating to different chi, Mach, numerical recipes or finer resolutions.

AthenaPK tests its actual historical constant-outer-momentum prescription, not a tanh velocity profile. Other accepted pairs compare historical tanh velocity to sharp velocity at 1.3R. Conditions are checked within each native-code pair; pressure, boundary and tracer prescriptions are not certified identical across codes.

A reuse decision needs a prospective scientific tolerance agreed with Ryan and provenance checks against the particular historical run. No post-hoc cutoff or code ranking is introduced. The blanket replacement queue stays inactive.

## Essential code-specific caveats

* The grid-code tests are coarse. Tracer losses in the finite boxes mean t=5 need not retain all cloud material. FLASH, Flash-X and Enzo-E have no native passive tracer in these recipes.
* Arepo retains its periodic streamwise boundary and initial pressure deviations up to about14.45% at L3 and13.75% at L4. Moving-mesh resolution evolves.
* Gadget-4 retains the existing smoothing-length seed repair and nonuniform SPH pressure: L3 peak3.9003 times nominal, L4 range0.80827 to2.10420. It is not a uniform-pressure grid baseline.
* GIZMO retains periodic boundaries and small kernel-pressure deviations. Repaired MFV uses its isolated timestep repair; original failed MFV cases are excluded, not relabeled. MFM trajectories are never substituted for MFV.
* Native evolved GIZMO velocities are staggered; simultaneous velocity diagnostics remain unvalidated. Particle-ID in-box mass is not a passive material-retention diagnostic, and periodic recirculation defeats a no-boundary-crossing claim.
* Native resource timings are not controlled speedup/convergence benchmarks. L3/L4 storage locations can differ. Restart byte/prefix checks do not certify checkpoint resume.

The [previous summary](../resolution_summary_v1/README.md) retains detailed source caveats for the original23 pairs. New [Gadget-4](../gadget4/analysis_levels_v1/README.md) and [MFV](../gizmo/mfv_analysis_levels_v1/README.md) reports provide their completed L3/L4 evidence. Full source caveats remain attached to each source/level in the machine-readable summary; historical one-level notes are not claims that the new L4 results are missing.

## Remaining work and decision for Ryan

Four Gasoline L3/L4 controls remain scientifically held: two velocity laws at each level. Its predeclared field-repeatability check failed in6/120 paired-time comparisons, including untouched-binary repeats, despite agreement in the density-selected mass diagnostic. The [force-order investigation](../gasoline/FORCE_ORDER_RESULTS.md) is completed evidence, not an unrun task. Do not silently loosen the criterion or rerun the same traces. A prospective acceptance decision and remaining same-executable sharp-IC validation are needed before full controls.

Higher-resolution pairs remain additional storage-held work. Full raw-retention budgets and separate host/guest safety reserves must fit before launching them. No native solver was launched by this summary. All old/new raw remains retained; reports, meshes and movies are not raw backups.

Cooling, other Mach numbers, MHD, Galilean tracking, all-material-retained Figure1 and new production3Dviewer entries are separate unvalidated scope.

## Reproducibility and review

[Summary JSON](summary.json) preserves25unique code/level pairs, source hashes/pointers, denominators, native-state counts and scope. [Validation](validation.json), [review](QA.md), [extension script](../extend_resolution_summary_v2.py) and [new tests](../test_resolution_summary_v2.py) document this report-only update.

The extension script uses only the Python standard library and reads accepted scalar reports, never native output. It refuses to overwrite resolution_summary_v2. The previous23 entries are preserved exactly; two newly validated L4 entries are appended, not substituted for missing data. Every source is hash-pinned. New tests cover coverage, scope, denominator, metric/count, law and time errors.

Native-state counts come from source records: Enzo102 per accepted case, all others101. This is not a count of auxiliary raw files. Assessment: share with caveats, not a completed all-resolution or cross-code-equivalence study.
