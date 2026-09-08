# Prospective MFV late-onset diagnostic

8 September 2026, before the new native run. This is a repaired historical-law
Level 3 diagnostic, not a newly accepted velocity pair or a Level 4 launch.

## Unchanged native experiment

Copy the retained `runs/L3_mfv_tanh13/ics.hdf5` and `params.txt` byte-for-byte
into a new `mfv_timestep_repair_v1/onset_native_v1` directory. Use the already
pinned repaired executable, eight MPI ranks, one thread per rank, and the
original sampling, periodic boundaries, CFL/timestep settings, floors, build
precision and physics. No new instrumentation or solver rebuild is needed.

The actual schedule comes from those parameters: code time 0 to
19.364916731037084, interval 0.19364916731037085, corresponding to 0 through
5 t_cc at chi100/Mach2. Both actual and normalized schedules are recorded
explicitly. The old stored-energy failure began at 3.95 t_cc; testing only
earlier frames would not answer whether it remains. Keep every native frame.

The original historical case took 127.96 seconds and 3249 synchronization
steps. Use a 600-second external wall cap, below the unchanged 3600-second
native periodic-restart interval. The native stop/checkpoint request gets
30 seconds, then TERM/5 seconds/KILL only for the owned process group. No
automatic restart or deletion. Hold both shared study locks. Require 12 GiB
available RAM before launch, 2 GiB live, and separate 10 GiB storage reserves
on guest and host. Budget 104 measured snapshots, three eight-rank restart
sets, the IC and 256 MiB logs, with 25% additional margin. This single new
diagnostic is all that is enabled; any future pair needs its own full budget.

## Predeclared validation

Check every saved state for original field schema, particle IDs/count, finite
fields and positive density, mass, internal energy and smoothing length.
Record failures and continue auditing later files; do not discard failed
times. Compare initial nonvelocity fields exactly with the retained original
full run. Velocities are staggered and not certified as header-synchronous.

Derive requested output times from native parameters. The original run.c
adds the interval repeatedly, truncates onto its 29-bit clock, and adds a
terminal dump if needed. Require complete nondecreasing actual times and
coverage of every source-derived scheduled time within two native clock
ticks plus eight double epsilons times the endpoint. This is a clock-scale
cadence check, not permission to retime frames. Preserve extra terminal
states and record all actual headers. Check this rule on retained original
headers before the new run; do not change it after new output is inspected.

Independently read all native frames with yt and compare raw total/dense mass
sums with direct HDF5 aggregation (relative bound 1e-11, as in the short
test). Dense selection remains rho > original cloud density/3; keep the
original initial denominator. Report full energy minima, low quantiles,
nonpositive counts, and the four previously affected particle IDs. These
histories are descriptive; no post-hoc thermal significance threshold.

Decode every terminal restart prefix with the exact executable's DWARF and
cross-check MassTrue by explicit struct offsets. Report positive/finite
internal conserved and predicted energy, density, pressure and mass. Sum
MassTrue plus pending dMass, not float32 predicted snapshot masses. Check
the terminal time and native 29-bit clock against the input schedule.

Prospectively extend the short test's engineering accumulation model to
0 <= K <= 32768 synchronization steps, just over ten times the original
3249 steps. With u=2^-53, n=32*N*(K+1), use gamma_n=n*u/(1-n*u) and allowance
gamma_n times the sum of absolute initial mass, terminal MassTrue and dMass.
Require n*u<0.01. Compute the residual with math.fsum over individual terms.
Require a conserved per-particle mass response exceeding 32 float64 epsilons
times the largest initial particle mass. This is an engineering ledger check,
not a rigorous arbitrary-flux error bound or scientific-accuracy tolerance.
An out-of-envelope K or failed check remains a failure, not a relaxed gate.

Freeze scripts, dependencies, plan, input and executable hashes and pass
unit tests before native launch. Preserve all evidence. Even a pass here
does not validate both velocity laws, finer resolution, simultaneous saved
velocities, matched cross-code pressure/boundaries, cooling or tracking.
