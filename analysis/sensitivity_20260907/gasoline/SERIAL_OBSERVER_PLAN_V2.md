# Serial-output observer: preparation correction

8 September 2026. This addendum is written before the new diagnostic launch.
The scientific question and unchanged byte/count criteria remain those in
[the original protocol](SERIAL_OBSERVER_PLAN.md).

Version1 completed six native steps but produced zero observer records: the
native path is `./state.initial`, while the guard recognized only `state.initial`.
The checker correctly failed. Its launcher also omitted the original
PKDGRAV_CHECKPOINT_FDL environment variable, so the final checkpoint was not
written. Both TIPSY outputs, sidecars, failed checker, binary and source remain
in the version1 folders. This was failed preparation, not a passed test or a
scientific byte-mutation result. Do not resume or rerun those folders.

Version2 uses fresh source/runner/case directories. A tested path predicate
recognizes exactly `state.initial` and `./state.initial`, rejecting other names.
Restore the retained case's checkpoint environment exactly, pin its FDL file
and verify that it exists before launching. Add a required finalized step6
checkpoint/header/hash check and reject the missing-checkpoint warning.

No tolerance, byte/count comparison, worker count, native step size, physics,
output cadence or scientific acceptance scope changes. The planned one new
six-step version2 diagnostic tests the corrected observer; it is not an unchanged
repeat selected to hide a failed numerical comparison. Build only master.o/link
in the new copy with unchanged native flags. Preserve both versions and all raw.
