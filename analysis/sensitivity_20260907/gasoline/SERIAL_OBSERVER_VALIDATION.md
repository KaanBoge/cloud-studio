# Gasoline serial-output buffer test

8 September 2026. **The observed particle buffers and count metadata were
unchanged across the initialized writing operations.** The master's original
buffer was restored exactly after swapping particles back. This excludes direct
mutation in the observed portions of this instrumented serial writer. It does
not prove that output timing, MPI/cache order or later trajectories are unaffected.
The existing failed field-equivalence criterion remains failed. No full Gasoline
control is enabled, and the accepted study total remains 46.

## What was tested

One short historical-law L3 diagnostic used the original two MPI workers,
65,536 particles, chi = 100, Mach = 2 and unchanged native numerics. Only its
duration was shortened from 120 to six original-size steps; output interval 6
and checkpoint interval 60 were preserved. Existing initialized-output and
checkpoint-retention options were enabled, with an additional passive observer.

The [original protocol](SERIAL_OBSERVER_PLAN.md) and
[preparation correction](SERIAL_OBSERVER_PLAN_V2.md) were frozen before the
successful version2 run. The instrumented master routine copied live particle
bytes before writing, compared them afterwards, and compared the original
master array after swap-back. The test compares complete live records, including
padding, plus nLocal, nActive, nTreeActive, nSmoothActive and nStore.

| Observed operation | Particles | Bytes compared | Byte/count equality |
| --- | ---: | ---: | --- |
| Master array before/after its write | 32,768 | 13,369,344 | Exact |
| Hosted remote array before/after its write | 32,768 | 13,369,344 | Exact |
| Original master array after swap-back | 32,768 | 13,369,344 | Exact |

The remote subset is checked while hosted on the master. The remote worker's
own buffer after receiving it back was not separately captured. These records
therefore must not be expanded into an all-process-state equivalence claim.

## Native outputs and resources

The solver finished in **3.064 seconds**, using a median **1.959 busy CPU workers**
out of the requested two. Peak summed solver-child RSS was **123.17 MiB**
(129,150,976 bytes). No GPU was used and no resource guard fired. These are
diagnostic process measurements, not a full-run performance forecast.

It saved **two actual native states**, at code times 0 and 0.19364916732
(approximately 0 and 0.05 t_cc), with all native sidecars retained. Initial
position, velocity, mass, stored energy and metals exactly recover the pinned IC.
Both TIPSY states have finite fields and positive mass/density/energy/softening.
Independent yt raw-field total and dense mass sums agree exactly: 2425.245532028377
and 409.90798234939575 in both states. No resampled or synthetic frame was added.

The final checkpoint `state.step000000006.chk` has native finalized valid=1,
version8, 65,536 gas particles, step6 and the correct time. Its length matches
the native 120-byte particle stride and header offset. SHA256:
`2dafe8b46895fb290a71dfc66913a680ef351f4722209c97a70b5efcbdf9fc94`.
This is a retained-file/header check, not checkpoint-resume validation.

## Build, tests and failed preparation retained

Only the new copy's `master.o` and linked executable changed; all other source
files and object hashes match the retained build, apart from the explicitly
instrumented master source and added observer header. Existing MPI/O3 flags
were kept. The master translation unit was recompiled, so matching other
objects is not a proof of zero instrumentation effect on execution.
New diagnostic binary SHA256:
`2b9ae839d0c5d6fd45edfa9ef69322d1b3d913018f8512e6c012a60095867545`.
No canonical solver or earlier experiment was modified.

Five Python tests and a C synthetic test program passed. They cover byte and
metadata changes, preservation, malformed marker populations, exact native
filename forms, checkpoint-environment requirements and exclusive output files.
The [frozen plan](serial_observer_plan_v2.json) has SHA256
`5c383a4772b36252bf8edf79ef66affea3a4e67b74973df66146d416c07d9c79`.
The [result](serial_observer_result_v2.json) has SHA256
`bd196f0028d551e22cfbbfe6673c85d8ba29cb51f236719b04dbfd7ba83057af`.

The first preparation attempt did not activate the observer because the native
filename was `./state.initial`, not the unprefixed name its guard expected. Its
launcher also missed the original checkpoint-schema environment setting. It
completed six steps and saved two TIPSY states, but no checkpoint or observer
records. The checker correctly failed. Its [failure record](serial_observer_v1_failure.json)
and [native execution measurements](serial_observer_v1_native_result.json), plus
all local raw files, scripts and binaries, remain preserved. The corrected test
used new folders; no failed record was overwritten or declared successful.

Native folders under `/home/kaan/sensitivity_20260907/gasoline`:
`serial_observer_native_v1`, `serial_observer_runner_v1`, `serial_observer_case_v1`
and their separate version2 counterparts. Selected custom files here are
[the guarded launcher](serial_observer_run_v2.py), [Python tests](test_serial_observer_run_v2.py),
[byte observer](serial_observer_v2.h) and [C tests](test_serial_observer_v2.c).
They depend on the recorded local native workspace and are not standalone solver
distributions. Do not relaunch either completed/failed stage.

Next: a separately planned force/energy order trace, if it can distinguish the
remaining mechanisms. The direct buffer-mutation candidate is narrower now;
the existing original-repeat and output-observation trajectory differences are
still unresolved. No tolerance adjustment or new full control follows from this
buffer test alone.
