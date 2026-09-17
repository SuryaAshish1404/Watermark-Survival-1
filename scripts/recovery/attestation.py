"""Build attestation / SBOM presence check, per docs/01 and docs/03.

Presence test: an in-toto/SLSA provenance predicate resolves, is well-formed, and
its subject digest matches the artifact digest under test.

NOT YET VALIDATED. Unlike trailer.py and signature.py (which only need a local git
checkout), this check needs a real attestation source: GitHub's Artifact Attestations
API, a Sigstore/Rekor transparency-log lookup, or a registry-embedded provenance
predicate, depending on how the sampled repo publishes. Which source is authoritative
is a sampling-frame-adjacent decision that hasn't been made yet (repos in the sample
may use different attestation stores). This module defines the interface so
trailer/signature checks aren't blocked on it; the resolver body is a stub until a
real sampled repo with attestations exists to build against.
"""

from dataclasses import dataclass

from scripts.recovery.outcomes import PresenceResult


@dataclass(frozen=True)
class AttestationQuery:
    artifact_digest: str  # sha256:... of the shipped artifact
    source: str  # "github-attestations" | "sigstore-rekor" | "registry-embedded"
    repo_slug: str | None = None


def check_presence(query: AttestationQuery) -> PresenceResult:
    raise NotImplementedError(
        "attestation resolution requires a live attestation store; "
        "implement once the sampling frame (docs/04) is frozen and at least one "
        "sampled repo with in-toto/SLSA attestations is available to build against. "
        "See module docstring."
    )
