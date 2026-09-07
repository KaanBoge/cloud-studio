# First velocity sensitivity results

## Update: 8 September 2026

Eighteen full controls are now validated: the eight pilot runs below, six
native Athena 4.2 runs at L3/L4/L5, and four Enzo runs at L3/L4. Each Athena 4.2 run has 101 distinct native
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

Enzo-E is now the next native paired queue, after initial-field checks with
eight Charm++ worker threads. Its existing recipe has no passive tracer, so
tracer retention is unavailable and no all-material-retained claim is made.
See [Enzo-E scope](enzoe/README.md).

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
Athena 4.2 L3/L4/L5 is complete. Enzo-E is the next paired native-code queue.
The other eight solver variants
(including separate GIZMO MFM/MFV) still need paired launchers and native
historical-law checks. A 15-minute task follow-up is enabled to inspect progress and
advance safe pending work. The old blanket replacement queue remains inactive.
Cooling, tracking and paper-ready retention checks remain separate work.

These results have not been added to the public viewer or emailed. The analysis
package is separate from viewer run entries; publication is verified separately.
Use the sensitivity evidence and each code's resolution dependence to discuss
with Ryan which historical datasets can be reused, rather than assuming that
every earlier run must be replaced. See PLAN.md for the reproducible protocol.
