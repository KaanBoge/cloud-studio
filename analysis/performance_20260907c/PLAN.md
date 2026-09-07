# Performance and storage follow-up

## Verified starting state

The six corrected L4 and six corrected L3 runs finished for Athena++ and
AthenaPK at Mach 2 and chi 10, 100, 1000. Each has 101 distinct native times
through 5 t_cc, finite fields, positive density/pressure, and a passing full
initial-condition check. Their measured intermediate times are not exact
uniform samples. These checks do not certify all-code scientific comparability.

The 12 prepared L5/L6 runs are storage-held. No production solver is running
while the separate, small performance probes execute. No cooling/tracking
variant is enabled, and no existing raw snapshot is deleted.

## Saved campaign scope

The August notes identify 12 code families, with GIZMO MFM and MFV treated as
two methods. Across levels 1 through 6 and three density contrasts this is
234 baseline configurations. This is a requested matrix, not 234 validated
launch commands or a demand to repeat compatible historical runs.

`campaign_inventory.json` distinguishes the 12 new native-checked results,
the 12 storage-held jobs, and configurations requiring reuse/launcher/physics
audits. Mach variants, common late-time figures, resolution-dependent mass
curves, tracking, radiative cooling, MHD, and full-frame visualization are
separate tasks with explicit validation prerequisites.

## Test plan

1. Compare 16 and 8 CPU ranks with the same LTO binary, L5 grid, work blocks,
   double precision, input physics and requested endpoint. Three alternating
   pairs, including initialization, two complete outputs and disk flush.
2. Compare GPU HDF5 compression levels 5 and 1 on the same L5 case. Three
   alternating pairs. Compare every numeric saved dataset exactly.
3. Reject numerical mismatches and candidates without a repeatable timing
   improvement. Do not extrapolate these short tests to universal speedups.
4. Audit deletion candidates separately. Published MP4/mesh assets are lossy
   visualizations, not backups of density, velocity, energy, tracer or restarts.
   Keep raw fields, parameters, source versions and logs.

## Hardware warning

Windows recorded several bugchecks today, including 0xA and 0x3B. The user's
reported "46" message has not yet been identified; no causal attribution to
RAM exhaustion, a driver, or faulty hardware has been established. Both 16 GiB
RAM modules are enumerated. Do not attempt to manufacture lag or exhaust RAM.
No BIOS, paging, power, driver or hardware settings are changed by this work.
