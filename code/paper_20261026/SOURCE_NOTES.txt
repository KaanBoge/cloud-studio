Source snapshots supporting the 26 October 2026 working draft

gizmo_generator_sharp.py is the recorded project initializer. The reported
finest run selected its volume mode: uniform lattice, variable particle mass,
and internal energy assigned from constant analytic pressure. The file also
supports a legacy equal-mass mode; that mode was not used for the stated run.
Dependencies: Python 3, numpy, h5py. Read its command-line help before reuse.

athenapk_hydro.cpp, athenapk_tabular_cooling.cpp and
athenapk_tabular_cooling.hpp are exact source snapshots from the retained
tracer_global_build_20261026_v1 build family. SHA-256 identifiers are in
source_manifest.json. The original AthenaPK copyright headers and BSD
3-Clause license are retained. These snapshots include project modifications
and are not presented as unmodified upstream AthenaPK.

In the bounded-tracer correction, shared fluxes are used by both neighbours.
If invalid candidate states persist on the last of four correction sweeps,
the hydro code switches the entire domain to a first-order local Lax-Friedrichs
update computed from the original stage state. The cooling-on/off pair used
the same binary. The recorded final fallback counts are 23 and 55. This
changes numerical diffusion and requires scientific resolution tests; it is
not a universal positivity or convergence certificate.

The cooling source assumes a fixed ionized H/He composition and uses a solar
equilibrium table with n_H squared normalization. Input examples and the exact
table are included. Paths in example inputs describe the recorded setup;
configure output locations explicitly before a new build or run.

These files document the changed components rather than a standalone solver
distribution. Reproduction of the executable also requires the compatible
AthenaPK/Parthenon/Kokkos source tree, generated configuration, problem generator,
compiler options and linked libraries retained in the local research archive.
The upstream commit is not reconstructed from the file hashes. No launch
authorization or live runtime-control state is included.
