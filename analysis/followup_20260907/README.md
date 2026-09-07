# Ryan follow-up: verified repairs and outstanding science

7 September 2026. These are code repairs and validation experiments, not a
completed twelve-code production comparison. No historical native data were
deleted, no old result was relabelled as a corrected rerun, and no email was sent.

## What changed in this follow-up

1. **Analysis integrity.** Figure inputs are checked against the original native
   parameter file and its hash. A common group name can no longer hide different
   Mach numbers, gamma, velocity radii, edited physical metadata, wrong time
   conversion, code labels or domain size. Figure 2 uses resolution-specific line
   styles and rejects negative dense mass. Cooling and tracked-frame inputs are
   refused by this fixed-frame, nonradiative figure pipeline until separately
   reviewed. Boundary conditions, tracers and particle kernels are NOT certified
   by these checks.
2. **Safe execution and retention.** Both launchers now check the Windows volume
   backing WSL as well as the guest filesystem. The old `week_queue.sh` and
   `gal_queue.sh` are replaced with refusal messages: they used stale inputs,
   coarse output cadence and deletion after lossy export. Original scripts are
   backed up outside run directories. The legacy cooling generator also refuses
   before writing an output. These changes do not restore previously deleted data.
3. **Experimental Athena++ frame tracking.** A separate source file/executable
   saves the frame velocity and displacement in restart files, initializes wind
   parameters on restart, transforms momentum/energy and primitive velocities
   including ghost cells, and updates the timestep estimate. Tracking is off by
   default; `problem/galilean_shift=true` enables it. The ordinary production
   binary was not replaced. See validation and limitations below.
4. **Viewer accuracy.** Mach variants have distinct readable code labels instead
   of disappearing or sharing an empty code label. Historical `apkcool` entries
   are explicitly marked **cooling NOT enabled**; legacy tracking remains
   unvalidated. Every distinct finite measured timestamp is retained, including
   times above 5. The viewer sorts times and removes exact duplicate timestamps;
   it does not invent missing frames. A visible warning points to the audit.
   Time labels follow the actually displayed mesh, not a pending download.
   Each comparison pane shows its own measured time. Failed downloads are
   labelled, and outdated requests cannot install meshes from a previous run.

## Native evidence, not only source inspection

The earlier IC audit checked 24 native initial outputs in eight grid codes and
12 particle-generator inputs. This follow-up rechecked 18 retained short grid
diagnostic sequences against the stricter physical metadata gates. The sample
figures are explicitly **IC audit tests**, not the requested late-time Figure 1/2.

42 Python unit tests pass: storage 7, comparison 10, cooling refusal 2, original
analysis 6, additional analysis 4, optimized launcher 13. Two JavaScript test
scripts parse the viewer module and exercise diagnostic, metadata and time rules.
An isolated headless Edge test loads a real streamed frame, verifies distinct
Mach labels and the cooling warning, delays a frame request to check label/mesh
agreement, scrubs to the final frame and tests the collapsible panel. It reports
no JavaScript errors. The figure PNGs and browser screenshot were visually inspected.

Six short native 3D tracking tests pass, including chi=10,100,1000, tracking-off
comparison and checkpoint restart. Tracking-off agrees exactly with the baseline
in saved fields. Restart vs uninterrupted final fields differ by at most
2.56e-15 after scaling each field by max(1, its maximum absolute value).
An earlier failed restart test remains on disk as evidence; a ghost-cell frame
inconsistency was then fixed and all tests rerun into a separate directory.

Six further L3 tests ran to 5 t_cc with **101 native outputs each**, at 64x32x32,
Mach 2. They are low-resolution integration tests, NOT high-resolution production.
Actual output times are read from the native files, not assigned from frame index.
Requested cadence is 0.05 t_cc; step scheduling means those measured times are not
necessarily identical between tests. The final times reached 5 t_cc.

| chi | No tracking: final tracer mass / initial | Tracking: final / initial |
|---|---:|---:|
| 10 | 1.0001605 | 1.0000468 |
| 100 | 0.8891089 | 0.9518129 |
| 1000 | 0.8007386 | 0.8885933 |

These are integrals of rho*C over the box. Small values above one reflect the
discrete mass budget/boundary treatment, not cloud creation. Even tracking loses
about 11.1% for chi=1000 at this resolution. It therefore **does not satisfy “all
cloud material remains in the box”**, and is not enabled in the production queue.
Dense-core tracking is not a substitute for a tracer budget or boundary-flux audit.

This prototype follows gas selected by rho > rho_cloud,0/3.
[Farber & Gronke (2022), section 2.3](https://arxiv.org/pdf/2107.07991) instead
uses tracer-selected upstream material and an inflow buffer. Their 4R buffer
cannot simply be copied into our current box with only 3R upstream clearance.
Implementing that full setup requires a reviewed domain/tracer specification
shared by the comparison codes. We do not claim this is their complete scheme.

## Important cooling correction

All nine retained `*apkcool*/athinput` files omit `cooling/enable_cooling=tabular`.
All nine corresponding native logs explicitly report the integrator/table
parameters **unused**. The native hydro source defaults the enable switch to
`none`. Those historical runs did not activate tabular radiative cooling.
Eight such runs are currently listed by the viewer's dense map; the ninth input
and log are also preserved locally. `evidence/cooling_audit.json` lists all nine
with hashes and independent log evidence. Example native inputs and logs are
included in `evidence/cooling_inputs/`.

The retained inputs also set T_wind=6.061408316891257e-9 K, using artificial CGS
values convenient for a dimensionless nonradiative test. These must not be used
with a physical plasma cooling table. Their table is Schure, not the requested
Sutherland & Dopita (1993). Adding the missing switch alone would not fix this.
Townsend describes the integration method; it does not specify a physical cloud.

Required before radiative production: agree on a physical cloud radius, density
and temperature (or equivalent cooling-to-crushing-time ratio), metallicity,
ionization/mean molecular weight, table source and range, temperature floor and
any high-temperature cutoff. Then validate cooling independently against a
single-zone reference and timestep refinements before adding cloud dynamics.
No arbitrary physical values were chosen in this follow-up.

## Answering the velocity-profile question

The tanh velocity profile was an earlier implementation error, not a prescription
we can attribute to the cited paper. The corrected native IC tests use
rho=1+(chi-1)*[1-tanh((r-R)/(0.1R))]/2, pressure=1, with velocity zero inside 1.3R
and constant wind outside. [Gronnow et al. (2018), section 2](https://arxiv.org/pdf/1805.03903)
specifies a **sharp** velocity boundary at 1.3R; its smooth profile is for number
density, with variable molecular weight. Our fixed-molecular-weight mass-density
edge is a custom setup, not an exact reproduction of that paper or Braspenning.
Ryan should confirm whether to retain this custom smooth-density setup or use a
sharp cloud density boundary before spending storage on the replacement campaign.

## What is not complete

There is still no validated all-twelve-code comparison with the same evolved
resolution, boundary conditions, passive tracers and late retained-material time.
Lagrangian resolution is not fixed by particle count alone. Corrected production
runs, radiative validation, full tracer-based frame tracking and late-time common
figures remain unfinished. Movies and quantized isosurfaces cannot recover raw
pressure, velocity or tracer fields removed by previous workflows.

At this audit Windows C: had about **35.6 GiB free**; WSL misleadingly showed about
165 GiB guest space. The new guard budgets against the smaller value and keeps
10 GiB reserve. Existing L5/L6 optimized profiles reserve about 38/236 GiB, so
neither large campaign is launched. This conservative check does not credit
already allocated reusable VHDX blocks. More verified storage is needed; no
automatic deletion, VHDX compaction or unrelated application termination occurred.

Hardware: Ryzen 7 7800X3D, 8 cores/16 threads; 32 GB RAM; RTX 4070 Ti SUPER,
16 GB VRAM; Windows with WSL2 Ubuntu. Windows C: reports 1,999,283,154,944 bytes
capacity. This is filesystem capacity, not a verified SSD make/model.

## Directory contents and reproducibility

```
C:\Users\kaanb\CloudCrushing\followup_20260907\  source, tests, this report
/home/kaan/followup_20260907/
  bin/athpp_tracking              separate experimental executable
  before/                        untouched pre-edit scripts, not published
  logs/build_tracking.log         build attempts, including initial failure
  tracking_tests/                 first test generation, including failed restart
  tracking_tests_v2/<case>/
    athinput                     native runtime configuration
    run.log                      actual MPI command's solver output
    *.athdf                      native 3D density, pressure, velocity, tracer outputs
    *.rst                        native restart files including frame state
    *.hst                        history including frame_v and frame_x
    verification.json            measured fields, times, hashes, test scope
  evidence/                      machine-readable audit and comparison reports
```

Ordinary simulations run in each solver's own directory using its own executable;
they are not FLASH results with different labels. Native files are subsequently
read by analysis scripts (yt or native readers), visualized into PNGs/isosurfaces,
and optionally encoded into MP4 with ffmpeg. The browser displays exported meshes;
uploading arbitrary native files does not automatically turn them into movies.

`stage.sh` installs safeguards with backups and runs unit tests. It deliberately
retires the two dangerous queues; inspect before running it on another machine.
`build_tracking.sh` uses the existing Athena++ configuration and separate object/
binary directories. `verify_tracking.py` and `--full-time` run the tests on this PC
and refuse existing case directories rather than overwriting data. They require
the locally compiled dependencies and the `../verified_20260907` Python modules.
`validate_followup.py` runs the non-production regression suite. Nothing here is
a portable replacement for the native code checkouts.

## Before a paper-ready comparison

Agree on the density IC and radiative physical scale with Ryan; decide the common
domain/boundaries/tracer and demonstrate tracking retention. Allocate storage for
native output retention. Only then launch one pinned corrected baseline per code,
validate it, and expand to the matched ladder. Reuse compatible raw results where
proven; don't mix incompatible historical simulations or call a prepared input a
finished run.
