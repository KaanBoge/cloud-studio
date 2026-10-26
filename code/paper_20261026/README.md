# Cloud-wind code and saved reductions — 26 October 2026

This dated package supports the revised cloud-survival manuscript. It contains the recorded GIZMO initializer, modified AthenaPK source components, cooling inputs and table, and portable plotting code with saved scalar reductions.

## Contents

- `plot_revision.py`: regenerate the mass-history and separate GIZMO/cooling diagnostic figures from `plot_series.json` and `diagnostic_series.json`. Requires Python 3 and matplotlib; run `python plot_revision.py`. Figures are written to `figures/`.
- `gizmo_full_histories.json`: four accepted 101-state GIZMO histories, including the supporting initial-velocity controls.
- `gizmo_generator_sharp.py`: the recorded initializer; the reported finest run used volume mode (uniform spacing, variable masses).
- `athenapk_hydro.cpp` and `athenapk_tabular_cooling.*`: exact modified source snapshots, identified in `source_manifest.json`.
- `cooling_on.in`, `cooling_off.in`, `solar.cooling`: the recorded matched-pair inputs and cooling table.
- `SOURCE_NOTES.txt`: numerical changes, dependencies and source provenance.
- `cooling_estimate.json`: mixed-phase cooling-time estimate.
- `revision_notes.txt`: completed editorial changes and scientific tests still required.

The source components require the compatible upstream solver build described in SOURCE_NOTES.txt. This package is for inspection and reproduction of the saved reductions; it does not contain a simulation launcher. The shared-flux fallback changes numerical diffusion. Matching particle sampling, reconstructed pressure and wind boundaries, along with further resolution tests, remains necessary for a controlled cross-code interpretation.

## Attribution

The AthenaPK source headers and BSD 3-Clause license are preserved in LICENSE-AthenaPK.txt. Repository licensing remains scoped by the root LICENSING.md; the simulation sources and research data are not blanket relicensed. See the manuscript bibliography for scientific references.
