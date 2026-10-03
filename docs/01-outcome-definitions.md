# Outcome Definitions (Retained / Silently Lost / Spuriously Gained)

These definitions are fixed before any measurement is run. A script must be able to
apply them without judgment calls.

## Preconditions shared by all three outcomes
- **Unit of recovery is the release**, not the commit that produced the carrier. A
  carrier is checked at the artifact a consumer would actually receive (tagged release,
  built package, published tarball/image) — never at an intermediate commit.
- **Before-state must be established, not assumed.** A carrier only counts as
  "present before the operation" if the before-state reconstruction procedure
  (docs/03-before-state.md) positively confirms it was emitted. If emission cannot be
  confirmed, the release is excluded from that carrier's denominator and logged, not
  scored as lost.

## Per-carrier presence check (what "the claim" means)
| Carrier | Presence test |
|---|---|
| Agent/co-authorship trailer | Trailer key present in commit message reachable from the release ref, matching the validated census's trailer vocabulary |
| Commit signature | `git verify-commit` (or equivalent) succeeds against a known-good key/identity for the commit(s) reachable from the release ref |
| Build attestation / SBOM | in-toto/SLSA attestation resolves, is well-formed, and its subject digest matches the shipped artifact's digest |

## The three outcomes, operationally

**Retained** — the carrier is present before the operation AND present after, AND the
post-operation carrier still resolves to the same origin claim (same identity/agent/
model/build) as the pre-operation carrier. A carrier that resolves but now names a
*different* origin is not retained — see Spuriously Gained.

**Silently Lost** — the carrier is confirmed present before the operation (per the
before-state procedure) AND absent, unresolvable, or verification-failing after the
operation, AND no error or warning was surfaced to any human in the ordinary tooling
path (i.e., the operation completed "successfully" from the operator's point of view).
If the tooling *did* surface a warning/failure that a reasonable operator would see
(e.g., `git verify-commit` printing an error the operator read), record it separately
as "lost, surfaced" — it still counts toward the loss rate but not toward the
"silent" sub-claim, which matters for the disclosure-obligation argument.

**Spuriously Gained** — the release carries a resolvable, verification-passing claim
attributing origin to an agent/model/signer/builder that was not the actual origin,
where actual origin is established by the ground truth of the experiment (for the
measured arm: the pre-operation state showed no such carrier, or showed a different
one; for the spurious-gain experiment specifically: the module is independently
classified as substantially human per docs/02-substantially-human-rule.md, but the
resulting commit/release nonetheless carries a claim attributing it to a model).

## Explicitly out of scope for these three labels
- **Modified but detectable** (used only in the anticipatory/watermark arm): the
  watermark's own detector returns a positive match below
  full confidence but above its stated threshold. This is a fourth, scheme-specific
  label layered on top of "retained" for statistical detectors only — deterministic
  carriers (signatures, attestations, trailers) never get this label; they are boolean
  resolve/don't-resolve.
- **Never emitted**: not scored on any axis; excluded and logged (see before-state doc).
