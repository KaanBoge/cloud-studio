# Extended native frame-tracking validation

7 September 2026. The tests are completed. **All-material retention is NOT
validated.** This is the Athena++ prototype, not all twelve solvers or the complete
Farber/Gronke buffer method. The existing conditions were retained.

## Results

Eight native 3D tests produced 475 snapshots, all retained and analyzed. Three
level-3 late restart tests produced 50 remaining snapshots each, two short MPI
tests produced 11 each, and three new full-duration level-4 tests produced 101
each. The restart outputs are continuations, not new full 101-frame runs.

| Validation | Result |
|---|---|
| Late restart at chi=10,100,1000 | PASS; final fields agree with uninterrupted runs, maximum scaled error 5.55e-15 |
| MPI 1 vs 4 ranks at L3 chi=100 | PASS; maximum scaled final-field error 1.28e-15 |
| Frame velocity/displacement | PASS; history recorded every step at high precision; offset integrated independently |
| Frame metadata and native snapshot pairing | PASS; contemporaneous measured times, not guessed frame numbers |
| Native tracer integral vs native history | PASS within 1e-10 relative; every saved snapshot checked |
| Finite fields and positive density/pressure | PASS; every saved snapshot checked |
| Initial fields for new L3/L4 runs | PASS against the existing IC prescription |
| Native history parser negative tests | Six unit tests pass, including headerless restart, missing header, malformed data and ordering |
| Complete material retention | NOT ESTABLISHED; chi=100 and chi=1000 fail even a 1% net-mass tolerance at 5 t_cc |

Full-duration tracked runs at the same Mach=2 and existing box/IC:

| chi | L3: 64x32x32, final tracer fraction | L4: 128x64x64, final tracer fraction | L4 native outputs |
|---|---:|---:|---:|
| 10 | 1.0000468 | 1.0000057 | 101 |
| 100 | 0.9518129 | 0.9841870 | 101 |
| 1000 | 0.8885933 | 0.9535786 | 101 |

These fractions are the volume integral of rho*C at the final time divided by
its initial value. Improved retention at higher resolution is not proof of
convergence. Small values above one are discrete mass-budget discrepancies, not
physical creation of cloud material. A 1% tolerance is only an explicit diagnostic;
it cannot certify zero cloud-material flux through the boundaries.

Both resolutions end at measured 5 t_cc. Output count 101 does not imply exactly
identical intermediate physical times: each solver writes after a completed
step. The JSON retains all measured times and the offset from requested cadence.
No synthetic time labels, interpolation or duplicated frames are used here.

## New validation improvements

The history output now uses `%24.16e` and records every completed step during
these tests. This changes diagnostic precision/cadence, not the solver or physical
setup. The previous `%12.5e` history was too coarsely printed for an exact
per-snapshot frame-coordinate audit.

Athena++ can write a headerless history in a fresh restart directory because its
output counter is restored. The validator now reads the column names from the
original run's retained history, rather than guessing them. The initially stopped
validation reused its successfully completed native run after this reader fix;
it did not overwrite or rerun that trajectory.

Frame reconstruction is x_lab=x_frame+frame_x and v_lab=v_frame+frame_v. Metadata
are paired to the actual native output time. This permits correct coordinate
interpretation; it does not make different fixed-grid evolutions exactly invariant
under a Galilean boost.

No C++ source, binary or production configuration changed in this pass. The
tracking binary SHA256 remains
`3885d83e2238eae01382b88add7a168f713ef72f46420c44219ad23bc7bd7655`.

## Retention and cooling next steps

The tracker follows a density-selected core and can still lose the wake or
mixed material. Do not publish these as demonstrating all material stays in the
box. Further tracker/boundary-flux work is required; replacing the current setup
with a different box, tracer definition or density law was not authorized by this
validation request.

The earlier cooling-labelled cases must be rerun from t=0 with correctly
configured, independently validated cooling. Switching cooling on at a late
checkpoint or modifying a movie cannot produce the missing radiative evolution.
Their historical raw files remain untouched. No cooling or L5/L6 production
simulation was launched in this pass. The existing physical-unit and storage
preflight requirements still apply.

## Files

- `tracking_validation.py`: opt-in test campaign, same pinned binary, storage guard,
  exclusive production lock and preserved outputs.
- `test_tracking_validation.py`: native history parser positive/negative tests.
- `evidence/tracking_extended.json`: all measured snapshot diagnostics, frame
  offsets, hashes, actual commands and passing/failing criteria.
- `evidence/tracking_extended_inputs/<case>/`: native input, solver log, high
  precision history and provenance.
- Local raw `.athdf` and `.rst` files remain under
  `/home/kaan/followup_20260907/tracking_validation_v1/<case>/`.

The CLI refuses existing directories unless `--resume-validation` is supplied.
That option only reuses an identical, completed, hash-checked case and redoes
analysis. It is not recovery from an arbitrary interrupted production job.
