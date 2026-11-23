# Update notes

## 23 November 2026

Every page now shares one navigation (Library, 3D viewer, Compare, Research, Paper, GitHub), one footer and the Cloud Studio icon, and each page title names its page.

The research page explains the work in one place: the twelve methods and their boxes, how to read a library card, what the pictures and the 3D view show, the main results of the paper, how the data is made and what can be downloaded. The progress log and the verification log stay as dated logs of September 2026 and are linked from the research page.

In a desktop window the archive opens with 24 requests and about 1.2 MB instead of about 400 requests and 294 MB. Terrain views load when their tab opens, each 3D volume loads when its run is picked, films load when they are played, and the 3D tabs use the copy of three.js in `vendor/`.

Some sentences in the analysis reports and code comments were reworded, and local user names, the machine name and the folder name of the early runs were replaced by neutral names (`user`, `workstation`, `wind_tunnel`). Checksums recorded inside the dated September 2026 records refer to the files as they were built and run; the analysis file list carries the current checksums of every analysis file.

## 9 September 2026

### Ongoing project and software licence

The public overview presents Cloud Studio as my ongoing project and describes the published collection. The original website and viewer, selected standalone utilities and the project guides are MIT licensed with an explicit scope; native code derivatives and research data keep their own terms. The bundled three.js licence is included with its original authorship.

### Easier to inspect

The repository gained an expanded README, a guide to the native codes and methods, resolution definitions, workflow and data retention guidance, contribution notes and citation metadata. A research page links the viewer and the library to the scientific evidence.

The searchable data catalogs list the public analysis files with SHA-256 checksums, and the earlier streamed meshes with their counts and times from the pinned frames branch. The research bundle packages custom scripts, reports, plots and provenance, without raw fluid states or licensed solver distributions.

### New evidence

Custom analysis and checking helpers and publication records joined the repository, together with the storage plan for the level 5 Enzo pair, its diagnostic pair, the independent checks of its sharp run and read only storage and compression measurements.
The all code summary covers 50 controls, 25 pairs and 5,054 native states; the level 5 Enzo checks are separate from it. [The dated Enzo observation](../analysis/publication_20260909/enzo_l5_observation.json) records what was observed during packaging.
