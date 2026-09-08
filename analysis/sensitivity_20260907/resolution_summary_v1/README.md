# Velocity sensitivity: resolution summary

## What the completed tests show

46 accepted full controls (23 velocity-law pairs) at chi=100 and Mach=2 are represented here. They contain 4,650 native states used in the accepted analyses. No simulations were rerun to build this summary.

The blanket replacement queue remains inactive. The effect varies by code and resolution; no historical run is automatically approved for reuse or selected for replacement.

## Peak separation of paired dense-mass curves

Each entry is `100 * max_t |M_dense,sharp(t) - M_dense,historical(t)| / M_dense(0)`. Dense means rho > initial cloud density / 3. Each resolution pair has its own fixed measured initial dense-mass denominator. Values are percentages of that initial mass, not exact-solution errors, statistical significance, or a ranking of codes.

All source methods explicitly use linear interpolation of scalar mass diagnostics onto 0:0.05:5 t_cc for this descriptive peak. Native states and their actual timestamps are unchanged. Equal nominal cadence does not make every native header time identical.

| Native code | L3 | L4 | L5 | Accepted controls |
| --- | ---: | ---: | ---: | ---: |
| [Athena++](../analysis/report.json) | 8.145% | 6.801% | Not tested | 4 |
| [AthenaPK](../analysis/report.json) | 5.947% | 1.139% | Not tested | 4 |
| [Athena 4.2](../athw/report.json) | 13.085% | 7.591% | 8.695% | 6 |
| [Enzo](../enzo/report.json) | 23.356% | 3.236% | Not tested | 4 |
| [Enzo-E](../enzoe/report.json) | 8.211% | 6.348% | Not tested | 4 |
| [RAMSES](../ramses/report.json) | 7.471% | 4.179% | Not tested | 4 |
| [FLASH 4.8](../flash/report.json) | 10.370% | 6.165% | Not tested | 4 |
| [Flash-X](../flashx/report.json) | 10.133% | 6.543% | Not tested | 4 |
| [Arepo](../arepo/report.json) | 2.811% | 2.699% | Not tested | 4 |
| [GIZMO MFM](../gizmo/mfm_levels_report.json) | 3.979% | 0.955% | Not tested | 4 |
| [Gadget-4 SPH](../gadget4/l3_report.json) | 6.954% | Pending | Not tested | 2 |
| [GIZMO MFV (repaired)](../gizmo/mfv_repaired_pair.json) | 6.438% | Pending | Not tested | 2 |
| Gasoline | Held | Held | Not tested | 0 |

L3 = 64 x 32 x 32 (3.2 initial elements/R); L4 = 128 x 64 x 64 (6.4/R); L5 = 256 x 128 x 128 (12.8/R). Particle/moving-mesh labels describe the initial lattice, not fixed evolved spatial resolution. L6 would be 512 x 256 x 256, not 512 cubed; it is not tested here.

## Decision limits

Athena 4.2 changes from 13.09% to 7.59% to 8.70% across L3/L4/L5: even the available three-level sequence is not monotonically declining. The smaller L4 differences in other codes do not establish convergence, negligible impact, or validity at a different chi, Mach, resolution or numerical recipe.

AthenaPK's historical prescription was constant outer momentum, not tanh velocity. The other accepted pairs compare historical tanh velocity with a sharp boundary at 1.3R. Within each pair, the completed source reports validate the retained native-code setup; they do not certify identical pressure and boundary conditions across codes.

This narrow summary addresses dense-mass evolution. It does not validate simultaneous velocity diagnostics, cooling, magnetic fields, Galilean tracking, or an all-material-retained final figure. A reuse decision needs a prospective, science-specific tolerance agreed with Ryan and a provenance match to each historical run. No universal cutoff is introduced here.

## Remaining work and unchanged holds

Eight full L3/L4 controls remain, in addition to higher storage-held levels:

* Gadget-4 SPH L4 (2 controls): Full-pair storage gate; proposed raw relocation not yet approved. Full runner still needs freezing and review. Existing L4 validation must not be repeated.
* GIZMO MFV (repaired) L4 (2 controls): Full-pair retention budget and L4 initial-condition/timing/repair validation remain pending.
* Gasoline L3 (2 controls): Scientific repeatability decision required; existing field-equivalence gate failed. Do not relax it or rerun completed traces.
* Gasoline L4 (2 controls): Same scientific hold as L3; same-executable sharp initial-condition validation and full runner remain pending.

Existing Gasoline diagnostic states are not one accepted 101-frame run. The original failed MFV controls are excluded; only the validated repaired MFV pair appears above.

No raw relocation/deletion, new solver launch, threshold change or production-viewer entry is performed by this summary. Movies, meshes and these reports are not raw-data backups.

## Source-specific caveats

### Athena++

* Only velocity changes within each code pair; tracer and native axis differ between codes.
* L3/L4 have 3.2/6.4 cells per R: density/velocity edge behavior is underresolved and requires finer confirmation.
* Finite box and tracer loss can contribute to late-time differences.
* No claim of negligible impact, convergence, all-code comparability or suitability for a paper based on this pilot alone.
* Existing historical runs still require individual provenance checks before reuse.

### AthenaPK

* Only velocity changes within each code pair; tracer and native axis differ between codes.
* L3/L4 have 3.2/6.4 cells per R: density/velocity edge behavior is underresolved and requires finer confirmation.
* Finite box and tracer loss can contribute to late-time differences.
* No claim of negligible impact, convergence, all-code comparability or suitability for a paper based on this pilot alone.
* Existing historical runs still require individual provenance checks before reuse.

### Athena 4.2

* Three finite resolutions do not establish a universal reuse decision or convergence.
* Net tracer retention is not proof that no material crossed a boundary.
* Native VTK is float32; density/tracer equality is checked at this native precision.
* Tracer concentration is chi*f/rho in Athena 4.2, unlike the other codes; interpret within-code pairs.

### Enzo

* L3/L4 only; L5 pair storage-held, no convergence or universal historical reuse decision.
* All 102 actual native times per run are retained, including the extra terminal dump.
* Tracer loss means t=5 is not a certified all-material-retained figure time.
* Full native fields remain on disk; derived figures are not raw backups.

### Enzo-E

* No passive tracer in either native recipe; material retention is not measured.
* L3/L4 only; L5 pair storage-held. No universal historical reuse or convergence decision.
* Historical radial law from 2D input is tested spherically in the audited 3D setup.

### RAMSES

* L3/L4 are coarse within-code controls, not convergence or a universal reuse decision.
* Native timestep-crossing output times can be slightly later than nominal times; no snapshots were retimed.
* Tracer retention is measured, not assumed. Final images need not retain all initial material.
* The second aggregation shares the native record decoder; stock yt does not support this rectangular patch correctly.
* L5 depends on full raw-retention storage. No raw files have been deleted.

### FLASH 4.8

* No passive tracer in the native FLASH recipe; no tracer-based material retention claim.
* Full checkpoints now saved at every plot time, without checkpoint overwriting; all original plotfields/precision retained.
* L3/L4 are coarse controls, not convergence or a universal historical reuse decision.
* All actual native times retained. Extra same-time forced outputs remain in the raw directory and are listed separately.

### Flash-X

* No passive tracer in the native Flash-X recipe; no tracer-based material retention claim.
* Full checkpoints now saved at every plot time, without checkpoint overwriting; all original plotfields/precision retained.
* L3/L4 are coarse controls, not convergence or a universal historical reuse decision.
* All actual native times retained. Extra same-time forced outputs remain in the raw directory and are listed separately.

### Arepo

* Periodic streamwise boundary retained, not matched to grid-code inflow/outflow. Tracer can recirculate; in-box mass is not proof it never crossed a boundary.
* Original jittered lattice gives native Voronoi density and pressure perturbations; report their measured magnitude. These are identical within each initial pair.
* Initial lattice level is not a fixed later moving-mesh resolution. Coarse tests do not certify convergence or a universal reuse decision.
* All native snapshots, restart files and failed smoke attempts retained. No cooling or frame tracking enabled.

### GIZMO MFM

* Only two coarse levels (3.2/6.4 initial elements per cloud radius), not demonstrated convergence or universal historical reuse.
* Original fully periodic boundaries and native kernel pressure/density deviations retained; not a matched grid inflow/outflow experiment.
* No passive material tracer or all-material-retained terminal-image claim. Conserved output velocity remains staggered.
* MFV L3 failures are excluded from this method-specific result and separately retained as failed controls.
* No snapshots retimed, repeated, deleted or substituted; independent yt evidence covers every accepted native state.

### Gadget-4 SPH

* Single coarse L3 (3.2elements/R), not resolution convergence, exact-solution error or a universal reuse decision.
* Original periodic boundaries and SPH initial pressure up to3.9003x nominal retained identically in both controls; not a matched grid baseline.
* Existing hfix smoothing-length seed patch retained, not a pristine upstream binary. No numerics or native data changed.
* Native scheduled outputs round earlier or later; exact native scheduler reproduced, not timestamps rewritten.
* ID-tagged in-box mass does not demonstrate no periodic boundary crossing. Evolved velocity-time diagnostics remain unvalidated.

### GIZMO MFV (repaired)

* One coarse initial64x32x32 lattice; finer resolution not validated.
* Old failed uninitialized-timestep MFV controls remain excluded.
* Native velocities are staggered; no simultaneous velocity diagnostics.
* Periodic boundaries and kernel-pressure deviations retained; no cross-code equality.
* No passive material-retention diagnostic, cooling or frame tracking.
* Validated analysis is not new production3Dviewer entries or a raw backup.

## Reproducibility and scope of this consolidation

[Machine-readable summary](summary.json) preserves full-precision metrics, source-file SHA256 hashes, exact JSON pointers, actual time endpoints, counts and initial denominators. [Validation record](validation.json) records report-only tests and the scalar cross-check. [Extractor](../build_resolution_summary.py) and [tests](../test_resolution_summary.py) use Python's standard library and never open native outputs or invoke a simulation.

To make a separately named new snapshot from the reports (existing output folders are refused):

```text
python build_resolution_summary.py --study-root STUDY_DIRECTORY --output-directory NEW_SUMMARY_DIRECTORY
```

Enzo contributes 102 native states per accepted case, including its extra terminal state; all other accepted cases contribute 101. The total counts analysis states, not every auxiliary plotfile or checkpoint present in the raw directories. Earlier source validations are referenced, not claimed to have been rerun by this extractor.
