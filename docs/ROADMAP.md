# Research roadmap

This is a dated research plan, not an automatically enabled simulation queue.
The scheduled monitor is paused at the user's request. Existing native workers
can continue independently; the [publication observation](../analysis/publication_20260909/enzo_l5_observation.json) is a snapshot, not live status.

## First: Ryan's velocity-sensitivity request

The latest published summary accepts50 controls/25pairs at chi100, Mach2. To
finish the proposed L3/L4/L5 ladder across thirteen methods,28 controls remain
outside that accepted, analyzed set at this publication snapshot (including the
new Enzo pair). They need execution, validation or analysis—not necessarily
another simulation. The first Enzo L5 native run has passed its checks; its paired
analysis remains outstanding. Some other controls need further validation or
storage and are not immediately runnable.

| Code / method | Remaining levels | Controls |
|---|---|---:|
| AthenaPK | 5 | 2 |
| Athena++ | 5 | 2 |
| Athena4.2 | None:3,4,5 completed | 0 |
| Enzo | 5: new pair underway at the dated check | 2 |
| Enzo-E | 5 | 2 |
| RAMSES | 5 | 2 |
| FLASH4.8 | 5 | 2 |
| Flash-X | 5 | 2 |
| Arepo | 5 | 2 |
| GIZMO MFM | 5 | 2 |
| GIZMO MFV | 5 | 2 |
| Gadget-4 | 5 | 2 |
| Gasoline | 3,4,5; scientific validation hold | 6 |

Both velocity laws are needed at each listed level. The Enzo L5 diagnostic pair
passed; full results still need completion and analysis. Gasoline's failed
repeatability gate is not waived. Each next level needs its own admission checks.

## Then: the broader comparison

* Decide with Ryan which historical runs are scientifically reusable. Keep the
  old blanket replacement queue inactive; neither replace nor accept all old
  runs solely from a coarse sensitivity result.
* Fill missing accepted nonradiative Mach2 combinations at chi10,100,1000 on
  integer levels1–6, subject to native feasibility and retention. The exact
  number of required new production runs is not yet established.
* Review and complete selected Mach0.5,1.5 and5 comparisons (or4.5 if chosen
  instead). Existing historical variants are not automatically accepted.
* Validate a tracer-aware frame-following/boundary treatment at all three chi.
  Existing Athena++ tests pass several numerical checks but still lose material.
* Specify physical cooling units, metallicity, table and temperature limits;
  validate the integrator against independent cooling tests, then run radiative
  cloud cases from t=0. The nine historical cooling-labelled cases had cooling
  disabled and are not radiative evidence.

## Deliveries from accepted native data

Common-time density figures at the latest defensible retained-material time;
mass-evolution figures with resolution overlays; 2D views of3D data; interactive
3D surfaces/volumes and terrains labelled honestly; and movies containing every
available real frame. Preserve measured timestamps and publish clear provenance.

The requested all-code equality is a scientific validation objective, not a
property already guaranteed by matching grid labels or color scales.
