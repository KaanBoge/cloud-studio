# First velocity sensitivity results

## Update: 8 September 2026

Forty full controls are now validated and analyzed: the eight pilot runs below, six
native Athena 4.2 runs at L3/L4/L5, four Enzo runs at L3/L4, and four Enzo-E runs
at L3/L4, plus four each for RAMSES, FLASH 4.8, Flash-X and Arepo at L3/L4,
and two GIZMO MFM controls at L3. Each Athena 4.2 run has 101 distinct native
snapshots through 5 t_cc. Its initial density, tracer, coordinates and volumes
match exactly within each pair at native VTK precision. Only velocity changes.

Athena 4.2 peak mass-curve separation is 13.09%, 7.59% and 8.70% of initial
dense mass at L3/L4/L5. The L5 trend does not demonstrate monotonic convergence
toward zero effect. At t=5, L5 retains about 97.4-97.5% of initial tracer mass;
these are not all-material-retained terminal images. See
[the Athena 4.2 results](athw/README.md) and [mass/retention plot](athw/mass_and_retention.png).

Enzo's four completed controls each have 102 actual native times, including an
extra terminal dump. Independent HDF5 sums agree with yt within 9.4e-16 scaled
mass difference for all 408 snapshots. Peak curve differences are 23.36% at L3
and 3.24% at L4; final tracer retention is about 85.9% and 92.7-93.2% respectively.
The L5 pair is storage-held: 69.8 GiB plus a 10 GiB safety reserve is needed,
against about 35.1 GiB free on the backing drive. See [Enzo results](enzo/README.md).

Enzo-E has also completed L3/L4 with 101 actual native times per case, using
eight Charm++ worker threads. Peak curve differences are 8.21% and 6.35% of
initial dense mass. Its L5 pair is storage-held. Its existing recipe has no passive tracer, so
tracer retention is unavailable and no all-material-retained claim is made.
See [Enzo-E scope](enzoe/README.md).

RAMSES L3/L4 is complete with 101 actual native times per case. Peak mass-curve
separation is 7.47% at L3 and 4.18% at L4; final tracer retention is about
84.1-84.3% and 92.1-92.2%. Its eight CPU workers were fully busy during L4,
which took about 2m48s per solver run. All 404 native outputs remain saved.
L5 is storage-held. See [RAMSES results and native-code checks](ramses/README.md).

FLASH 4.8 L3/L4 is now complete, with 101 distinct full-state times in each of
four controls. All 404 native mass sums agree independently with yt within
5.6e-16 relative difference. Peak mass-curve separation is 10.37% at L3 and
6.17% at L4. L4 solver runs took 8m04s and 7m59s on eight CPU ranks, peaking
at 13.49 GiB solver-child RSS. There is no native tracer, so retention is
unavailable. L5 is storage-held. See [FLASH results](flash/README.md).

Flash-X L3/L4 is complete too, with 101 actual times per control and all 404
checkpoint mass sums independently checked with yt (relative discrepancy
below 4.1e-16). Peak curve separation is 10.13% at L3 and 6.54% at L4.
L4 took 7m21s and 7m15s on eight busy CPU workers, with peak solver-child
RSS 11.47 GiB. Native raw is retained. L5 is storage-held and no tracer
retention is available. See [Flash-X results](flashx/README.md).

Arepo L3/L4 is complete with 101 actual native times per control. All 404
snapshot mass sums agree independently with yt within 6.2e-16 relative
difference. Peak dense-mass curve separation is 2.81% at L3 and 2.70% at L4.
L4 took 1h06m35s and 1h06m26s on eight CPU ranks, with peak solver-child RSS
3.66 GiB. The original jittered mesh produces initial pressure deviations up to
14.45% at L3 and 13.75% at L4, identical within each pair. Its periodic x
boundary allows tracer recirculation: an in-box tracer fraction of one is not
proof that no material crossed a boundary. All raw data is retained and L5 is
storage-held. See [Arepo results and limitations](arepo/README.md).

GIZMO MFM L3 is complete with 101 distinct native times per control and all
202 mass sums independently checked with yt. Peak mass-curve separation is
3.98% of the fixed initial dense mass. The two solver runs took 82.4 and 82.1
seconds on eight busy CPU workers, peaking at 0.489 GiB solver-child RSS.
This is a single coarse resolution, not a convergence result. Both MFV L3
controls also reached 101 outputs, but zero stored internal energy first
appears at t=3.95 t_cc in each. They are retained as failure evidence and
excluded from the 40 validated controls. No floor or output was changed.
See [GIZMO results and failure audit](gizmo/README.md).

The first Enzo full
attempt exposed an output-setting error: dtRestartDump is a wall-clock exit
trigger, not a physical-time snapshot interval. Its 21 saved outputs remain
intact. The v2 queue restores the native disabled setting and starts fresh
under different directory names. See [Enzo status and safeguards](enzo/README.md).

Analysis scripts, figures and diagnostic records are published on GitHub;
these experiments are not relabeled as production runs in the 3D viewer.

## Original two-code pilot

Completed 7 September 2026. **Share with caveats; not a blanket reuse or rerun decision.**

Eight genuine 3D runs are complete: Athena++ and AthenaPK, levels 3 and 4,
historical and corrected velocity prescriptions, fixed chi = 100 and Mach = 2.
Every run produced 101 distinct native output times from t=0 through 5 t_cc.
All native fields, restart files, logs, inputs and source/build evidence are retained.
The original two-code WSL pilot occupies about 11 GiB. No historical data was deleted.

## Findings

Maximum absolute separation of the mass curves on the stated common-time grid,
expressed as a percentage of the unchanged initial dense mass:

| Code | Level 3 | Level 4 | Historical change tested |
| --- | ---: | ---: | --- |
| Athena++ | 8.15% | 6.80% | Tanh velocity at 1.3 R versus sharp velocity |
| AthenaPK | 5.95% | 1.14% | Constant outer momentum versus constant outer velocity |

These are not relative errors against an exact solution, and the two codes did
not have the same historical mistake. At t=5, both L3 cases have zero mass above
the selected density threshold, despite differences earlier in their evolution.
Comparing only their final dense mass would miss the effect.

At L4, Athena++ historical/corrected dense mass fractions at t=5 are approximately
0.002554/0.021815; AthenaPK fractions are 0.021540/0.021815. Relative percentages
against a nearly zero final mass exaggerate that comparison, so the fixed initial
mass denominator is reported instead.

## Checks and limits

Within each pair, executable, numerical settings, domain, boundary recipe and
native sampling are unchanged; only `velocity_ic` differs in the input. Initial
density, tracer and cell coordinates agree exactly. Pressure agrees to recovery
roundoff, and the native velocity matches the selected law. All saved primitive
fields are finite with positive density and pressure. Seven unit tests passed.
Direct HDF5 mass sums are also checked independently with yt.

Dense selection is rho > rho_cloud_initial/3. The denominator is the measured
native initial dense mass, not a new denominator each timestep. Plot lines use
actual native output times. Reported curve differences use explicitly labeled
linear interpolation of scalar diagnostics onto 0:0.05:5 t_cc; no 3D snapshots
were synthesized or retimed.

L3 and L4 have only 3.2 and 6.4 cells per cloud radius. These coarse tests do not
establish convergence, all-code equivalence or high-resolution insignificance.
Only about 88.6-95.7% of the initial tracer mass remains in the box at t=5 across
these runs. The t=5 images are common-terminal-time diagnostic views, **not** a
certified all-material-retained Figure 1. Density selection and tracer mass are
different quantities. Tracer prescriptions and native wind axes differ between
the two codes, so the pairs are interpreted within code.

## Files

`analysis/mass_evolution.png`: resolution overlays of the measured dense mass.

`analysis/density_slices_t5.png`: 3D data visualized in 2D, averaging the two cell
planes nearest z=0, using the same coordinates and density/color normalization.

`analysis/report.json`: full 808-snapshot diagnostic series, hashes, metrics and
independent L3 checks. `analysis/crosscheck_l4.json` adds independent L4 checks.

`build.json`, `historical_sources.json`, `batch.json`: executables, commands,
historical-law provenance, run timings and validation evidence.

Native simulation output: `/home/kaan/sensitivity_20260907/runs`.
Windows scripts/results: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907`.

## Still pending

The Athena++/AthenaPK and Enzo level-5 continuations remain storage-held.
Athena 4.2 L3/L4/L5 and Enzo-E L3/L4 are complete. Enzo-E L5 is storage-held too.
RAMSES and FLASH 4.8 L3/L4 are complete; their L5 continuations are storage-held.
Flash-X and Arepo L3/L4 are complete and their L5 pairs are storage-held.
Arepo's original jittered lattice gives native pressure deviations up to 14.45%
in both controls, and its streamwise boundary is periodic. These limitations
are preserved and documented for the within-code experiment, not claimed as
a matched cross-code setup. See [Arepo results and caveats](arepo/README.md).
GIZMO MFM L3 is validated and analyzed; GIZMO MFV L3 completed the native
solver but failed positive-energy checks in both controls. All 404 native
outputs remain retained. The stopped L3 batch must not be relaunched.
A separate timestep-scaling test explains native t=0 velocity staggering;
those velocities must not be interpreted as simultaneous with the header time.
MFM L4 per-level native/timing tests now pass:16 actual test outputs and nine
additional unit tests. Its separate full pair launched at07:50 local on
8 September, sharp then historical, using eight CPU workers. This launch is
not yet included in the40 accepted/analyzed controls. Its whole-pair budget
is10.25GiB plus10GiB reserve on both filesystems. MFV requires diagnosis,
not silent floor changes or blanket retries.
See [GIZMO validation and remaining work](gizmo/README.md).
Gadget-4 and Gasoline remain unprepared.
A 15-minute task follow-up is enabled to inspect progress and
advance safe pending work. The old blanket replacement queue remains inactive.
Cooling, tracking and paper-ready retention checks remain separate work.

These results have not been added to the public viewer or emailed. The analysis
package is separate from viewer run entries; publication is verified separately.
Use the sensitivity evidence and each code's resolution dependence to discuss
with Ryan which historical datasets can be reused, rather than assuming that
every earlier run must be replaced. See PLAN.md for the reproducible protocol.
