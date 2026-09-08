# Cloud-crushing analysis: verification status

The [velocity-prescription sensitivity study](sensitivity_20260907/README.md)
now tests historical versus corrected initial velocities within each native code
at fixed chi=100 and Mach=2, following Ryan's request to measure impact before
deciding which old runs need replacing. Forty-four full controls are validated
and analyzed, including Athena 4.2 L3/L4/L5, Enzo/Enzo-E/RAMSES/FLASH 4.8/Flash-X/Arepo L3/L4,
GIZMO MFM L3/L4 and Gadget-4 L3. [Gadget-4's result](sensitivity_20260907/gadget4/README.md)
retains the original SPH pressure deviations and periodic boundaries, and is
not a matched uniform-pressure grid baseline. GIZMO MFV's two full L3 attempts failed positive-energy
checks and are published as failure evidence, not accepted controls. See
[GIZMO results](sensitivity_20260907/gizmo/README.md). Larger pairs remain
separately guarded. These experiments are distinct from the historical viewer.

Updated 7 September 2026. **Historical runs are not yet a validated matched-code
comparison.** The corrected scripts are in `verified_20260907/`. Previous
analysis entry points are retained under `legacy_before_20260907/` for provenance,
not recommended for execution. See [the verification report](../verification.html).

The [follow-up report](followup_20260907/README.md) adds stricter figure checks,
Windows-backed storage guards, native restart/tracking tests and a correction:
the historical `apkcool` runs did not enable cooling. It includes the remaining
scientific and storage blockers; this is still not a completed production comparison.

## What was verified

The actual 3D initial output of Athena++, AthenaPK, Athena 4.2, FLASH 4.8,
Flash-X, Enzo, Enzo-E and rectangular RAMSES was checked at chi=10,100,1000:
24 tests, each on a 64 x 32 x 32 uniform grid. Density, velocity, pressure,
domain dimensions and cell count pass within stored-output precision. These
are initial-condition tests after short native-solver runs, not complete science runs.

Arepo, GIZMO, Gadget-4 and Gasoline additionally passed 12 tests of generated
3D IC files on an equal-volume lattice. These do NOT certify their solver's
kernel-estimated densities, boundary fluxes or later evolution. GIZMO's MFM
and MFV solver modes share the tested IC generator; they were not each evolved here.

Each solver evolves its own equations using its own executable. Shared custom
problem generators specify the experiment; the analysis and browser do not
run FLASH under other code labels. Binary/source hashes and native test inputs
are included in `verified_20260907/evidence/`.

## Initial-condition correction and citation

The corrected test prescription retains the existing mass-density tanh edge:

    f = (1 - tanh((r/R - 1)/0.1))/2
    rho = rho_wind * (1 + (chi-1)*f)
    v_parallel = 0 for r <= 1.3 R; v_wind otherwise
    v_transverse = 0; P = P_wind

[Gronnow, Tepper-Garcia & Bland-Hawthorn (2018), section 2](https://arxiv.org/pdf/1805.03903)
describes a sharp velocity boundary at 1.3 cloud radii, not a tanh velocity.
It smooths number density and accounts for variable molecular weight; our
mass-density law is not an exact reproduction of that entire experiment.
This prescription is a documented custom choice, not a claim that
[Braspenning et al. (2023)](https://arxiv.org/pdf/2203.13915) used the same IC.
The 1.3 R cutoff does not guarantee numerical stability or no dense-moving gas
in the density tail. Changing source code does not fix previously evolved data.

## Workflow and actual files

1. A native solver reads its problem generator, compile options and input file.
2. It evolves the gas and writes numerical fields: HDF5/ATHDF/PHDF, VTK,
   Enzo directory hierarchies, RAMSES AMR/hydro binary shards, Gadget-style
   HDF5, or Gasoline TIPSY. These are data, not movies.
3. Python reads these using yt **where supported**, h5py or code-specific
   readers. Native-leaf mass sums must not use a downsampled visualization grid.
4. Matplotlib renders image frames; ffmpeg encodes MP4s. A separate marching-cubes
   exporter builds quantized isosurface meshes that the three.js viewer displays.
5. Publishing uploads those derived assets. It does not convert raw files into
   a movie automatically, and meshes/MP4s do not preserve all fluid variables.

Typical native run directory (actual smoke inputs are in the evidence folder):

    run/
      athinput / flash.par / CloudWind.enzo / run.nml / *.in / parameter file
      provenance.json            # new runner: parameters and pinned binary hash
      run.log                    # native solver stdout/stderr
      native snapshot files or output directories
      restart/checkpoint files   # when configured
      mass_diagnostics_v2.json    # derived, does not replace snapshots

## Output cadence and resolution

The campaign TARGET is 101 native snapshots, t/t_cc=0,0.05,...,5.
This is a target, not an assertion that all published historical runs achieved it.
Read actual times from output headers. Never fill missing samples with repeats
or invent an evenly spaced time array. Output frequency is not the solver timestep.

`t_cc = sqrt(chi)*R/v_wind`. FLASH 4.8 uses R=0.1 in the audited inputs while
most other grids use R=1, so their code-time values differ by a factor of ten.
The new parser reads R and rho from the parameter file and prints the derived
parameters; AthenaPK units and its density ratio are handled explicitly.

The ladder describes the initial spatial grid, not a cube:

| Level | Streamwise x transverse x transverse | Cells per R |
|---|---|---|
| 1 | 16 x 8 x 8 | 0.8 |
| 2 | 32 x 16 x 16 | 1.6 |
| 3 | 64 x 32 x 32 | 3.2 |
| 4 | 128 x 64 x 64 | 6.4 |
| 5 | 256 x 128 x 128 | 12.8 |
| 6 | 512 x 256 x 256 | 25.6 |

Low levels may not resolve the cloud or its edge adequately. Equal-volume
particle spacing is not identical effective SPH smoothing or moving-mesh resolution.

## Corrected analysis usage

Run from `verified_20260907/`, with the native inputs/outputs accessible:

```bash
python diagnostics_v2.py --kind athpp --params /path/run/athinput \
  --group reviewed_M2_sharp13_inflow_outflow --out /path/new_diagnostics.json \
  /path/run/CloudWind.out2.00000.athdf /path/run/CloudWind.out2.00001.athdf
python figure2_v2.py --out new_convergence.png /path/level3.json /path/level4.json
python check_snapshot.py /path/initial.athdf --params /path/run/athinput \
  --kind athpp --center 0 0 0 --dims 64 32 32 --out new_check.json
python -m unittest test_analysis.py
```

Figure 2 uses `M_dense(t)/M_dense(0)` with `rho > rho_cloud,initial/3`.

`figure1_v2.py --plan comparison.json --time 3 --out figure1.png` takes a JSON
plan with a `panels` list; each panel supplies `diagnostics` (a schema-2 JSON path)
and `center_code` (three explicit native coordinates). It reads chi, wind speed
and time scale from the original parameter file, verifies its hash, and rejects
missing common times, unequal measured resolution, mixed groups and incomplete
code/overdensity combinations. Every panel shows its actual measured time.
The full 20 R x 10 R x 10 R domain is shown. A missing/unreadable file is an
error, not evidence of a fully mixed cloud. An empty isosurface alone also cannot
distinguish mixing from material leaving the box. This version supports uniform
native grids only; it does not assert that all cloud material remains in the box.

`dense_export_v2.py --diagnostics new_diagnostics.json --center 0 0 0 --out NEW_DIRECTORY`
exports every measured uniform-grid snapshot, including empty surfaces, without
a t<=5 cutoff or guessed times. It refuses an existing directory and writes the
index only after every snapshot has exported successfully. Center coordinates
must be specified in the native code's coordinate system. AMR resampling and
particle reconstruction require further validation and are not silently substituted.
Old positional invocations of the figure/export scripts now fail with usage help.

The example PNGs in the evidence directory are explicitly labelled **short IC
audit tests, not science production**. They are not the requested late-time paper figures.

The diagnostic definition is unchanged by plotting:
It does not divide by the changing total mass in the box. The original t=0
snapshot is required. Duplicate times, non-finite fields and old fraction-only
JSONs are rejected. Resolution labels come from measured native grid metadata.
`--group` is a reviewed experiment ID, not automatic certification of matching physics.

The special `ramses_native.py` reader supports the audited rectangular, six-face
boundary layout. The standard yt reader omitted the second interior coarse cell
in this patch. Other RAMSES layouts are explicitly rejected, not guessed.
Enzo-E's IC test uses its native HDF5 fields; general Enzo-E mass analysis is not
implemented in this version. Particle diagnostics still require further validation.

## Running and retaining data

`run_corrected_athpp.py --level 3 --chi 10` prepares a fresh, versioned directory.
Adding `--run` explicitly starts that one run using the hash-checked native binary.
It supports input generation for levels 1 through 6, but this audit validates
native initial fields at level 3 only. Memory/disk checks precede launch.
It retains outputs and checks actual cadence after completion. It does not launch
other codes or claim that an L6 production campaign is already validated.

The destructive `redo_athpp.sh` path was replaced; the automatic
`sweep_clean.sh` raw-data deleter was disabled. Other historical queue scripts
remain historical and must not be blindly restarted. Native data already deleted
by earlier workflows cannot be reconstructed from a mesh or movie.

## Still required before a matched research comparison

Review boundary conditions, tracer definitions, particle mass/kernel resolution,
floors and all production inputs. Some particle builds remain periodic rather
than wind-inflow/outflow. Rebuild and pin every intended production variant;
old per-run binaries do not change when a source file is edited. Re-run affected
experiments under distinct IDs and validate all measured times and in-box material.
Cooling and Galilean-frame variants remain experimental/unvalidated. No large
production campaign was restarted during this audit.

Hardware: Ryzen 7 7800X3D (8 cores/16 threads), 32 GB RAM, RTX 4070 Ti SUPER
(16 GB VRAM), WSL2 Ubuntu. WSL reported 1007 GiB filesystem capacity and about
195 GiB free at the start of this audit; this is not a physical SSD model/capacity audit.
