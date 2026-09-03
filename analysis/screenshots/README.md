# Directory layout

Terminal output from the actual run directories on the machine, one image per
code, showing the output files as they are written.

| image | code |
|-------|------|
| `tree.png` | top of the source tree and the Athena++ run list |
| `athenapp.png` | Athena++, level 4, chi=10 (`.athdf`, 101 snapshots, 2.4 GB) |
| `athenapk.png` | AthenaPK, level 5, chi=10 (`.phdf`) |
| `enzo.png` | Enzo, level 4, chi=10 (one `DD####` directory per snapshot) |
| `enzo_snapshot.png` | inside a single Enzo `DD0005`, which is itself a directory |
| `ramses.png` | RAMSES, level 4, chi=10 (`output_#####` directories) |
| `flashx.png` | Flash-X, level 5, chi=10 (HDF5 plotfiles) |
| `athena42.png` | Athena 4.2, level 4, chi=10 (per rank `.vtk` under `id0/`) |
| `gizmo.png` | GIZMO MFM, level 4, chi=10 (particle HDF5 under `output/`) |
