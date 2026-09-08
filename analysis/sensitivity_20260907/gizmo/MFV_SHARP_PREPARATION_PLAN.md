# Prospective repaired MFV sharp-law checks

8 September 2026, written before new native sharp work. This stage cannot
launch a full control. It checks the same isolated repaired MFV executable
already used by the completed historical L3 diagnostic. Canonical source,
original data, all numerical settings and every native output remain intact.

## Design and gates

Pin both original L3 ICs, full/short parameter files and their records. Require
identical IDs, coordinates, masses, internal energies, sampling and header
attributes; only the IC velocity array may differ. Verify the actual sharp
law (zero through1.3R, wind outside), historical tanh law, original density
edge, regular64x32x32 lattice and nominal pressure construction. The native
SPH density is checked separately; do not substitute lattice density for it.

Run three new sharp diagnostics on the SAME repaired binary and eight ranks:
one byte-identical original short recipe (end/output0.1code, maxstep0.05),
and two output-staggering tests (end/output4e-5, maxstep1e-5 and5e-6).
Those diagnostic timestep caps never enter a full control. Compare the new
native initial nonvelocity fields with the retained repaired historical short
and full initial states and original sharp short state. Require exact values
and original dtypes. Do not require native saved velocity to equal header-time
velocity: the native first half kick precedes output. For the two new sharp
timing tests, use the existing prospective norm-ratio tolerance0.002 around
0.5 and zero-step extrapolation bound4*float32epsilon*max(1,maxabs(ICvelocity)).
No extrapolated velocity is saved as a replacement simulation state.

Every new native field must be finite; density, mass, internal energy and
smoothing length positive. Check exact field schema, complete IDs, native
coordinates, direct mass sums and an independent yt reader at every output.
Retain all actual times, including extra terminal states. Reconstruct output
times from the pinned60-bit native clock, with the previously corrected
two-tick plus eight-double-epsilon endpoint allowance, not a29-bit clock.
Verify all eight terminal restart prefixes against the exact executable ABI,
finite/positive selected fields and the60-bit endpoint. Prefix decoding does
not certify the unparsed RNG/tree tail for checkpoint resume.

The short terminal mass gate retains the earlier engineering accumulation
model (n=32*N*(K+1), binary64 unit roundoff2^-53, K<=256). Include both MassTrue
and pending dMass. Require a detectable conserved-mass response above
32*doubleepsilon*max(ICmass). This is not a physical-accuracy theorem.

## Historical reuse and resource envelope

Verify the completed historical full diagnostic's frozen recipe, repaired
binary, actual input, IC, schedule and successful corrected review hashes.
Recheck every retained frame and restart hash. Its full input must be
byte-identical to the original sharp full input. Its nonvelocity IC arrays
must match. Do not rerun the historical diagnostic or old failed cases.

Reserve all three new short cases AND the potential missing full sharp case
before starting: each short case budgets4 native snapshots,3 restart sets,
IC and64MiB logs with25% margin; full budgets104 snapshots,3 restart sets,
IC and256MiB logs with25% margin. Existing historical data already occupies
disk and is not counted as new growth. Require separate10GiB guest and host
reserves,12GiB available guest RAM before launch,2GiB live RAM reserve.
Take benchmark.lock and production.lock. No competing heavy solver or build.
Use180s per short case,15s native-stop grace then bounded owned-group stop;
no automatic restart, raw deletion, source rebuild or application closing.

## Delivery

Freeze and hash all runner dependencies and tests before running. Negative
tests reject wrong laws, changed nonvelocity fields/parameters, bad cadence,
failed mass accounting, invalid JSON scalars and repeat attempts. A failed
native attempt or validator remains in its original directory.

Passing preparation permits a separately reviewed, frozen full sharp runner;
it does not itself count a full pair. Accepted total remains44. These tests
do not certify finer levels, pressure/boundary equality across codes, cooling,
frame tracking, material retention or velocity-at-header-time diagnostics.
