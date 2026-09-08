# Read-only Gasoline divergence review

8 September 2026. This is additional analysis of the four preserved two-worker,
120-step historical-law diagnostics, not a new simulation or acceptance rule.

Question: when do the saved fields first differ, which particle/component is
involved, and are differences already present in the retained double-precision
checkpoints rather than caused solely by TIPSY serialization?

Use all four cases and all 20 common evolved outputs, after exact iOrder mapping.
Preserve the 81-state audit and its failed one-float32-spacing criterion. Report
all six pairs, not a chosen passing subset. Identify earliest *saved* differences;
the first differing integration operation cannot be inferred from sparse files.
Do not add repeats, change tolerances, rebuild, resume, or launch the solver.

Decode only the verified checkpoint prefix: iOrder/iActive, mass, softening,
position, velocity and internal energy. Native pkd.h and pkdWriteCheck use a
120-byte CHKPART; the exact original executable's disassembly confirms the
120-byte fwrite and double stores at offsets8,16,24..40,48..64,72. Original,
hook and retained builds share the same pkd.o. Verify binary/object hashes and
the native FDL header probe before using this selected layout. The FDL text's
legacy particle declaration is not the payload ABI. Checkpoints do not store
density or smoothing length; their reader resets those fields. Do not interpret
unwritten/padding bytes, cooling tails, or compare full checkpoint bytes as a
physical state. This decoder is not permission to resume a checkpoint.

Check both checkpoints (steps60/120) for all four cases. Compare their selected
double fields by native ID, independently decode selected records using struct,
and test exact float32 agreement with the same-step TIPSY position, velocity,
mass, softening and parameter-scaled internal energy. A failed roundtrip stops
the review instead of silently relaxing it. Record actual headers and hashes.

Source review must follow the actual SMX_DENDVDX and SMX_SPHPRESSURETERMS paths.
DenDVDX gathers density locally and combDenDVDX only combines active flags; do
not attribute density directly to the unused combDensity callback. Symmetric
pressure-force/energy accumulation and MPI cache-service interleaving remain
candidate mechanisms until a controlled trace demonstrates causality.

Tests cover ID mapping, malformed/truncated files, selected ABI offsets,
nonfinite fields, finite-precision distances, signed zeros, independent decoding,
temperature scaling and refusing existing outputs. Freeze the analysis scripts
and plan in a new read_only_divergence_v1 directory. A 64 MiB artifact cap and
sequential loading keep this far below native-run resource budgets. No raw files,
cache files, native binaries, source or previous reports may be modified.

Outcome is a diagnostic report with caveats. Full controls remain held. A
separate prospective protocol is required for any new native causal experiment.
