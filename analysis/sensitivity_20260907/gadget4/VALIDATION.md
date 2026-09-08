# Gadget-4 native preparation validation

8 September 2026. **Share the completed L3 mass result with caveats.**

## Test plan and results

| Layer | Check | Result |
| --- | --- | --- |
| Provenance | Byte-identical existing hfix binary; native log/config/source evidence | Passed |
| Historical reconstruction | All arrays reproduce the saved historical L3 chi100 IC | Exact |
| Paired IC | Same nonvelocity arrays, IDs and lattice | Exact |
| Native initial state | Same nonvelocity fields; IC recovery at storage precision | Passed |
| Native evolved state | All four short-test outputs finite and positive; pressure recovery | Passed |
| Independent reader | yt sums total, dense and tagged mass for all four raw files | Zero reported discrepancy |
| Unit | Velocity law, parser/duplicates, numerical-setting guards | 7 passed |
| Unit | JSON report serialization, native IC error and pair checks | 4 passed |
| Unit | Full cadence/extra states/unchanged native numerics | 7 passed |
| Unit | Native early/late schedule and corrupted/missing-time rejection | 5 passed |
| Unit | Fixed denominator, interval completeness and unchanged time rows | 4 passed |
| Full runs | All 202 native states, exact native schedule, independent mass sums | Passed |
| Delivery analysis | Fresh raw hashes/direct mass sums and fixed normalization | Zero reported discrepancy |
| L4 | Own native initial/evolved and output-scheduler checks | Four native states passed; full pair storage-held |

The separate [level-4 report](L4_VALIDATION.md) gives its per-level spacing,
counts, original-pressure caveat, nine regression tests and whole-pair storage
budget. Evolved velocity synchronization remains unvalidated. These short
tests do not add any completed full science controls to the study total.

There is no blanket native-initial-pressure acceptance threshold hidden in
these checks: the measured pressure deviation is large (up to +290.03%),
identical within the pair and explicitly reported. This preparation does
not certify a matched uniform-pressure comparison with other solvers.

## Scientific limits

This is a two-law comparison at fixed chi100/Mach2 within the existing
Gadget-4 SPH recipe. Fully periodic boundaries, variable masses, the existing
smoothing-length seed patch and finite neighbor tolerance are preserved.
Both full controls and their 101 actual times each are now validated, in
addition to the short tests. Native sharp/historical times are identical.
Do not treat launch, exit zero or a target frame count alone as acceptance.
Native saved velocities at evolved times are not yet certified as simultaneous
with the header time; only mass diagnostics will be admitted by this runner.

yt receives explicit rectangular bounds and disables its own spatial
periodicity. These checks sum raw particle fields, without spatial interpolation,
kernel reconstruction or changing simulation boundary conditions. Native
files and hashes remain unchanged, including reader-created sidecar caches
being separate from the snapshots.

## Publication and retention

The original full runner's late-only output check was incorrect. A separate
source-derived audit reproduces every saved time exactly using the native
29-bit clock and nearest power-of-two block rounding. Five regression tests
protect this corrected rule. The original stopped ledger and runner remain
unchanged. Sharp was revalidated, not rerun; only the unstarted historical
case was then simulated. Both completed ledgers are retained.

The analysis re-read all 202 native hashes and mass sums, reproducing the
independent-check ledgers exactly. The fixed initial dense mass is
409.90798235; peak interpolated scalar-curve separation is 6.95382751% of
that mass at t=1.65 t_cc. Actual native times are used in the plotted curves.
The zero-based, labeled single-resolution plot was visually inspected.
This is not a resolution-convergence figure or an exact-solution error.

All original and failed attempts remain local. The JSON serialization fix
changed a report scalar type only and has a regression test. The frozen
full runner pins its own scripts, native build and completed validation hash.
No raw dataset is a deletion candidate merely because an analysis is public.

Require matching advanced remote commit, successful Pages deployment and live
SHA256 checks before claiming these scripts/evidence are published. A failed
publication can be corrected or reverted without touching native outputs.
