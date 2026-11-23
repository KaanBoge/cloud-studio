Custom source code of the manuscript

gizmo_generator_sharp.py builds the GIZMO starting particles: a uniform lattice
with variable particle mass and internal energy set from a constant pressure.
It needs Python 3, numpy and h5py; its help option lists the settings.

athenapk_hydro.cpp, athenapk_tabular_cooling.cpp and athenapk_tabular_cooling.hpp
are the AthenaPK source files changed for the radiative pair, with their SHA-256
values in source_manifest.json and the AthenaPK copyright headers and BSD 3-Clause
licence (LICENSE-AthenaPK.txt). The tracer update uses shared face fluxes; where
four correction sweeps leave an invalid state, the stage is recomputed with a
first order local Lax-Friedrichs update. The cooling-on and cooling-off runs used
the same binary and recorded 23 and 55 such stages.

The cooling source uses a fixed ionized H/He composition and the solar
equilibrium table solar.cooling with n_H squared normalization; cooling_on.in and
cooling_off.in are the inputs of the two runs. Building them needs the matching
AthenaPK, Parthenon and Kokkos sources.
