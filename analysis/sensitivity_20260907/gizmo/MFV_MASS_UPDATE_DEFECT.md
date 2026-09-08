# MFV flux-timestep defect: confirmed source bug, isolated repair test pending

8 September 2026. The native MFV routine uses a local timestep variable before
initializing it. GCC confirms the warning. The retained terminal state also
shows that every particle's conserved mass still equals its initial mass,
despite nonzero instantaneous mass fluxes in all particles.

This is a new finding beyond the [previous export-zero diagnosis](MFV_RESTART_DIAGNOSIS.md).
No simulation was run, solver replaced, floor changed or native file deleted.
The two failed MFV controls remain excluded; the accepted total is still44.

## Source and compiler evidence

The [original native source at the pinned commit](https://github.com/pfhopkins/gizmo-public/blob/a828c4ba79d67093bd1a3d04f6f90b5d2d94d65f/hydro/hydro_evaluate.h)
declares `dt_hydrostep_i` but does not assign it. It is subsequently used to
integrate MFV mass flux. A separate `local.dt_hydrostep_i` field is populated
by `particle2in_hydra` and used in neighbor-step comparisons. Those are different
variables. This is not a newly introduced velocity-profile change.

The inspected hydro/update files are byte-identical to tracked source at commit
`a828c4ba79d67093bd1a3d04f6f90b5d2d94d65f`, not modified working-tree copies.
A warning-only compiler check reports the uninitialized use at
`hydro/hydro_evaluate.h:375:24`. Assembly output went to `/dev/null` under both
shared locks. No object or executable was produced or replaced. Other unrelated
warnings were not treated as a diagnosis; the exact relevant warning and source
hashes are in the report.

## Measured terminal inconsistency

The new reader selects additional mass-update fields from the same exact MFV
executable's DWARF, checks matching layouts, and reads the16 retained final
restart files. Their hashes and endpoint match the previous independent audit.

| At 5 t_cc, per case | Sharp | Historical tanh |
| --- | ---: | ---: |
| Particles checked | 65536 | 65536 |
| Conserved mass differs from original IC | 0 | 0 |
| Nonzero accumulated mass increments, dMass | 0 | 0 |
| Nonzero instantaneous mass derivatives, DtMass | 65536 | 65536 |
| Largest absolute mass derivative | 4.25708 | 4.41576 |

The final predicted masses also equal conserved masses. Intermediate native
snapshots show changing predicted masses for the four thermal-failure IDs.
That distinction matters: varying exported predicted mass is not evidence that
the conserved mass was successfully advanced. We do not reconstruct unrecorded
conserved-mass histories from those snapshots.

The native energy update includes terms involving mass flux. Leaving conserved
mass unchanged while using those fluxes elsewhere is a concrete consistency
problem. The uninitialized timestep is a strong candidate for that failure,
but a corrected/unmodified isolated test is still needed to establish the causal
effect and assess whether any additional energy problem remains. No assertion
is made that an uninitialized C variable always evaluates to zero on every build.

## Thermal limiter evidence and limits

For the four terminal-zero IDs, the saved energy derivative is negative even
though conserved energy is tiny and positive. Using just one native clock
quantum, about1.67964e-17 code time, would make the unconstrained energy update
negative in all four. The source's half-energy limiter would then intervene.
This is a clearly labeled counterfactual endpoint calculation, not an executed
next timestep or proof of every previous limiter decision.

The saved energy first falls below1e-10 while still positive at about3.70t_cc
(sharp ID109),4.15(ID96),3.85(ID99),4.75(ID102). That threshold simply locates
the decline; it is not a new scientific acceptance cutoff. Every original time
and scalar in the existing histories remains unchanged.

Four regression tests check mass-array consistency, distinguish real conserved
changes from predicted changes, reject invalid inputs, and test the endpoint
limiter calculation. The diagnostic is ready to share **with these caveats**;
MFV science evolution is not certified. MFM lacks this integrated MFV mass-flux
path, but shared optional code paths still need explicit review before claiming
that every MFM configuration is unaffected. No existing MFM result was rerun or
reclassified on assumption alone.

## Files and next action

[Measured trace](mfv_mass_update_trace_v1.json),
[read-only checker](trace_mfv_mass_update.py), [tests](test_mfv_mass_update.py),
and [prospective repair-validation plan](MFV_TIMESTEP_REPAIR_PLAN.md).

The checker requires the existing local MFV binary, raw restarts, ICs and pinned
previous reports. It refuses an existing output report. Do not rerun it into
`mfv_mass_update_trace_v1.json`. The public package is not a raw-data backup.
The repair plan is preparation, not evidence that a corrected run has finished.
