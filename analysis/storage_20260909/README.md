# Storage evidence, not a raw-data deposit

The [project inventory](project_storage_inventory.json) records file counts and
logical sizes by research directory category at its stated time. It includes
native fields, code, logs, environments and derived views inside those roots.
It is metadata only—not a raw-only total or a backup. Personal recordings,
installer names and whole-machine cleanup inventories are not included.

The [compression probe](compression_probe.json) tested four retained Enzo
snapshots without changing them or the active solver. Gzip levels1 and6 were
stream-decompressed and compared byte-for-byte with the original input. All
checks passed. The [script](compression_probe_v1.py) reads native files, writes
only a small report, and is not an archiver or cleanup command.

| Snapshot | Original MB | Gzip level1 MB | Gzip level6 MB |
|---|---:|---:|---:|
| L5 initial | 206.48 | 3.77 | 2.71 |
| L5 early, about0.25t_cc | 206.48 | 66.62 | 64.62 |
| L4 sharp, terminal | 26.59 | 20.14 | 19.89 |
| L4 historical, terminal | 26.59 | 19.75 | 19.49 |

MB here means1,000,000bytes. Initial data compress exceptionally well; do not
extrapolate that ratio to a full turbulent evolution. Gzip archive files need
extraction before native readers/restart tools can use them. This test does not
certify a production archive/restart workflow or a simulation speedup. No
compression was applied to the active pair and no raw outputs were deleted.
