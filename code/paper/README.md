# Data and code of the paper

Series, scripts and custom source code behind [Cloud survival in supersonic winds](../../paper/Cloud_survival_OJA.pdf).

* `plot_series.json`: dense fraction histories of the twelve methods at n = 32, 64 and 128 (times in cloud crushing times). `plot_revision.py` draws Figure 3 and the diagnostic figures from it and from `diagnostic_series.json`.
* `boundary_control_series.json`: the Athena++ boundary control (inflow and outflow, periodic along the wind, periodic on all faces) at n = 32, 64 and 128. `plot_boundary_control.py` draws Figure 4.
* `contrast_series.json`, `validated_scalar_series_20261029.json`, `apk_chi10_history.json`, `athpp_chi1000_series_20261029.json`: the contrast and AthenaPK histories. `plot_contrasts.py` and `plot_hllc.py` draw Figures 5 and 9.
* `plot_morphology.py` draws Figures 1 and 2 and the maps of Figure 7 from the column density picture strips of the complete runs (one folder per run on the [runs branch](https://github.com/KaanBoge/cloud-studio/tree/runs)); `check_contrast_maps.py` confirms that those strips belong to the calculations of Figure 5.
* `add_n128_series.py`, `make_boundary_control_series.py` and `summarize_series.py` assemble the series and print the numbers quoted in the text.
* `custom_code/`: the cloud initializer for GIZMO and the modified AthenaPK sources of the radiative pair, with their licence.
* `RUN_INVENTORY.csv`: the calculations and where they appear in the paper.

The figure scripts run with Python 3, numpy and matplotlib; `plot_morphology.py` also needs Pillow. The raw simulation outputs are not part of the repository.
