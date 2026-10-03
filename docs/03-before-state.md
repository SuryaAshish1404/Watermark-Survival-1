# Before-State Reconstruction Procedure

Purpose: a claim recorded as "lost" must be shown to have existed before the
operation that allegedly destroyed it — never inferred. This procedure is what lets
docs/01-outcome-definitions.md distinguish "never emitted" from "emitted then
destroyed."

## Per-carrier reconstruction

**Agent/co-authorship trailer** — walk the commit graph backward from the
pre-operation ref (e.g., the PR branch tip before squash) using the real parent
chain (not the rewritten one). Trailer is "emitted" if present in any reachable
commit message on that pre-rewrite chain. Requires access to the pre-rewrite refs —
for GitHub-hosted repos this means PR commit history via the API, since local clones
often only retain the post-squash ref.

**Commit signature** — same pre-rewrite chain requirement. A signature is "emitted"
if `git verify-commit` succeeds on the pre-rewrite commit object. Rebase/amend
produce a new commit object even when content is unchanged, so the *original* object
must be resolvable (via reflog, PR API, or archived ref) — it will not exist in the
final history.

**Build attestation/SBOM** — "emitted" if a provenance predicate (in-toto/SLSA)
exists for *some* build of the pre-operation source tree, resolvable via the CI
provider's attestation store/transparency log, independent of whether that build was
the one eventually shipped.

## Distinguishing absence-of-signal from absence-of-evidence
If the pre-rewrite chain is not recoverable at all (host has garbage-collected PR
refs, no CI attestation retention, reflog expired), the release is **excluded** from
that carrier's denominator and logged in the exclusion log (experiments/data/sampling/exclusions.csv)
with a reason code — it is never scored as "silently lost." This is the standard the
Repository Mining checklist in the brief requires.

## Validation
Before running at scale: build a hand-constructed fixture set (small local repos with
known, engineered before/after states for every carrier x outcome combination,
including the "gained" case) and confirm the procedure classifies every fixture
correctly. This is the acceptance test named in the brief's technical task table.
