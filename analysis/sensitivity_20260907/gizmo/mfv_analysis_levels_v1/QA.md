# MFV L3/L4 analysis review

8 September 2026. **Assessment: share with the documented caveats.**

## Methodology and calculation checks

The question is within-code velocity-law sensitivity at fixed chi=100 and
Mach=2, over two initial resolutions. The original failed MFV attempts are
explicitly excluded, not silently relabeled as repaired runs. The accepted
L3 report is reused by exact hash; all new L4 saved states are included.

The 404 native states have finite, strictly increasing times from zero to
5 t_cc. Both cases at each level share a fixed measured initial dense-mass
denominator. The new stage verifies native clock evidence rather than
assuming a requested time equals a saved time. The 101-point scalar grid
is used only for a labeled descriptive peak, not new 3D snapshots.

All 202 new HDF5 hashes, 16 restart hashes and 39 frozen source/input pins
match. Independent native/yt field checks are reused from the completed
full-run validator; no costly repeat extraction is needed. Case records
match the batch, initial-condition/parameter hashes and launch records.
CPU/RAM summaries reproduce from the saved resource samples.

Fourteen new tests cover changed denominators, missing/duplicated times,
nonfinite scalars, extrapolation, incorrect laws/binaries/parameters,
wrong cadence/resolution, failed energy/reader/conservation evidence, and
known scalar examples. Independent scalar interpolation differs by at
most 2.220446049250313e-16. Existing L3 curves/peaks reproduce exactly.
L4 peak=0.0207205310514873 of initial dense mass at 1.35 t_cc; final
sharp/historical fractions=0.4093015183103702/0.40370218570067085.

## Visual review

The rendered PNG was inspected. All four native-time curves are shown,
with levels distinguished by color and marker and laws by line style.
Axes and units are readable, the legend does not cover data, the upper
panel does not clip the small density-selected mass increase above one,
and both panels start at zero. The lower panel labels percent of initial
dense mass, not relative error. The report includes a numeric table and
complete scalar series as an alternative to reading the chart.

## Limits that must accompany sharing

Two coarse levels do not establish convergence or a universal historical
reuse threshold. Density-selected mass is not material retention. The
periodic box and small original pressure deviations are retained, not
silently harmonized across codes. Native velocity staggering, the
engineering-only conservation allowance and unverified checkpoint-resume
tail remain explicit. No new cooling, tracking or production viewer
completion is implied. The report is unsuitable for code accuracy ranking.

## Publication checks

Publish only custom scripts, scalar reports, plots and provenance, using
the existing GitHub analysis path. No raw/binary/upstream-source upload
or production viewer entry. Require new exact local/remote commit,
successful exact-commit Pages deployment, valid relative links and exact
live byte hashes. A missing or mismatched live artifact blocks the
publication claim. Keep previous immutable reports/proofs untouched.
If the new links fail, investigate and publish a corrective commit;
do not delete native data or rewrite prior history.
