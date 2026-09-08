# Methods and reproducibility

## Scope

This is a native-code cloud-crushing research workspace and public evidence archive, not one universal executable. Kaan Boge maintains the project with scientific mentorship from Dr. Ryan Farber. The current accepted experiment is a **within-code velocity-prescription sensitivity study**, not a finished comparison in which all codes have identical evolved resolution and boundary physics.

## Execution

Each solver is compiled from its own source and run under WSL2 Ubuntu on Windows. CPU codes use their native parallel runtime; AthenaPK uses CUDA on the NVIDIA GPU. Launch scripts record inputs, commands, executable/source hashes, clocks, memory and output retention. The current hardware is a Ryzen7 7800X3D (8physical cores/16threads),32GB installed RAM and an RTX4070TiSUPER with16GB VRAM. A code is not GPU-enabled merely because the machine has a GPU.

## Current experiment

Chi100, Mach2, gamma5/3; nominal ambient density and pressure1; cloud radius1 (FLASH uses a rescaled0.1); existing tanh density edge of width0.1R and20×10×10R domain. The sharp velocity law is zero inside1.3R and constant wind velocity outside. Each native pair holds its source/binary, numerical settings and initial nonvelocity fields fixed, with consistent energy for the selected velocity.

AthenaPK's historical law had constant outer momentum. It must not be described as tanh velocity. Original code-specific pressure initialization, boundaries, tracers, particle kernels and time staggering are documented in the accepted reports. Density edge and velocity edge are different prescriptions; this setup is not claimed as an exact reproduction of a cited paper.

The cloud-crushing time is t_cc=sqrt(chi)R_cloud/v_wind. Dense mass uses rho>rho_cloud,initial/3 and a fixed measured native initial dense-mass denominator within each level/pair. Quantities and units come from native parameters where available and are checked against recorded provenance.

## Output to figures and interactive 3D

1. The native solver evolves the fluid and saves 3D states plus logs and restart data.
2. Native readers and yt load measured fields and times. Validators check dimensions, initial laws, finite/positive fields and diagnostics; independent reader checks are code-specific.
3. Analysis produces mass-evolution curves and resolution overlays. Any interpolation applies explicitly to scalar diagnostics, not invented 3D frames.
4. Matplotlib makes 2D views of 3D states. Extracted surfaces provide 3D geometry. ffmpeg encodes rendered frame sequences into movies.
5. The browser displays exported geometry through three.js. Camera motion does not simulate new physics. Surface/terrain exports must be labelled by what they represent.

Example layout, with actual filenames varying by code:

```text
run/
  native-input                   Physical and numerical parameters
  run.log                        Actual solver output
  DD0000/CW_0000                  Enzo state metadata
  DD0000/CW_0000.cpu0000          Native HDF5 fields (rank layout varies)
  DD0001/...                     Next measured output
  result.json                    Validation and provenance
  resources.jsonl                Sampled resource use
analysis/
  report.json                    Measured diagnostic series
  mass_and_retention.png          Quantitative figure
  README.md                      Interpretation and limitations
```

## Reproduce carefully

Use [the study plan](../analysis/sensitivity_20260907/PLAN.md), the relevant code report and its pinned input/source evidence. Scripts contain machine-specific paths and require separately acquired native-code dependencies. Build or run in a **new directory**. Do not rerun a completed launcher against an existing result directory, infer activity from an old PID, or overwrite a frozen report.

Validate storage for the entire retained run or pair, accounting separately for WSL and its backing Windows drive. Do not sum their free space. Keep double precision and accepted numerics unchanged. A lossless archive must be restored and checked before any storage workflow relies on it; a metadata inventory is not such a check.

## Limits to report in a paper

Resolution labels refer to initial cells/elements per cloud radius, not MP4 pixels; level6 is512×256×256. Moving meshes/particles change their spatial resolution during evolution. Two coarse levels do not establish convergence. Paired curve separation is not error against an exact solution or a ranking of solvers. A shared final time of5t_cc does not prove all cloud material remained in the box. Cooling and tracking results must pass their separate physical and numerical validation before use as a matched comparison.
