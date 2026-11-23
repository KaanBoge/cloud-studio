# Cloud Studio

### One cloud, twelve methods

**Cloud Studio is the public home of my cloud crushing research.** I simulate a dense gas cloud struck by a supersonic wind and run the same problem with twelve hydrodynamic methods. The site shows every run as pictures, films and rotatable 3D surfaces, next to the paper that compares them. Kaan Boge, ongoing.

**[Open Cloud Studio](https://kaanboge.github.io/cloud-studio/)** · **[Read the paper](paper/Cloud_survival_OJA.pdf)** · **[Paper source for Overleaf](paper/Cloud_survival_OJA_Overleaf.zip)** · **[How the work is done](https://kaanboge.github.io/cloud-studio/research.html)**

## The site

| Page | What it holds |
|---|---|
| [Library](https://kaanboge.github.io/cloud-studio/) | Every run as a card, with search and filters for code, contrast and level, films to play and pictures to download |
| [3D viewer](https://kaanboge.github.io/cloud-studio/viewer.html) | Two density surfaces for every saved state: turn the cloud, play it through time, set two runs side by side, save pictures and recordings |
| [Compare](https://kaanboge.github.io/cloud-studio/recent.html) | Edge on and face on column density pictures on one colour scale, two runs at the same moment, saved pictures and films |
| [Research](https://kaanboge.github.io/cloud-studio/research.html) | What I ran, how to read a card, what the pictures and the 3D view show, the main results, the data and the downloads |
| [Archive](https://kaanboge.github.io/cloud-studio/archive.html) | Earlier runs: two dimensional runs, films, image sets, terrain views and the first 3D volumes |
| [Progress log](https://kaanboge.github.io/cloud-studio/progress.html) and [verification log](https://kaanboge.github.io/cloud-studio/verification.html) | Earlier work up to September 2026 |

Every frame of a film, picture or capture prints its time, written t = 1.25 t<sub>cc</sub>, where t<sub>cc</sub> is the cloud crushing time. In the library and on the Compare page the default version of every film plays at 60 frames per second and cross fades between saved states; the original versions and the films of the archive page keep the rate they were made at.

## What I ran

Every run of the comparison starts from the same cloud: 100 times denser than the wind (χ 100), with a smooth edge, in a Mach 2 wind, inside a box of 20 × 10 × 10 cloud radii. Each method runs at levels 3, 4 and 5 and saves 101 states up to 5 t<sub>cc</sub>. Further runs at χ 10 and 1000, one at level 6 and runs with radiative cooling show how the result depends on the cloud and the physics.

| Method | Codes | Box faces |
|---|---|---|
| Eight grid codes | Athena++, AthenaPK, Athena 4.2, Enzo, Enzo-E, RAMSES, FLASH 4.8, Flash-X | Wind flows in and out |
| Moving mesh | Arepo | Periodic along the wind |
| Particle methods | GIZMO MFM, GIZMO MFV, GADGET-4 | Periodic on all faces |

A boundary control repeats Athena++ in the two periodic boxes at levels 3, 4 and 5.

| Level | Cells | Cells per cloud radius |
|---|---|---:|
| 3 | 64 × 32 × 32 | 3.2 |
| 4 | 128 × 64 × 64 | 6.4 |
| 5 | 256 × 128 × 128 | 12.8 |
| 6 | 512 × 256 × 256 | 25.6 |

## Main results

* For the first 3 t<sub>cc</sub> the methods stay close: at level 5, eleven of the twelve keep between 67 and 79 percent of the dense gas.
* By 5 t<sub>cc</sub> they separate. The eight grid codes keep between 10 and 28 percent, GIZMO MFV 37 percent, Arepo 54 percent, GADGET-4 76 percent and GIZMO MFM 98 percent.
* Running Athena++ in the periodic boxes of the other methods changes nothing for the first 2 t<sub>cc</sub> and raises its final dense fraction from 0.10 to 0.27 (periodic along the wind) and 0.33 (periodic on all faces).
* AthenaPK and Athena++ use the same scheme and give the same history.

Dense gas is gas denser than one third of the starting cloud density, counted as a fraction of its starting mass. The [paper](paper/Cloud_survival_OJA.pdf) has the full comparison.

## What is in this repository

```text
index.html, studio.js, studio.css      Library
viewer.html                             3D viewer
recent.html, recent.js, recent.css      Compare page
research.html, research.js              Research page
archive.html                            Archive of earlier runs
progress.html, verification.html        Earlier logs
assets/                                 Pictures, films, posters and 3D frames shown on the site
data/                                   Catalogs the pages read, and downloadable file lists
paper/                                  The paper, its LaTeX source, figures and reduced data
code/                                   Problem sources, input files and run logs of the simulation codes
analysis/                               Analysis, rendering and publishing scripts with their reports
docs/                                   Methods, data guide and update notes
downloads/                              Analysis bundle of the September 2026 velocity setup study
vendor/                                 three.js, served from the site itself
```

The site publishes derived pictures, films and 3D surfaces of every saved state. The raw simulation snapshots are kept offline because of their size. The files of the complete runs live on the [`runs` branch](https://github.com/KaanBoge/cloud-studio/tree/runs), one folder per run, the earlier 3D frames on the [`frames` branch](https://github.com/KaanBoge/cloud-studio/tree/frames) and the 60 fps film previews on the `media-60fps` branch, so the Pages site stays small. The [data guide](docs/DATA.md) and the [methods guide](docs/METHODS.md) describe the files and the steps from a simulation to the site.

## Licence and citation

The website and viewer software are released under the **[MIT License](LICENSE)**, copyright 2026 Kaan Boge. [LICENSING.md](LICENSING.md) lists the files the licence covers; the simulation codes, their adapted sources and the research data keep their own terms, and the bundled three.js keeps its authors' MIT notice. See the [third party notices](THIRD_PARTY_NOTICES.md).

To cite this work, cite the paper and the commit you used; [CITATION.cff](CITATION.cff) holds the project metadata. Ideas and corrections are welcome as issues or pull requests, see [CONTRIBUTING.md](CONTRIBUTING.md).
