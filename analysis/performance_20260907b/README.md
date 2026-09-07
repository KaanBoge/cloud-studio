# Second performance pass: faster where measured, not universally

7 September 2026. Two additional optimizations passed native-field checks. The
level-6 CPU candidate was slower and was rejected at that level. No production
run was launched, historical data deleted, or simulation resolution reduced.

## Results relative to the already optimized profiles

| Test | Previous profile | Candidate | Decision |
|---|---:|---:|---|
| Athena++ L5 | 17.89 s | 16.77 s | 6.2% less time; enable only at L5 |
| Athena++ L6 | 108.61 s | 112.97 s | 4.0% slower; keep previous L6 settings |
| AthenaPK L6, output included | 37.74 s | 33.08 s | 12.4% less time; enable lossless compression level 1 for snapshots |

L5 CPU and L6 GPU values are medians of three runs per configuration. CPU L6 has
one run per configuration. These are **short tests**, not completed 5 t_cc science
runs. CPU L5 ends at 0.6 code-time units, CPU L6 at 0.24, GPU L6 at 0.32; all use
chi=100 and Mach 2. Do not compare CPU/GPU timings across these different test
durations or add these percentage reductions to the first report's percentages.

Timings include initialization, two full native snapshots and a disk flush. The
GPU improvement mainly reduces output-encoding work. The saving across a full
production run depends on its output/compute balance and how compressible its
later fields are. The GPU files were 10.9% larger than with compression level 5.
Turning compression off was faster still but consumed 22.6 times as much space
in this test, so it was not selected. Early-time compression ratios are not
used to reduce the conservative production storage reservation.

## Exactly what changes

Athena++ L5 uses a separately built executable with link-time optimization and
128 x 64 x 32 **work blocks**, with 16 MPI ranks. The physical grid remains
256 x 128 x 128 with cubic cells. L6 keeps the prior native build and 64-cubed
work blocks on its 512 x 256 x 256 physical grid. A work block is a subdivision
of a fixed mesh, not a different or fractional simulation level.

The extra compiler flag is `-flto=2`; `-fno-fast-math` and `-ffp-contract=off`
are retained. [GCC's optimization documentation](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
describes the distinction between compiler optimizations and relaxed arithmetic.
The new executable hash is in the timing and native-IC evidence. Existing solver
executables are not overwritten.

AthenaPK L6 adds `hdf5_compression_level = 1` only to
`<parthenon/output1>`, the primitive-field snapshot output. The old value was
the checkout's default of 5. The native executable, double precision, variables,
physics, timestep controls, grid, output schedule and restart settings are
unchanged. See [HDF5's compression documentation](https://support.hdfgroup.org/documentation/hdf5/latest/_comp_t_s.html)
for the storage mechanism; actual decoded-data equality is checked here directly.

## Verification and quality limits

Thirteen full-field comparison pairs passed. For CPU variants, the checker reads
every native cell and compares density, pressure, all velocities and tracer at
the same physical time and grid. The chosen L5 variant's saved fields agreed
exactly with the previous profile in the tested evolution. The new LTO binary
also passed full t=0 IC checks on the real L5 grid at chi=10,100,1000, not just
a ray or a filename check. Those three results are in `lto_ic_results.json`.

For GPU compression, every numeric HDF5 dataset, including all six primitive
fields and mesh coordinates, decoded to exactly the same values. Three independent
comparisons of gzip setting 5 against setting 1 passed. These are compression
settings, not simulation resolution levels. Launcher safeguards pass 13 unit tests.

This preserves the tested numerical results; it does **not** demonstrate better
physical accuracy, full-run convergence, or a universal optimization for all twelve
simulation codes. The slower L6 CPU candidate is a concrete reason to keep profiles
specific to code and resolution. Correct initial conditions, boundary conditions,
comparison times and convergence tests still determine scientific validity.

## Current launch settings and retained data

The guarded launcher and current profiles are in
[`../performance_20260907/`](../performance_20260907/). It remains prepare-only unless
`--run` is explicitly supplied. Three new L5 CPU and three new L6 GPU input directories
are prepared, not completed:

    /home/kaan/codes/athenapp/runs/OPTLTO_sharp13_20260907_L5_chi{10,100,1000}
    /home/kaan/codes/athenapk/runs/OPTIO1_sharp13_20260907_L6_chi{10,100,1000}

The earlier `OPT_...` directories remain intact. The run ID changes so new output
cannot overwrite old data. The production target remains 101 actual snapshot
times through 5 t_cc; actual headers must pass validation before claiming that
target was achieved. Checkpoint compression remains unchanged. No frames were
thinned, repeated or interpolated by this optimization.

The conservative L6 retention reservation is still about 236 GiB. The benchmark
files are retained under `/home/kaan/performance_20260907b/runs`; this experiment
did not free space by deleting scientific data or treating viewer meshes as backups.

## Reproduce or inspect

`build_lto.sh` builds only into separate test object/binary directories.
`bench.py` runs the isolated candidates; `verify.py` compares native fields;
`verify_lto_ic.py` checks the newly built executable; `summarize.py` records the
decisions and updates the opt-in launch profiles only after the checks pass.
These scripts require this PC's WSL checkouts and the verified first-pass modules.

`performance_report.json` records every timing, including the rejected candidates.
The first background build attempts were interrupted, leaving empty object files;
an isolated full rebuild completed successfully in a supervised batch. The log
and failed/interrupted build artifacts remain on disk, separate from production.

For rollback, the earlier profile document is retained as
`profiles_before_io_change.json`. Restore profile configuration deliberately;
never overwrite a run directory or restart evolved data under a changed IC.
