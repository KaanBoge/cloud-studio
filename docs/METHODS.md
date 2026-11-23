# Methods and reproducibility

## Scope

Cloud Studio holds my ongoing cloud crushing research: one cloud and one wind, run with twelve hydrodynamic methods. Each method uses its own native solver and its own boundary physics, and the [paper](../paper/Cloud_survival_OJA.pdf) compares their results.

## Execution

Each solver is compiled from its own source and runs under WSL2 Ubuntu on Windows. The CPU codes use their native parallel runtime, and AthenaPK runs on the NVIDIA GPU with CUDA. Launch scripts record the inputs, commands, executable and source hashes, clocks, memory and output retention. The workstation has a Ryzen 7 7800X3D (8 cores, 16 threads), 32 GB of RAM and an RTX 4070 Ti SUPER with 16 GB of video memory.

## The setup

χ = 100, Mach 2, γ = 5/3, with ambient density and pressure 1 and cloud radius 1 (FLASH uses a rescaled 0.1). The cloud has a tanh density edge of width 0.1 R and sits in a box of 20 × 10 × 10 R. The velocity is zero inside 1.3 R and equal to the wind velocity outside. Each code keeps its own pressure initialization, boundaries, tracers, particle kernels and time stepping, and its report documents them.

The cloud crushing time is t<sub>cc</sub> = √χ R / v<sub>wind</sub>. Dense gas is gas with ρ > ρ<sub>c,0</sub> / 3, and its mass is divided by the measured starting dense mass of the same run.

In the September 2026 velocity setup study each code ran in pairs: one run with the sharp velocity edge above and one with the earlier velocity law of that code, a tanh edge or, for AthenaPK, constant momentum outside the cloud. Everything else stayed fixed within a pair.

## From output to figures and 3D

1. The native solver evolves the gas and saves 3D states, logs and restart data.
2. Native readers and yt load the fields and times. Checks confirm the dimensions, starting conditions, finite and positive fields and the diagnostics.
3. The analysis makes the dense mass histories and the resolution overlays.
4. Column density pictures, surface meshes and films are made from every saved state. Particle and moving mesh runs are placed on the same grid as the grid codes for display.
5. The browser shows the meshes with three.js and plays the default version of every film in the library at 60 frames per second, cross fading between saved states. Every frame prints its time.

Example layout, with the actual file names depending on the code:

```text
run/
  native-input                   Physical and numerical parameters
  run.log                        Solver output
  DD0000/CW_0000                 Enzo state metadata
  DD0000/CW_0000.cpu0000         Native HDF5 fields (rank layout varies)
  DD0001/...                     Next saved state
  result.json                    Checks and provenance
  resources.jsonl                Sampled resource use
analysis/
  report.json                    Measured diagnostic series
  mass_and_retention.png         Figure
  README.md                      Reading of the results
```

## Reproducing a run

Start from [the study plan](../analysis/sensitivity_20260907/PLAN.md), the report of the code and its pinned inputs and source evidence. The scripts carry machine specific paths and need the simulation codes installed separately. Build and run in a new directory, keep double precision and the same numerical settings, and check that the storage holds the whole run before it starts. A compressed archive is restored and checked before any workflow relies on it.

## Reading the levels

Resolution levels count cells across the box, not film pixels: level 5 is 256 × 128 × 128 and level 6 is 512 × 256 × 256. For the moving mesh and particle methods the level gives the starting sampling, and their spatial resolution follows the gas as it evolves.
