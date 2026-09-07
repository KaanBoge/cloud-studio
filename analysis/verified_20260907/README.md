# Cloud comparison verification, 7 September 2026

Status: initial-condition and analysis corrections verified. This is not a
claim that previous production runs are matched or that the campaign is complete.

Later follow-up: see [repair and tracking/cooling audit](../followup_20260907/README.md).
It adds 42 regression tests, native frame-tracking evidence, host-volume storage
guards and the finding that the historical cooling-labelled runs did not enable cooling.

24 native-grid initial-output checks passed (eight solvers, three chi values),
plus 12 particle-generator IC checks. Native mass diagnostics were exercised on
21 short grid runs. Ten Python unit tests passed, the viewer's diagnostic gate
was tested, two figure pipelines rendered, and the new mesh exporter retained
both measured snapshots of its short test without repeating or inventing times.

The evidence directory contains inputs, native solver logs, JSON verification
results and source/binary hashes. Original changed sources and scripts are in
before/. Test native fields remain at /home/kaan/ic_audit_20260907 in WSL.

See ANALYSIS_README.md for process, directory contents, script usage, scope and
remaining limitations. In particular, particle boundaries, tracer definitions,
production reruns, cooling and Galilean tracking still need validation. No large
production run was started in this audit; a corrected L3 Athena++ input was
prepared only. Old raw-data cleanup was disabled. No native data was deleted.

No production results should be overwritten or deleted by the verification work.
The velocity prescription under review is zero within 1.3 cloud radii and the
constant wind velocity outside; the density keeps the existing tanh profile.

Reference: Gronnow et al. (2018), section 2,
https://arxiv.org/pdf/1805.03903 . This reference uses a sharp velocity boundary;
it does not support a tanh velocity profile.
