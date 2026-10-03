"""Build attestation / SBOM presence check, per docs/01 and docs/03.

Presence test: an in-toto/SLSA provenance predicate resolves, is well-formed, and
its subject digest matches the artifact digest under test.

Unlike trailer.py and signature.py, which only need a local git checkout, this
check resolves against an attestation store: GitHub's Artifact Attestations API, a
Sigstore/Rekor transparency-log lookup, or a registry-embedded provenance predicate,
depending on how a repository publishes. This module defines the query and result
interface; resolution requires access to a live attestation store.
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
        "attestation resolution requires a live attestation store "
        "(github-attestations, sigstore-rekor, or registry-embedded); "
        "see module docstring."
    )
