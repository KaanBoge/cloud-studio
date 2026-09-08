# Force-order trace infrastructure checks

8 September 2026. The binary trace transport and independent arithmetic replay
pass their synthetic tests. **They are not yet integrated into Gasoline.**
No native solver was built or launched, no simulation frame was added, and
the failed trajectory/field-equivalence gate remains unchanged.

## Completed checks

The C transport compiled with GNU89/O3 and warnings treated as errors. It
records initialized 128-byte events with explicit phase, rank, native time,
target, role, cache lifetime, component and exact floating-point bit patterns.
It preserves caller-provided records, refuses existing files, enforces the
fixed byte limit and writes buffered events outside the observed phase.

A 47-record synthetic C trace passed the independent Python reader. A separate
deliberately overflowed C trace remained saved and was correctly rejected as
incomplete. Neither file is a simulation state or a native force measurement.

Fifteen Python tests pass. They cover exact addition/subtraction and factor
replay, signed zero, reordered identical contributions, changed contribution
values, owner versus cache initialization, cache lifetimes, inactive targets,
missing events, malformed fields, nonfinite values, truncated files and
cross-worker owner coverage. An idle rank may own no selected targets; the
two streams together must contain each of the seven selected owners exactly
once per matching phase. The reader does not silently assume that owner
accelerations were cleared by the pressure initializer.

The synthetic order example distinguishes different results caused by the
same contributions in different orders from different input contributions.
This tests the diagnostic decision logic; it is NOT evidence that this
mechanism caused the existing Gasoline trajectory differences.

## Evidence and boundaries

Completed frozen stage:
`/home/kaan/sensitivity_20260907/gasoline/force_trace_core_v1`.
Plan SHA256:
`1b35716e8d781253aeff19bc61f826065593cfde3192a6a41982e3d1df77ea2a`.
Report SHA256:
`69100849bf2cd4423d6f91bfcf82e887a87bff62bc1ffa4719ad8118eed772cb`.
The combined compile/test/check stage took 0.334 seconds and held 63,101 bytes
of artifacts before its report. Those are synthetic-test measurements, not
simulation runtime or hardware-scaling results. The retained native executable
and reviewed force source hashes were unchanged before and after the tests.

The custom source copies and report are local, not yet published. The existing
published serial-output diagnostic and its publication proof are unchanged.
Do not relaunch the completed core stage or edit its frozen files.

Next: implement and review native insertion points, cache/owner lifetime
tracking and a guarded three-case runner under FORCE_ORDER_TRACE_DESIGN.md.
The transport header requires fully initialized records and explicit error
handling from that adapter. The replay cannot certify source coverage,
compiler contraction/rounding, outgoing-cache packets or instrumentation
effects by itself. Freeze and test the native adapter before any new trace.

There are still 46 accepted full controls and eight pending L3/L4 controls,
plus separately held higher levels. No viewer entry or acceptance rule changed.
