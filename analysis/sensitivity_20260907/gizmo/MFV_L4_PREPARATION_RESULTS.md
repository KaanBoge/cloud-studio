# Repaired MFV L4: validation passed, full pair launched

8 September 2026. Six new native L4 diagnostics passed, producing16 actual
states and retaining48 terminal restart files. These are short validation
experiments, not additional accepted full controls. The accepted study total
remains48; six L3/L4 controls remain, two of which are now in the active MFV
full-pair queue. Higher levels and Gasoline's scientific hold remain separate.

The full sharp control launched at15:50UTC with eight bound MPI workers.
The historical full control follows automatically only after the first
passes all native checks. Live workers were observed at97.5-99.2%CPU each
about20seconds after launch, with about1.67GiB summed child RSS. This is a
dated observation, not proof of current activity. No GPU solver is involved.

## New validation evidence

L4=128x64x64=524288 initial equal-volume elements, chi100/Mach2. The existing
isolated repaired executable is unchanged, as are original per-level floors,
neighbor tolerances, periodic box and numerical settings. The L4 IC arrays
were copied from the existing matching MFM inputs after checking them against
the archived MFV IC and the two intended velocity laws; MFM output trajectories
were NOT used as MFV simulations. The actual executable running these cases
is GIZMO MFV with the existing one-assignment timestep repair.

The historical L4 IC reproduces all archived MFV arrays exactly. Paired IC
nonvelocity fields and corresponding native initial fields are exact.
All16 snapshots passed finite/positive native field, complete ID/schema,
actual-time and independent yt mass-sum checks. Native initial pressure is
0.99907852..0.99913334 times nominal in every diagnostic; this kernel
deviation is reported, not removed. The fully periodic boundary recipe is
retained, so this is not universal cross-code initial/boundary equivalence.

| Diagnostic, for each law | Native states per law | Sharp / historical solver time |
|---|---:|---:|
| Original-timestep smoke to code time0.1 | 2 | 12.54 / 12.27 seconds |
| Timing cap1e-5 to code time0.00004 | 3 | 8.11 / 8.12 seconds |
| Timing cap5e-6 to code time0.00004 | 3 | 11.72 / 11.85 seconds |

All actual terminal states are retained, including the extra timing outputs.
Peak solver-child RSS was1.633..1.635GiB and median busy CPU workers7.95..7.99.
These short timings are not a full-run or level6 forecast.

For sharp/historical laws, halving the diagnostic timestep gives velocity-offset
ratios0.50001960/0.49964167. Both zero-step recovery residuals are2.38419e-7,
below the unchanged1.23119e-6 float32-scale bound. Native velocities remain
half-kick staggered; no snapshot field or timestamp was extrapolated or replaced.

All48 restart prefixes pass the exact executable ABI, complete IDs, native
60-bit endpoint clock, recipe and positive-field checks. Independent struct
sums reproduce conserved mass. The largest absolute MassTrue+pending dMass
residual is1.3303e-14 code mass, below the existing step-dependent engineering
allowances. The gate is not a physical-accuracy or arbitrary-flux theorem.
The unparsed restart tail has not been certified for checkpoint recovery.

Twenty-three new preparation tests and seven new full-run tests pass.
L4 readers reject the hardcoded L3 count and handle native rank prefixes
larger than65536 without modifying the old decoder. Negative tests cover
wrong clock width, schema/dtypes, fields, law, invalid mass accounting,
storage mapping/budgets, stale ownership, existing directories, unequal
full parameters and tiny timing caps accidentally entering a full run.
No completed L3 experiment or repair build was repeated.

## Storage and full-run boundaries

Short tests wrote new raw directly to C: using a separately reviewed
mapping and independent Windows readback. No old data was moved or deleted.
After preparation, measured full-pair budget is12.92883GiB, including104
snapshots, three measured eight-rank restart sets, IC/log allocation and
25% margin per law. The guest and Windows drive retain separate10GiB
reserves plus the charged1GiB guest ancillary allowance. Launch preflight
rechecked capacity after staging the full inputs. No capacity from the
guest was counted as additional host storage.

The full runner restores the unchanged MaxSizeTimestep0.05 and metadata-derived
5t_cc duration/0.05t_cc cadence; both full parameter files are identical.
It checks every native full-state output and late thermal positivity,
actual60-bit cadence, initial field identity and terminal conserved mass.
Exit0 alone does not accept a control. It preserves all raw data and stops
for review on a guard/check failure; there is no blind auto-resume.

Full raw directory:
`C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_velocity_pair_v1`.
Short raw directory:
`C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_preparation_v1`.
Each native directory retains its IC, parameters, log, resource samples,
actual HDF5 snapshots, restart files and validation evidence.

Preparation plan SHA256:
`579f85c2ca74cf7e44a8529b77d3d8f80e45e6760ccc18fa9aad9bae7c15e096`.
Preparation result SHA256:
`77768badc2721247f471c251ef7e316d02060eabf3e76c549dadcbd367e842c2`.
Full plan SHA256:
`2b77bb64257e2826dfe241ca6fb31eedcd5b868d73eeb4761cf96ac079430d7c`.

## Reproducible custom artifacts

[Preparation protocol](MFV_L4_PREPARATION_PLAN.md), [runner](mfv_l4_prepare.py),
[level-aware native checks](mfv_l4_native_checks.py), [tests](test_mfv_l4_prepare.py),
[Windows short launcher](launch_mfv_l4_prepare.ps1),
[full protocol](MFV_L4_FULL_PLAN.md), [full runner](mfv_l4_full.py),
[full tests](test_mfv_l4_full.py), [Windows full launcher](launch_mfv_l4_full.ps1),
[frozen preparation plan](l4_validation_v1/prepare_plan.json),
[all16-state evidence](l4_validation_v1/validation.json),
[preparation test result](l4_validation_v1/prepare_tests.json),
[frozen full plan](l4_validation_v1/full_plan.json),
[full test result](l4_validation_v1/full_tests.json).

This is validated preparation and a launched pair, not two completed full
controls, a convergence result, a universal historical reuse decision or new
production3Dviewer entries. Cooling, Galilean tracking and all-material-retained
figures remain unvalidated separate work. The blanket replacement queue is inactive.
