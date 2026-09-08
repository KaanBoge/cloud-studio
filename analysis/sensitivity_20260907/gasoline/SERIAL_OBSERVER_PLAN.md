# Prospective native serial-output observation diagnostic

8 September 2026. One new short historical-law L3 diagnostic, not a full
control or an attempt to rerun the old field gate until it passes.

## Question and hypothesis

The initialized output hook calls Gasoline's serial writer, which writes the
master's particles, swaps a remote worker's particles into that buffer, writes
them, then swaps the original particles back. Does this operation change any
of the live particle-record bytes or the checked local particle counts?

Read-only source inspection of pkdWriteTipsy and the selected VecType branches
finds local temporary casts/returns for the TIPSY, iOrder, pressure and smoothing
length outputs. The HI/HeI/HeII output accessors and swap implementation also
need verification before execution. This check addresses a possible direct
data mutation, not the separate arrival-order force-accumulation hypothesis.

## Fixed design

Copy native_retained into a new isolated serial_observer_native_v1 tree.
Only master.c/master.o and the newly linked executable may change; a new custom
header implements read-only byte comparisons. All other copied object hashes,
including all force, density, communication and time-integration objects, must
remain identical. Do not change compiler flags, arithmetic or precision.

Instrument only msrOneNodeWriteOutputs for the exact `state.initial` filename
when GASOLINE_CLOUD_SERIAL_AUDIT=1. Capture the master's original live particle
array, compare it after its own write, compare each remote array immediately
before/after writing, and compare the original array again after swap-back.
Compare all live record bytes (including padding) and nLocal/nActive/nTreeActive/
nSmoothActive/nStore. Do not interpret a padding-only failure as physical change.
Do not write new particle fields or modify the native writer/swap statements.

Use the already pinned historical IC and retained-on two-worker input. Change
only total steps120 to6; keep output interval6, checkpoint interval60, original
dDelta, all physics/numerics and original two MPI workers. Enable the existing
initialized-output/checkpoint-retention options and the new observer. Preserve
both actual initialized and step6 native states, all sidecars, logs and any
native checkpoints. No original repeat or sharp-law experiment is added here.

## Prospective checks

Synthetic C tests must distinguish unchanged buffers, one changed byte, and
changed count metadata without changing either input. Python tests must reject
bad marker populations, unequal payloads, input mismatches and existing output
targets. Freeze all custom scripts, tests, protocol, build hashes and the input
before the diagnostic is launched.

Require a zero native exit, exactly one native initialized-output marker,
exactly three audit records (master written, remote written, master restored),
65536 particles across the first two records, restored master count, and
byte/count equality in every record. Require the two real TIPSY outputs at
their actual times, positive finite stored fields, exact IC recovery where
appropriate at initialization, independent yt mass sums, and unchanged inputs
and binaries. Any failure remains evidence; do not relax the check or retry
unchanged. Passing says only that these observed buffers/counts were restored.
It does NOT prove all process state, caches, timing, MPI order or trajectories
are unaffected, and it does not clear the existing one-spacing field failure.

## Resource and retention boundaries

One GiB total scratch allowance plus independent10 GiB guest/backing-drive
reserves. At most two live-array copies (under54 MiB even with extreme rank
imbalance); require12 GiB available RAM before launch and2 GiB while running.
Take both benchmark and production locks. No competing heavy build/solver.
Build one object at a time with the existing MPI/O3 recipe, nice19 and at most
two build workers. Native wall cap60 seconds; on a guard write the native STOP
request, wait a bounded grace period, then signal only the verified owned group.
No automatic resume, cleanup, deletion, resource saturation or extra repetitions.
