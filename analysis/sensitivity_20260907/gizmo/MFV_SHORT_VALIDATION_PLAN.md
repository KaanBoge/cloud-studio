# Prospective short native MFV repair check

Written 8 September 2026, before either new native evolution case.
This is an additional gate, not a full sensitivity pair or a performance test.

## Cases and output stage

Use the retained historical L3 chi100/Mach2 IC and parameter file from
`smokes/L3_mfv_tanh13`, byte-identically in two NEW directories. The isolated
reference and one-assignment repaired executables are already built and pinned.
Use eight MPI ranks, original MaxSizeTimestep=0.05, MinSizeTimestep=1e-12,
TimeMax=0.1, output interval=0.1 and restart interval=3600 seconds. Change no
physics, precision, floors, compiler flags, sampling or boundary conditions.

Native run.c evaluates initial forces, chooses timesteps, kicks, then enters
the output/drift routine. Snapshot velocities are therefore staggered. The
final scheduled snapshot can precede the final force/kick update even when its
header equals the restart time. Do not require every final snapshot field to
equal the final restart field or call the two integration stages identical.
The reference's saved arrays/times must reproduce the retained original short
case exactly. Report any difference as a failed rebuild-control check, not
silently as the repair's effect. Repaired initial nonvelocity arrays must
match reference; report velocities without asserting header-time synchronization.

## Direct mass accounting

Read double MassTrue, dMass and DtMass from all eight finalized native restart
prefixes using the exact executable's selected DWARF layouts. Check IDs, count,
positive finite density/pressure/energy/mass and common native time. Do not
resume these restarts or claim the unparsed RNG/tree tail was validated.

The source adds opposite pair transfers to dMass. Kick mode1 subtracts a
coupled increment from dMass and adds it to MassTrue; mode0 consumes the
remainder. A terminal restart after mode1 can therefore retain pending flux.
Report sum(MassTrue), sum(dMass), and their combined ledger separately.
The combined ledger should recover initial IC mass; predicted float32 snapshot
mass is NOT the conserved-ledger quantity. No snapshot or native field is changed.

Before seeing results, define a roundoff-scaled smoke gate with double unit
roundoff u=2^-53, N=65536, and K=the native synchronization-step count:
n=32*N*(K+1), gamma_n=n*u/(1-n*u), allowance=gamma_n*S,
where S is initial absolute mass plus final absolute MassTrue and dMass sums.
Require 0<=K<=256, finite positive masses and n*u<0.01. The factor32 is a
conservative accumulation-depth model allowing all-particle neighbor visits,
local/imported reductions and two kicks at each synchronization. This is a
predeclared engineering diagnostic informed by precision and accumulation,
NOT a rigorous error bound for every possible intermediate flux history or
a significance/accuracy threshold for the research comparison. Report the
actual residual and allowance; do not relax this gate after observing output.
Longer validation still requires detailed accounting if this model is inadequate.

Use math.fsum for the residual over all individual positive/negative ledger
terms. Cross-check restart MassTrue with an explicit struct-offset summation.
Require a repaired per-particle conserved-mass change greater than
32*float64_epsilon*maximum initial particle mass. Nonzero DtMass alone is not
evidence that mass has been integrated. All native snapshot fields and actual
times must pass checks; independently sum each snapshot with yt.

## Resource and execution gates

Reserve per case four measured native snapshots, three measured eight-rank
restart sets, an IC and64 MiB logs, plus25% margin. Budget BOTH cases before
launch, in addition to separate10 GiB reserves on WSL and its Windows backing
volume. Require12 GiB RAM before launch and2 GiB while running. Wall cap180s
is below the native3600s periodic restart interval. On a guard failure request
native stop/checkpoint, allow15s, then terminate only the owned group if needed.
Never automatically resume or delete data. Hold both shared locks.

Freeze and test a new launcher before native work. Preserve failed attempts,
all real outputs, input hashes, logs and final restarts. Neither short case
increases the accepted44 full-control total or becomes a production viewer run.
A short pass does not establish that the late thermal failure is resolved.
