# Gadget-4 level-4 validation and storage hold

8 September 2026, checked at approximately 09:39 Istanbul time.
**The level-4 short validation passed; no full level-4 control has started.**
The accepted study total remains 44. These tests are not 101-frame science runs.

## Native checks

Two isolated native Gadget-4 tests used a 128 x 64 x 64 equal-volume lattice
(524288 particles, 6.4 elements per cloud radius), chi=100 and Mach=2.
The sharp and archived historical velocity laws used the same existing
`Gadget4_3d_mixed_hfix` binary, all original per-level numerical settings,
and fully periodic 20 x 10 x 10 boundaries. No native solver source was rebuilt.
MaxMemSize remains 2000 MB per MPI rank, CourantFac=0.15, DesNumNgb=64,
MaxNumNgbDeviation=2, MaxSizeTimestep=0.05 and restart interval=7200 seconds.

Each test produced two actual native snapshots at code times 0 and 0.1.
Sharp took 5.491 seconds and historical 5.240 seconds on eight MPI workers,
peaking at 1.220 and 1.150 GiB summed solver-child RSS respectively. These
short solver times exclude validation and are not forecasts for full runs.

All four outputs have finite fields, positive native density, mass, pressure,
internal energy and smoothing length. Direct and independent yt sums of total,
dense and ID-tagged mass agree with zero reported discrepancy in every file.
Actual headers exactly match the native scheduler reconstruction. The
101-time full-run schedule is predicted separately, not claimed to be computed.

Initial coordinates, masses, internal energies and all native nonvelocity
fields match exactly within the pair. Native initial velocities match their
respective IC values at float32 precision; internal-energy recovery differs
by at most 1.19e-7 within the recorded storage-roundoff bound. Every array of
the archived-law IC exactly reproduces the old saved level-4 historical IC.
The level-4 checker explicitly uses dx=0.15625 and 524288 particles; it does
not reuse level-3 spacing, counts or native validation as evidence.

The original native SPH pressure variation remains significant and identical
in both laws: initial P ranges from 0.80827 to 2.10420, versus nominal P=1.
This is not a uniform-pressure grid-code baseline. No mass, energy or kernel
setting was changed to hide it. Periodic ID-tagged mass cannot prove that no
material crossed a boundary, and evolved velocity synchronization is not yet
certified. yt performs raw-field mass sums only, without kernel reconstruction.

## Measured full-pair storage requirement

| Item | Bytes |
| --- | ---: |
| Native snapshot | 25179656 |
| Eight-rank restart set | 114013430 |
| Native IC | 37754984 |
| Budget per full control | 3920297945 |
| Budget for both full controls | 7840595890 |

Each control reserves 104 snapshots, three measured restart sets, its IC and
256 MiB for logs, then adds 20% margin. The pair requires **7.30 GiB plus a
separate 10 GiB reserve on both filesystems**. The measured WSL free space was
16.66 GiB and Windows backing-drive free space was 35.72 GiB. The WSL check
therefore failed by about 0.64 GiB. This is a storage hold, not a solver or
RAM failure. A full runner is not enabled by this validation package.

A read-only duplicate audit found 1693 rendered PNGs with pre-existing,
byte-identical Windows copies, totaling 261603328 allocated bytes (0.244 GiB).
Even reclaiming all of those would not close the measured storage gap, so
nothing was deleted. Native raw, ICs, restarts, logs and earlier failed
attempts remain intact. A movie, mesh or diagnostic JSON is not a raw backup.
Refresh both filesystem capacities before any future full launch.

## Reproducibility and tests

[l4_validation.json](l4_validation.json) records every native output hash,
independent check, timing, initial-field measurement and storage decision.
[l4_validation_bundle.json](l4_validation_bundle.json) pins the scripts and
unchanged native-source/build evidence. Nine level-4 regression tests and
five native-scheduler tests pass, executed from the frozen package itself.

Native evidence: `/home/kaan/sensitivity_20260907/gadget4/validation_l4_v1`.
Frozen validation runner: `runner_validation_l4_v2` beneath that Gadget-4 root.
Do not relaunch either short test or overwrite an existing report.

The first package-freeze attempt referenced a nonexistent root-level scheduler
helper. It failed before any native simulation began. Its partial
`runner_validation_l4_v1` and original freeze script are retained. Version 2
copies the exact source-validated scheduler from the immutable L3 bundle into
its own package and tests that frozen copy. No native numerical setting or
data value was changed to fix this packaging error.

This publication adds validation, scripts and evidence only. It does not add
full controls, production 3D viewer entries or native raw backups. A failed
publication can be corrected or reverted independently of all native data.
