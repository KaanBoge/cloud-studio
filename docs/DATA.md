# Data guide

## What can I download?

* [The paper](../paper/Cloud_survival_OJA.pdf) and [its source for Overleaf](../paper/Cloud_survival_OJA_Overleaf.zip): the LaTeX project with its figures and the reduced data behind the plots.
* [Library catalog](../data/studio-catalog.json): every entry of the library with its code, contrast, level and media.
* [Projections catalog](../assets/recent/catalog.json): the column density projections with their dense mass histories.
* [Analysis bundle](../downloads/research-evidence-2026-09-09-current.zip): scripts, Markdown reports, JSON diagnostics, figures and these guides from the September 2026 velocity setup study. [LICENSING.md](../LICENSING.md) separates the MIT software from the research material and the third party files.
* [Analysis file list](../data/research-files.csv), also as [JSON](../data/research-files.json): paths, byte counts and SHA-256 checksums of the analysis files.
* [Frame list of the earlier 3D runs](../data/streaming-inventory.csv), also as [JSON](../data/streaming-inventory.json): every index on the frames branch with its frame count, times and mesh size.
* [Storage inventory](../analysis/storage_20260909/project_storage_inventory.json): dated counts and sizes of the research folders on my workstation.

## Three kinds of data

| Data | What it contains | What it is for |
|---|---|---|
| Native simulation output | 3D fields or particles with their times, plus restart files | Every quantitative analysis |
| Diagnostics and figures | Mass histories, selected statistics, slices and their provenance | The recorded analysis and the paper |
| Pictures, films and 3D surfaces | Column density pictures, rendered films and surface meshes of every saved state | Looking at the runs on the site |

The native formats differ between the codes: HDF5 and ATHDF, VTK, RAMSES binary records, particle HDF5 and Gasoline TIPSY. Each code is read with its own format or a checked reader.

## Why native outputs are large

A level 5 grid has 4,194,304 cells. Six float64 volume fields alone take 201,326,592 bytes per snapshot, so 101 snapshots take about 20.3 GB per run, before boundaries and metadata. Level 6 has eight times as many cells.

Read only gzip tests reduced an early level 5 snapshot from about 206.5 MB to 64.6 MB and two late level 4 snapshots from 26.6 MB to 19.5 MB and 19.9 MB. Every test restored the source bytes exactly. Evolved data compresses less than the starting state, and a whole file gzip has to be unpacked before the native tools can read the file. See [the measured report](../analysis/storage_20260909/compression_probe.json) and [the read only test script](../analysis/storage_20260909/compression_probe_v1.py).

## Hosting

[GitHub Pages limits a published site to 1 GB](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) and [GitHub blocks regular files over 100 MiB](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). The site therefore carries pictures, films and surfaces made from the runs, while the raw snapshots stay offline on my own drives. The files of the complete runs live on the `runs` branch, one folder per run, the earlier 3D frames on the `frames` branch and the 60 fps film previews on the `media-60fps` branch.

## Time

The runs save a state every 0.05 t<sub>cc</sub> up to 5 t<sub>cc</sub>. The times on the site come from the native files and can differ slightly from the requested schedule; every frame prints its measured time. Runs in the archive have their own cadence and length.
