# Prospective MFV timestep repair validation

Written8 September2026, before changing or running a repaired solver.
Status: planned, not executed. The source defect and retained-state measurements
are in [MFV_MASS_UPDATE_DEFECT.md](MFV_MASS_UPDATE_DEFECT.md).

## Scope and single candidate change

Use an isolated copy of the pinned native source/configuration. Populate the
local `dt_hydrostep_i` from the already supplied `local.dt_hydrostep_i` after
both local/imported input paths have populated `local`, before its first use.
Do not modify the canonical source or original binaries. Do not change CFL,
floors, output precision, FTZ/compiler options, sampling, boundaries or physics.
This changes a defective solver update; it is not a performance-only change.

## Gates before any native run

1. Review the precise native diff and verify that only this assignment changes.
   Verify populated input timesteps for local and imported neighbor paths.
2. Compile an isolated unmodified reference and repaired MFV with the same
   recorded toolchain/options; retain source/binary/config hashes and logs.
   The relevant uninitialized-variable warning must disappear in the repaired
   path. Any unrelated source/ABI/precision change stops the test.
3. Check which uses survive preprocessing in the existing MFM configuration.
   Do not assume all MFM modes are unaffected or rerun accepted full MFM cases.
4. Use synthetic flux tests: constant/zero flux, positive and negative flux,
   unequal timesteps and local/imported paths. Integrated mass must use the
   target's supplied physical timestep; exchange must be antisymmetric under
   the intended native active-neighbor schedule. These are tests to implement,
   not checks already passed.
5. Pin a fresh runner and output directory, reserve both original and repaired
   full-state diagnostic outputs/restarts/logs plus margins and10GiB on each
   filesystem. Hold both shared locks; no other heavy build/run. Keep the
   original eight MPI ranks and original per-level numerical settings.

## First native diagnostic, deliberately short

At existing chi100/Mach2/L3, run the existing historical IC with the repaired
binary only through the already used short0.1-code-time endpoint. Compare with
the retained original short run and isolated unmodified reference as needed
to separate rebuild effects; do not overwrite or blindly rerun old directories.
Keep output cadence, numerical timestep caps and restart conventions identical
within this diagnostic comparison. Check actual native t=0/nonvelocity state,
all native fields/times, IDs, finite positive density/pressure/energy and
independent raw-field reader sums. Respect native half-kick velocity staging.

Retained restarts must show conserved mass responding to nonzero integrated
flux. Check global mass conservation using double-precision conserved mass,
not solely predicted float32 snapshot mass. Derive the numerical allowance
prospectively from summation and native update precision; do not pick a tolerance
after looking at the result. A source fix alone is not a passing evolution test.

If scalar tracing is needed, first prove that the optional instrumentation does
not change the solver state: use per-rank buffered observations without new
MPI reductions or particle sorting in the hot loop, hook-off/on controls, and
fixed checks declared before running. Log the actual pre/post mass and energy,
flux derivatives, kick duration and limiter branch; no reconstructed branch
history may be called measured. Do not loosen a failed comparison afterward.

## Longer confirmation only after short gates pass

A short run does not reach the observed thermal decline. Only after the above
gates pass, plan a bounded extension covering its onset with sufficient retained
native states and trace data, again in new directories. Establish whether the
mass-update repair prevents the decline and check global mass/energy accounting.
If not, retain that failed evidence and diagnose further; do not add floors or
use an apparently favorable subinterval as a successful full control.

Both velocity laws would eventually need the same repaired executable for a
new accepted MFV sensitivity pair. Existing failed controls remain separate.
No blanket rerun of the44 accepted controls, L4 launch, changed-Mach/cooling
experiment, or production viewer promotion is authorized by this plan alone.
