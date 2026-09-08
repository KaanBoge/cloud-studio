# Arepo validation review

8 September 2026. **Share with caveats.** All four L3/L4 controls completed;
no full case, snapshot or distinct native time was excluded. No raw data was
deleted. This package answers within-Arepo velocity sensitivity at chi=100,
Mach=2, not whether all historical codes already form a matched comparison.

## Method and reproducibility

The actual sharp and archived tanh IC generators, identical pinned native
executable, input files, seed42 and original sampling are recorded in the
setup evidence. Every full case has 101 actual times from zero to 5 t_cc.
The analysis reads native Voronoi density, not a visualization reconstruction.
Dense mass is the sum of native mass where rho exceeds initial cloud density/3.
The measured initial dense mass is identical within each pair and remains the
denominator at every time. The plotted curves retain actual timestamps; only
the reported scalar peak separation interpolates onto 0:0.05:5 t_cc.

All 404 outputs were independently read with explicit yt ArepoHDF5Dataset,
rectangular bounds and float64 sums. Total, dense and tracer masses agree with
the direct HDF5 aggregation to at most 6.1688e-16 relative discrepancy. Native
file hashes are checked before and after independent reads. All eight native
fields remain saved; physical arrays are float64 and particle IDs uint32.
Inputs and native initial coordinates, masses, density and IDs agree exactly
within pairs. Internal energy/pressure recovery differs by less than 2e-15.

The report's batch SHA256 is
`bb32437197ad477d7ef61f9367cf8e233b75e4182bf3770bde80c6ceada33108`.
Its analysis script SHA256 is
`67a73f40d7644c6971265ebd521d8f329ea3fcb76153d834ac72e8d7f0752c6f`.
Windows and native reports match byte-for-byte. Eight launcher tests and two
analysis tests cover the original validation pipeline. No solver is rerun for
publication; staging checks completed scope, hashes, counts and mass errors.

## Findings and required caveats

Peak curve separations are 2.8113% (L3) and 2.6993% (L4) of initial dense mass.
These are not relative errors against an exact solution. The plot overlays
both resolutions and both laws, rather than selecting only the terminal mass.
Its axes, legends and constant-tracer panel were visually reviewed.

The original jittered lattice creates native initial density/pressure
perturbations up to 14.4508% at L3 and 13.7478% at L4. They are identical within
pairs but differ from a uniform-pressure grid baseline. Periodic x boundaries
are also retained. Tracer can leave and re-enter; a final in-box tracer fraction
of one does not certify no boundary crossing or an all-material-retained image.

L3/L4 mean 3.2/6.4 initial points per cloud radius, not a fixed later grid and
not a converged study. Higher-resolution sensitivity remains unknown. The L5
pair requires 124.02 GiB plus a 10 GiB reserve and additional runtime/restart
review. No cooling or frame tracking is enabled. Analysis assets are published
separately from production viewer entries and do not back up the raw fields.

## Publication checks

`stage_results.ps1` refuses inconsistent batch/report hashes, incomplete cases,
missing times or independent errors above 1e-11. It atomically replaces only
explicit analysis targets to avoid modifying older hardlinked copies in place.
Publication requires an advanced commit, matching remote main, successful
Pages workflow and live report/PNG verification. Local `publication.json`
records those external checks after success. A failed check is not called live.
