# Correction to the diagnostic clock audit

The completed 101-frame diagnostic is retained unchanged. Its first validation
report passed every snapshot, independent mass sum and initial nonvelocity
comparison, but stopped before terminal mass accounting because the custom
checker incorrectly assumed GIZMO used its optional 29-bit clock.

The pinned native allvars.h automatically defines LONG_INTEGER_TIME at lines
57-58, selecting TIMEBINS=60 at lines 922-925. init.c sets Timebase_interval
to (TimeMax-TimeBegin)/TIMEBASE. The corrected read-only audit requires the
exact binary's Ti_Current type to be eight bytes, the source-defined 60-bit
span, and every retained restart's clock interval to match that formula.
It reconstructs the same repeated-addition output schedule using 60 bits.

The original cadence allowance (two ticks plus eight endpoint epsilons)
becomes stricter with the correct clock, not looser. The saved times are not
rewritten. All 101 raw hashes, direct scalar sums and energy checks are
rechecked; their independent yt checks remain recorded in the first report.
Original headers are checked against the same corrected schedule too.

Terminal mass accounting uses the unchanged prospective mass_account function
from the frozen onset runner, including its K<=32768 envelope and engineering
allowance. No positivity limit, physical/numerical parameter, native output,
run or completed report is changed. This review is a separate immutable
artifact, not a rerun or replacement of the failed audit.

The original plan, runner and needs_review report remain as evidence of this
checker error. Future launchers must use the source-validated native clock.
This corrected diagnostic still does not accept a two-law science pair.

The first read-only review passed its numerical checks, then failed while
serializing a NumPy boolean in mass_account.response_detected. Its partial
report, tests and source remain under onset_review_v1. Version 2 converts
NumPy report scalars to their equivalent Python scalar types, adds a JSON
regression test, and writes a new onset_review_v2/report.json. This fixes
report serialization only; numerical checks and native data are unchanged.
