# Faster corrected 3D runs on Kaan's simulation PC

**Current profile update:** [the second performance pass](../performance_20260907b/README.md)
adds LTO/128x64x32 work blocks for CPU L5 (6.2% additional measured time reduction)
and lossless snapshot compression level 1 for GPU L6 (12.4% in the output-including
test). CPU L6 retains the first-pass profile. The measurements below describe the
first pass, not a cumulative or full-run speedup guarantee.

The new settings reduced measured runtime without lowering the grid resolution,
output precision, reconstruction order or physics. These are **short tests**, not
completed replacement production runs or a promise of the same speedup for days of
turbulent evolution. No production data was deleted and no full campaign was started.

## Measured results, 7 September 2026

| Native solver | Grid, streamwise first | Before | After | Measurement |
|---|---|---:|---:|---|
| Athena++ L5 | 256 x 128 x 128 | 9.04 s | 7.66 s | 15.3% less wall time; medians of 3 tests each |
| Athena++ L6 | 512 x 256 x 256 | 47.03 s | 38.40 s | 18.4% less wall time; one test each |
| AthenaPK L5 | 256 x 128 x 128 | 5.01 s | 3.51 s | 30.0% less wall time; medians of 3 tests each |
| AthenaPK L6 | 512 x 256 x 256 | 20.94 s | 20.32 s | Similar speed; one test each, safer memory use |

Times include initialization and two native output writes. Every test used chi=100,
Mach 2, the corrected sharp velocity boundary at 1.3 R, the same density profile,
HLLC/PLM/VL2/CFL=0.4 and double precision within each code. End time was 0.25 code
units at L5 or 0.08 at L6, **not** 5 cloud-crushing times. Test output count is two;
the production input still requests 101 times at intervals of 0.05 t_cc through 5 t_cc.

CPU changes: separate `-O3 -march=native -fno-fast-math -ffp-contract=off` build,
64-cell blocks, 16 MPI ranks explicitly bound to hardware threads. The original
binary was not overwritten. Its three independent native IC checks at chi=10,
100,1000 also passed.

GPU changes: the same corrected AthenaPK executable, 64-cell blocks at L5,
128-cell blocks at L6. L6 device-wide sampled VRAM fell from 15.3 to 12.8 GiB
between the 64/128-block tests. Background graphics use differed; subtracting the
initial readings gives about 2.2 GiB less incremental use. The 32-cell-block L6
configuration stalled at initialization near VRAM capacity. This is evidence of
a configuration problem, not proof that every level-6 simulation is impossible.

All native cells of the final test snapshots were compared, including density,
pressure, all velocity components and the native tracer. Nine comparison pairs
passed a scaled maximum difference tolerance of 1e-10. In these short tests the
hydrodynamic saved fields agreed exactly; CPU tracer differences were at most
4.24e-22 on that scale. This does not guarantee bitwise identity over long chaotic
evolution, convergence, or matching tracer definitions between different codes.

`performance_report.json` preserves timing records, memory samples, hashes and
excluded probes. Two 128-block attempts accidentally overlapped a stalled probe;
they were excluded and repeated alone. The benchmark now has an exclusive lock.
The initial MPI listener failure is also retained rather than hidden.

## Do the simulations need to be repeated?

Not automatically every simulation. An analysis or plotting error can be corrected
using intact native snapshots. A completed run with verified matching initial
conditions and numerical controls can be reused. A change to the initial velocity
is different: the flow must evolve again from the corrected initial state, not from
an evolved checkpoint or a relabelled movie.

The preserved t=0 samples in `ATHPP3D_chi10_256` and `ATHPP3D_chi100_256` match the
old velocity tanh centred on the density edge. The `M3D_L3_chi10/100/1000` AthenaPK
samples match the old constant-exterior-momentum prescription. Both are incompatible
with the corrected constant-exterior-velocity prescription. The sampling rejects
these cases; a passing ray would not certify an entire IC. Several other directories
retain only final snapshots, so they remain unclassified rather than presumed bad.

The existing results remain useful as labelled historical or exploratory results.
We cannot yet claim a clean twelve-code comparison with only the solver changing.
Boundary-condition and tracer differences, particle resolution conventions, missing
native data and unvalidated cooling/frame-shifting variants remain separate issues.
Changing source code today does not alter a run that already finished.

To reduce reruns, first establish a verified common L5 baseline across codes for
chi=10/100/1000, reuse every compatible result, and add L6 convergence cases after
that. Keep the native snapshots needed for mass evolution and future analysis.
MP4s and quantized viewer meshes are not lossless archives of those fields.

## Files and local usage

Windows working directory: `C:\Users\kaanb\CloudCrushing\performance_20260907`.
Native binaries and benchmark output: `/home/kaan/performance_20260907` in WSL.

`run_optimized.py` prepares one fresh, versioned production directory. It does not
run anything without `--run`. This release enables only the two solvers and levels
actually benchmarked here; it does not pretend to optimize all twelve codes.

```bash
/home/kaan/venv/bin/python /mnt/c/Users/kaanb/CloudCrushing/performance_20260907/run_optimized.py --code athpp --level 5 --chi 10
```

After preparation, the explicit launch command for that same untouched directory is:

```bash
/home/kaan/venv/bin/python /mnt/c/Users/kaanb/CloudCrushing/performance_20260907/run_optimized.py --code athpp --level 5 --chi 10 --resume-prepared --run
```

Use `apk` for AthenaPK. Directories use `OPT_` for unchanged first-pass profiles,
`OPTLTO_` for the new CPU L5 profile, or `OPTIO1_` for the new GPU L6 profile,
followed by `sharp13_20260907_L{level}_chi{chi}`
under the corresponding native solver's `runs` directory. They contain `athinput`
and `provenance.json` before launch. A launched run adds `run.log`, native `.athdf`
or `.phdf` snapshots and restart files. Inputs print the physical parameters read
back from the file. Profiles pin executable hashes and native IC-test evidence.

The launcher will not overwrite an existing run or treat an interrupted run as
merely prepared. Checkpoint recovery is a separate procedure. Its exclusive lock
prevents two of these high-resource production jobs from competing on this PC;
it cannot lock unrelated software or historical queue scripts.

Twelve production inputs (two codes, two levels, three chi values) have been
prepared without launching them. Thirteen launcher tests and two native output/restart
write smoke tests pass. The smoke tests do not establish checkpoint-read recovery.

Disk/RAM/VRAM are checked before execution. Disk reservation includes all 101
double-precision snapshots, possible extra terminal output, retained checkpoints
and headroom. It uses uncompressed sizes, not the unusually good compression of
nearly uniform initial fields. Both L6 profiles reserve about 236 GiB.
The follow-up audit checks both guest space and the actual Windows backing volume,
which had only about 35.6 GiB free, plus a 10 GiB safety reserve requirement.
L5 reserves about 38 GiB. Both large launches therefore refuse under this
conservative growth budget. Nothing is deleted to force a run to fit.
Using 100% of RAM or filling the SSD is not a speed optimization.

101 is a target until measured native times are checked. A successful solver exit
alone is not a completed scientific result. The launcher marks missing or off-time
output for review, retains duplicate terminal files and never invents frames.
Even a cadence pass still leaves full-run physics validation pending.

## Reproduce the evidence

`build_cpu.sh`, `benchmark.py`, `compare_fields.py`, `verify_native_cpu.py` and
`summarize.py` build, time and validate the profiles. `test_optimized.py` checks
launcher inputs and safeguards. They require this PC's compiled code checkouts,
WSL Python environment, verified analysis modules and preserved audit evidence.
They are not self-contained substitutes for the native simulation codes.

The old `run_corrected_athpp.py` is still available as a baseline. No existing
historical queue was silently restarted or rewired to the new profile.
