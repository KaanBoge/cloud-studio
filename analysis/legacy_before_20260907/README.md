# Analysis pipeline

Scripts that turn raw simulation snapshots into the movies, the interactive 3D
viewer at <https://kaanboge.github.io/cloud-studio>, and the figures.

Twelve codes write twelve different formats. Everything here reads them through
**yt**, which flattens AMR onto a uniform grid and deposits particle data onto a
grid, so every code becomes the same `rho[nx,ny,nz]` array. Nothing downstream
needs to know which code produced a file.

## Setup

Each run writes **101 snapshots**, evenly spaced from t = 0 to t = 5 t_cc, so
the output interval is 0.05 t_cc. Because t_cc = sqrt(chi) R / v_wind, the
interval in code units depends on the overdensity:

| chi | t_cc | tmax = 5 t_cc | output interval |
|------|---------|---------------|-----------------|
| 10 | 1.2247 | 6.1237 | 0.06124 |
| 100 | 3.8730 | 19.3648 | 0.19365 |
| 1000 | 12.2474 | 61.2370 | 0.61237 |

Common to all runs: gamma = 5/3, wind rho = 1, P = 1, vx = 2.581989 (Mach 2
exactly), cloud radius 1 with a tanh edge of width 0.1 R, velocity transition at
1.3 R, domain x in [-3,17] and y, z in [-5,5] cloud radii.

Resolution is quoted as a level: level N has 8 * 2^N cells along the wind, so
level 5 is 256x128x128 (12.8 cells per cloud radius) and level 6 is 512x256x256.

## Files

| file | what it does |
|------|--------------|
| `dense_export.py` | Marching cubes isosurfaces at 0.15 chi and 0.6 chi for every snapshot, written as quantised gzipped meshes. This is what the browser viewer streams. |
| `diagnostics.py` | Time series per run: surviving dense mass fraction, centre of mass, peak density, mixing fraction. Written as JSON. |
| `render_3d_movie.py` | Renders each snapshot with matplotlib and encodes with ffmpeg. |
| `figure1_isosurfaces.py` | Figure 1: 3D isosurfaces, rows chi = 10/100/1000, columns codes, one fixed time. |
| `figure2_mass_evolution.py` | Figure 2: dense mass against time, normalised to t = 0. |
| `check_initial_conditions.py` | Verifies the density edge and the velocity transition sit where the spec says, used when harmonising the codes. |
| `run_ladder.sh` | Run queue for the grid codes across the resolution ladder. |
| `run_lagrangian_level5.sh` | Serial queue for Arepo, GIZMO and Gasoline at level 5. |

## Usage

```bash
# isosurface meshes for the viewer
python dense_export.py <tag> <kind> <chi> <outdir> <snapshots...>

# diagnostic time series
python diagnostics.py <tag> <kind> <chi> <t_cc> <snapshots...>

# movie
python render_3d_movie.py <kind> <chi> <t_cc> <label> <name> <dir> <glob> 1

# figures
python figure1_isosurfaces.py out.png L5 apk,enzo,flashx,ramses 5.0
python figure2_mass_evolution.py out.png L3
```

`kind` is one of `apk athpp athw enzo flash flashx ramses part tipsy` and selects
the reader and any per code coordinate convention.

## Two coordinate conventions worth knowing

* **AthenaPK** blows the wind along x2, so its arrays are transposed before use.
* **RAMSES** is reported by yt in normalised [0,1] box units, so coordinates are
  scaled by `boxlen` before the campaign shift is applied. Getting this backwards
  puts the cloud in a corner of the box; it was a real bug here.

## Requirements

Python 3 with `yt`, `numpy`, `scipy`, `scikit-image`, `matplotlib`, `h5py`, and
`ffmpeg` on the path.
