# Run staging

These tools turned the saved outputs of each complete run into the folder the site reads, one folder per
run on the `runs` branch. Each tool reads every saved state once, checks it against an independent
reduction of the same run, and writes the pictures, posters, films, 3D surfaces and catalog entries.

* `stage_grid.py`: Athena++, AthenaPK, Athena 4.2, Enzo and Enzo-E at level 5, the Athena++ periodic box
  controls at levels 3 to 5, and Athena++ at level 6.
* `stage_run2.py`: RAMSES, FLASH 4.8, Flash-X, Arepo, GIZMO MFM, GIZMO MFV and GADGET-4.
* `stage_older.py`: the runs at density contrasts 10 and 1000, the AthenaPK solver and cooling runs,
  and the GIZMO runs with the smooth velocity profile.
* `film_style.py`: draws both films of every run from the picture rows and the saved times, so all films
  share one style.
* `make_posters.py`: draws the two posters of every run from the last saved state. The staging tools first
  wrote posters of the state nearest 2.5 t<sub>cc</sub>; this script replaced them.

The folder paths at the top of each tool are those of my workstation, with the user name replaced by
`user`, and need adapting elsewhere. The tools need Python 3 with numpy, h5py, scipy, scikit-image and Pillow, and ffmpeg.
