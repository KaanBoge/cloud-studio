# Short native MFV repair test passed

Later update: the [101-frame late-onset diagnostic](MFV_ONSET_VALIDATION.md)
now passes. The short-test assessment below remains the preceding stage.

8 September 2026. **The repaired native solver now integrates particle mass in
the short test, while conserving the total mass ledger to rounding precision.**
This does not yet establish that the late thermal failure is resolved.
No new full sensitivity control is accepted; the study total remains44.

## Matched diagnostic and results

Two new native cases used the isolated reference and one-assignment repaired
executables from [the build validation](MFV_REPAIR_BUILD_VALIDATION.md).
Both copied the retained historical L3 chi100/Mach2 IC and short parameter file
byte-for-byte. Eight CPU MPI ranks, original numerics, floors, precision,
periodic boundaries, sampling and output settings were unchanged.

Each produced two actual native snapshots at code times0 and0.1, or
0 and0.025819889 t_cc, plus all eight terminal restart files. All four snapshots
passed schema, finite/positive-field and independent yt mass-sum checks, with
zero reported sum discrepancy. The new reference reproduces every array and
time of both retained original short outputs exactly. Repaired initial
nonvelocity arrays match reference exactly. No frame was synthesized or retimed.

| Terminal diagnostic | Reference | Repaired |
| --- | ---: | ---: |
| Particles with changed conserved mass | 0 | 22347 |
| Largest absolute particle-mass change | 0 | 0.09554868 |
| Sum of coupled MassTrue | 2425.24553203 | 2425.15961922 |
| Sum of pending dMass | 0 | 0.08591281 |
| Combined mass ledger | 2425.24553203 | 2425.24553203 |
| Ledger residual versus initial mass | 0 | 1.38364e-14 |
| Native synchronization steps | 8 | 8 |

The native pair loop accumulates opposite transfers in dMass. A kick moves
mass from this pending buffer into MassTrue. At the saved final kick stage,
some transfers remain pending, so the conserved accounting includes BOTH.
The residual is computed over all individual double-precision terms with
math.fsum, rather than subtracting two already rounded displayed totals.
A separate struct-offset sum checks the restart MassTrue decoder. Snapshot
predicted float32 masses are not substituted for the conserved ledger.

The prospective roundoff-scaled allowance was about1.0165e-5 code-mass units;
the measured residual is much smaller. That allowance is an engineering
accumulation check, not a theorem for arbitrary intermediate flux histories,
physical accuracy measurement or a post-hoc significance cutoff. The full
[pre-run protocol](MFV_SHORT_VALIDATION_PLAN.md) states its derivation and limits.

## Resources and preservation

Observed process wall times were1.241s reference and1.164s repaired, including
exit polling/guard overhead. Sampled peak summed child RSS was0.518/0.519 GiB.
These tiny tests are not a performance benchmark or a full-run ETA; CPU duty
percentage was not measured. GPU acceleration was not used by these CPU solvers.

The frozen launcher passed eight tests before launch. Both shared locks,
native RAM checks and separate Windows/WSL storage reserves were used. The
whole two-case budget was0.550 GiB plus10 GiB reserves. Both solvers exited0
without a resource guard. Every IC, raw frame, log and restart remains local;
all four frame hashes and16 restart hashes were rechecked after analysis.
No canonical solver, old executable, old run or completed report was changed.

Native evidence is under
`/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/short_native_v1`.
The frozen launcher is the adjacent `short_runner_v1`. Do not relaunch either
case, refreeze its package or rerun analysis into the completed report.

## Interpretation and next gate

The reference reproduced the retained original output, and the one-line
candidate changes conserved-mass evolution as expected. This supports the
mass-update repair causally in this short diagnostic. It does NOT prove that
every late energy anomaly has the same cause. The old zero-energy failure
started around3.95 t_cc, far later than this0.0258 t_cc test.

The next step is a separately planned, guarded extension reaching that onset,
with unchanged physics and retained native outputs/restarts. Full MFV L3/L4
acceptance and sharp/historical comparison are still pending. These four
diagnostic frames are not four full science runs or production viewer entries.

Snapshot and terminal restart fields can belong to different integration
stages despite equal headers. Saved velocities are staggered; no simultaneous
velocity diagnostic is claimed. yt reads raw fields in code units with an
explicit rectangular box; its reader settings do not change native boundaries.

Files: [validation](mfv_short_validation.json), [native execution ledger](mfv_short_batch.json),
[frozen plan](mfv_short_plan.json), [launcher/analysis](mfv_short_controls.py),
[eight tests](test_mfv_short.py), and [storage helper](storage_guard.py).
The plan's inherited physics object preserves the parent study's5 t_cc target;
the actual short schedule is the pinned parameter file's TimeMax=0.1 and
TimeBetSnapshot=0.1, confirmed by every native header. The scripts are explicitly
for this fixed L3 diagnostic, not universal metadata-free analysis tools.
Public custom scripts require the retained local native data and pinned helpers;
the public package is not a raw simulation backup.
