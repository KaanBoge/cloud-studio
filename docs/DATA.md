# Data guide

## What can I download?

* [Research evidence bundle](../downloads/research-evidence-2026-09-09-current.zip): public custom analysis scripts, Markdown reports, JSON diagnostics/provenance, figures and these guides. Native code source directories, the legacy archive, binary executables and raw simulation arrays are excluded. It is not a portable prebuilt solver installation. The included [license scope](../LICENSING.md) distinguishes MIT software from research artifacts and third-party material.
* [Analysis file inventory](../data/research-files.csv), also [JSON](../data/research-files.json): repository-relative paths, byte counts and SHA-256 hashes for the public analysis tree. A catalog entry is not a scientific acceptance certificate.
* [Historical streaming inventory](../data/streaming-inventory.csv), also [JSON](../data/streaming-inventory.json): every index in a pinned snapshot of the existing public frames branch, actual index counts/times, referenced mesh bytes and any integrity warnings. Listed/unlisted viewer entries are distinguished. Binary mesh payloads were not decoded by this metadata check.
* [Local project storage inventory](../analysis/storage_20260909/project_storage_inventory.json): dated counts and sizes by research directory category. It includes raw outputs, source, logs, environments and visuals inside those categories; it is not a raw-only total, an atomic snapshot, or proof of upload.

## Three different kinds of data

| Data | What it contains | What it can establish |
|---|---|---|
| Native simulation output | 3D fields, geometry or particles, times; separate restart formats | New quantitative analyses, subject to retained fields and code-specific validation |
| Derived diagnostics and figures | Mass curves, selected statistics, slices and provenance | The specific recorded analysis—not unrecorded fields |
| Browser meshes and MP4s | Selected surfaces, rendered pixels or quantized geometry | Visualization—not full fluid state or certified restart recovery |

Native formats vary: HDF5/ATHDF, VTK, RAMSES binary records, particle HDF5 and Gasoline TIPSY. Each code is read using its native format or a validated reader. The native-data and restart caveats remain in its own report.

## Why native outputs are large

The current level-5 Enzo grid contains 4,194,304 cells. Its six float64 volume fields alone require 201,326,592 bytes per snapshot, before boundaries and metadata. Saving 101 times requires about20.3GB per run. Native Enzo can also write a terminal output, and all actual outputs are retained. Level6 has eight times as many cells.

The current Enzo pair's approximately75GB allowance is a conservative raw-retention budget for two runs, not a movie size or the number of bytes already written.

Read-only gzip tests measured about206.5→64.6MB for an early L5 snapshot and26.6→19.5–19.9MB for two late L4 snapshots. Every test restored the source bytes exactly. Initial snapshots compress much more strongly than evolved data; these four snapshots do not predict a universal reduction. Compression is tested, **not applied to the active pair**. Whole-file gzip needs extraction before native tools can open the files. See [the measured report](../analysis/storage_20260909/compression_probe.json) and [read-only test script](../analysis/storage_20260909/compression_probe_v1.py).

## Hosting and retention

[GitHub Pages limits published sites to1GB](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). [GitHub blocks individual regular Git files over100MiB](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) and is not a raw-data backup service. The existing frames branch is a derived visualization store, not a way to claim that terabytes of native state are backed up.

No Zenodo deposit or external raw archive is verified. The published movies, size inventories and figures are derived results, not complete native-data backups. Native outputs retained locally contain fields that are absent from these visualizations.

## Time and completion

The current sensitivity controls request output spacing0.05t_cc through5t_cc. Actual times come from native files and can differ from the requested schedule. Extra native terminal times are preserved. Historical viewer entries vary in cadence and completeness. Frame count alone does not prove completed physics, correct initial conditions, radiative cooling or complete material retention.
