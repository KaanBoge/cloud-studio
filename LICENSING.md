# Licensing Cloud Studio

Cloud Studio's original website and viewer software is **MIT licensed**, with
copyright attributed to **Kaan Boge**. This document identifies the files covered
by the [root MIT License](LICENSE); it does not alter that license's terms.

## Covered by Kaan Boge's MIT grant

* Original application code in `index.html`, `viewer.html`, `research.html`,
  `research.js` and `research.css`.
* Original project guides: `README.md`, `CONTRIBUTING.md`, `CITATION.cff`,
  `LICENSING.md`, `THIRD_PARTY_NOTICES.md` and `docs/*.md`.
* These standalone project authored utilities:
  `analysis/publication_20260909/build_research_index.py`,
  `analysis/publication_20260909/validate_publication.py` and
  `analysis/storage_20260909/compression_probe_v1.py`.

Embedded or quoted third party material retains its existing notices and terms.
Importing an external dependency does not transfer ownership of that dependency.
Scientific citations remain citations, not claims of authorship by Kaan Boge.

## Separate terms; not blanket relicensed

* `vendor/`: three.js and OrbitControls are third party software under the
  three.js authors' MIT License, reproduced in [vendor/LICENSE.threejs](vendor/LICENSE.threejs).
* `code/` and all `analysis/` contents except the three utilities listed above:
  native code excerpts, adaptations, input files, archived scripts, reports and
  scientific evidence. Existing file level licenses, copyright notices and
  upstream access terms are preserved; absence of a notice is not an MIT grant.
* `data/`, `assets/`, `verification.html` and the separate `frames` branch:
  research results, visualizations, reports, inventories and derived geometry.
  This software license update does not assign a new data/media license.
* `downloads/`: bundles contain mixed material. Apply the terms of each included
  file, not one assumed license for an entire ZIP.

Native simulation packages are developed by their respective upstream teams.
Running them for this project, adapting a problem initializer or publishing a
visualization does not make those packages original Cloud Studio software.
The [third party notices](THIRD_PARTY_NOTICES.md) identify the relevant boundaries.

## What MIT means here

MIT allows reuse, modification and redistribution, including commercial use,
provided its copyright and permission notice is retained. It does not require
derivatives to be open source. It provides no warranty, does not validate the
scientific results and does not imply affiliation with or endorsement by the
Massachusetts Institute of Technology. See the [official license text](https://opensource.org/license/mit).

The dated scientific reports and their source hashes remain unchanged by this
licensing update. Public access alone does not certify redistribution rights
for every historical file.
