# MFV: final exported zeros explained, thermal evolution still unvalidated

8 September 2026. No new simulation was run for this diagnosis. Both original
L3 attempts remain excluded from the accepted comparison; the study still has
44 accepted full controls. No floor, timestep, compiler option, native field,
restart or raw snapshot was changed or deleted.

## What the retained state shows

Both native terminal restarts are at exactly 5 t_cc, the time of snapshot100.
Their conserved and predicted internal energies are positive for all 65536
particles per case. The four particles exported with zero energy have:

| Velocity prescription | Particle ID | Internal energy in double-precision restart | Energy in float32 snapshot |
| --- | ---: | ---: | ---: |
| Sharp | 109 | 1.52799421328655e-43 | 0 |
| Historical tanh | 96 | 4.37163851163316e-141 | 0 |
| Historical tanh | 99 | 2.498054346189284e-78 | 0 |
| Historical tanh | 102 | 1.649788009116768e-48 | 0 |

Conserved and predicted energy agree for these four terminal particles. Their
restart pressures are also positive, though extremely small. All four started
with exported energy about0.01500266 and density about99.8913; terminal density
is236.6-301.7. These are retained native values, not repaired outputs.

The native writer casts `max(MinEgySpec, InternalEnergyPred)` to float32;
the retained floor is exactly zero. The three historical values are below
the smallest positive float32 value, about1.4013e-45, and round to zero.
The sharp value would be a nonzero float32 subnormal. However, this exact
executable's startup constructor enables flush-to-zero and denormals-are-zero
(FTZ/DAZ). Its float32 subnormal output is therefore zero too.

This is direct binary evidence, not an inference from a current Makefile:
`set_fast_math` at address0x4040 ORs MXCSR with0x8040 and loads it; the
`.init_array` entry and relative relocation point to that constructor.
The [GCC x86 documentation](https://gcc.gnu.org/onlinedocs/gcc-15.1.0/gcc/x86-Options.html#index-mdaz-ftz)
describes FTZ/DAZ. The actual disassembly is retained in the diagnostic JSON.

## How the reader was checked

The exact original MFV executable is pinned by SHA256
`b7634f844d98ceef246d66e2243827f0c5774c9997b92bd8ffeedfdf940eed91`.
Its DWARF debug data gives struct sizes15864/288/384bytes for the global,
particle and gas records. All32/24/20 complete definitions respectively agree
on the selected fields' offsets and types. No present-day header compilation
was substituted for the executable's ABI.

All16 existing final restart files were read without calling the native restart
routine. Eight exported fields match exactly for all particles: IDs, child IDs,
generation IDs, periodically wrapped positions, masses, fluid velocities,
density and particle velocities. Energy matches exactly when reproducing the
independently observed native FTZ convention. The ordinary IEEE float32 cast
also remains recorded: it fails for the sharp particle, rather than being
silently treated as an exact match.

A second reader uses `struct.unpack`, not the NumPy structured-array decoder.
It independently verifies IDs, mass, density and energy serialization for all
131072 final particles, and checks positive conserved/predicted energy and
pressure. It also rechecks all202 original snapshot hashes and16 restart hashes
against the earlier audit. Scalar histories retain every actual header time for
the four terminal-zero IDs; they are not synthesized 3D frames.

Eight synthetic tests cover DWARF hierarchy/array layout, ambiguous definitions,
unsupported expressions, buffer/count bounds, incomplete restart prefixes,
true zero versus ordinary underflow versus FTZ, and independent scalar casting.
The first reader attempts exposed a whitespace parser issue and the ordinary
float32-versus-FTZ mismatch. No completed report was overwritten to hide either.

## What this does not establish

The precise terminal export-zero mechanism is now explained. The reason thermal
energy fell by tens to more than100 orders of magnitude in a non-radiative run
is not. Native kick/predictor code contains a half-previous-energy limiter;
repeated limiting is a hypothesis to investigate, not a proven causal history.
Changing output precision alone would expose tiny values, not validate their
physical evolution. Do not add a floor or change compiler flags merely to make
the existing acceptance check pass.

Only snapshot100 has the matching retained restart generation. We do not claim
that every earlier zero snapshot has been diagnosed from contemporaneous
double-precision state. The RNG/tree restart tail and smoothing-length storage
are not decoded here; this is not certification that the full restart can be
executed. The original snapshot hashes and contents remain untouched.

The next useful work is a read-only trace of the native energy update, limiter,
and already saved scalar histories. If a short instrumented test is necessary,
it needs a prospective observational-equivalence check and isolated outputs
before any larger science run. No full MFV queue has been enabled.

## Reproducible evidence

[Diagnosis and compiled layouts](mfv_restart_diagnosis_v1.json),
[independent review and native histories](mfv_restart_review_v1.json),
[decoder](diagnose_mfv_restart.py), [independent reader](review_mfv_restart.py),
[tests](test_mfv_restart.py), and [earlier all-state audit](mfv_pair_audit.json).

Native working root: `/home/kaan/sensitivity_20260907/gizmo`.
Windows source root: `C:/Users/kaanb/CloudCrushing/sensitivity_20260907/gizmo`.
Use `/home/kaan/venv/bin/python -m unittest -v test_mfv_restart` from the
native root for synthetic tests. Completed diagnostic/review JSONs must not be
overwritten or needlessly regenerated. Public scripts require the retained
local raw files and exact binary; they are not themselves a raw-data backup.
