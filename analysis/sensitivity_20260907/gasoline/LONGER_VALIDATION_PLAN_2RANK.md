# Historical-worker-count addendum, specified before two-worker diagnostics

8 September 2026. The original eight-worker diagnostic failed entering step7:
native pst.c:1254 asserted nHighTot <= nUpperStore. It saved one actual output
at step6, exited134 and used about0.279GiB, without a system-RAM or disk guard.
The initial-output hook and retained-checkpoint hook were both absent. Its
entire attempt and the three unlaunched prepared cases remain untouched.

Source pst.c allocates nStore=nFileTotal+ceil(nFileTotal*dExtraStore) per
partition; dExtraStore=.2 is retained. The domain splitter enforces that
partition capacity. More total free RAM does not expand it automatically.
The MPI missing-help-file message is a secondary error-reporting problem;
the native assertion is the recorded cause of this solver abort.

The saved original L3 chi100 run.out explicitly identifies **two processors**
and ends with Integration complete at19.3649 code time. The historical recipe
therefore has an established two-worker reference, not an established eight-
worker speedup. New isolated diagnostics use two workers for every case,
preserving dExtraStore and every physical/numerical parameter. They compare
the same four original/off/on variants and120 native timesteps as specified
in LONGER_VALIDATION_PLAN.md. All finite-precision criteria, exact dense-mask
requirements, retained outputs/checkpoints and reserve rules remain unchanged.

This change restores the observed historical worker count; it does not loosen
a numerical check, change the failed eight-worker attempt, modify a floor or
patch the domain splitter. It is not a performance benchmark. Both historical
and sharp science controls, if enabled later, must use the same validated
worker count and binary. Eight-worker allocation optimization remains separate
work requiring its own output/scaling checks.

The four new directories are longer_validation_2rank_v1/{original_a,
original_b,retained_off,retained_on}. There is no automatic checkpoint resume
or overwrite of any earlier directory. The original failed exact-equivalence
and eight-worker tests remain failed records, not retroactively passed tests.
