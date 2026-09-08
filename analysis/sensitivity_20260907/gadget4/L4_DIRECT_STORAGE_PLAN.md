# Gadget-4 L4 pair: direct Windows raw storage

8 September 2026. The next missing pair uses the already validated native
Gadget4_3d_mixed_hfix executable, eight MPI ranks, chi=100, Mach=2, and the
128 x 64 x 64 equal-volume initial lattice. This is within-code velocity
sensitivity, not a blanket replacement or a matched-pressure grid comparison.

## Storage change, not a physics change

New native data will be written directly under
`C:/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1`.
Its WSL path is the same path prefixed by `/mnt/c` rather than `C:`.
Both laws use that same filesystem. Completed WSL raw directories are untouched:
no move, deletion, compaction or change to historical access paths is needed.
Direct Windows I/O may be slower than ext4; no speedup is assumed.

The existing guest-based storage helper explicitly rejects mounted-drive output.
It is not edited or bypassed. This new launcher has a separately tested mapping:
findmnt must identify writable drvfs C: at /mnt/c, distinct from the guest
filesystem. Both Windows DriveInfo and mounted-filesystem free space are checked.
The current distro's VHDX must also be on C:. Both measurements fail closed.

The entire original L4 budget is retained: 7,840,595,890 bytes for both laws,
including 104 snapshots, three restart sets, IC, 256 MiB logs per law and 20%
margin. This payload is charged to its actual destination, C:, not to ext4.
A separate 1 GiB allowance covers the small guest runner/package and unexpected
guest-side ancillary growth. Preflight requires C: free >= full remaining pair
budget + 1 GiB guest allowance + 10 GiB reserve, and guest free >= 1 GiB allowance
+ 10 GiB reserve. Guest usage still consumes C: capacity; it is not free storage.
During execution both filesystems retain at least 10 GiB free. No VHDX shrink,
reusable ext4 blocks, compression, thinning or deletion is credited.

## Unchanged controls and preservation

The two previously validated L4 IC files are copied byte-for-byte, independently
hash-read in Windows, and checked against their existing validation record.
They are not regenerated. Native numerical parameters and restart interval
7200 seconds remain unchanged. Only relative IC/output paths and metadata-derived
full duration/cadence replace the historical template values, identically in both
controls. The native output scheduler is reused without modifying timestamps.
Each case has a 6000-second external runtime cap; no checkpoint is auto-resumed.

All snapshots, ICs, logs, resources and restart files stay in the new folder.
Runs and package directories must be absent before preparation. Completed/failed
runs cannot be restarted by this launcher. Eight ranks use the same Linux binary;
no native code rebuild, worker-count benchmark or GPU simulation is introduced.

Both existing benchmark and production locks are held throughout the pair.
Preflight requires 12 GiB available guest RAM; the live guard stops below 2 GiB.
Graceful native checkpoint/stop is requested first. Only the launcher's verified,
still-owned process group may receive a terminating signal after bounded grace.
Unrelated applications are not closed and RAM is not artificially filled.

## New tests and acceptance

Unit tests cover mounted-drive identity, read-only/foreign mounts, incomplete
measurements, host/guest reserve accounting, wrong destination, reused paths,
changed numerical parameters and changed pinned inputs. Existing native L4
smokes and old tests are not repeated. A tiny new file-I/O probe and both copied
IC hashes must agree when independently read from Windows before launch.

Every new full snapshot receives the existing L4 finite/positive field, native
schema/count/ID, initial-condition, exact-scheduler and independent yt mass checks.
Initial nonvelocity fields must match across the new pair. Source and IC hashes
must remain unchanged, and restart generations must match the retained budget.
Failed guards/checks stop advancement; they do not relax scientific tolerances.

The original periodic boundaries and SPH pressure range (about 0.808 to 2.104
at t=0, nominal P=1) remain explicit caveats. Evolved velocity-at-header-time
synchronization is not certified. The previous 46 accepted controls remain the
count until both new full controls and their paired checks pass. Gasoline stays
scientifically held; the old blanket replacement queue stays inactive.
