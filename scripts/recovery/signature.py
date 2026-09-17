"""Commit signature presence/verification check, per docs/01 and docs/03.

Presence test: `git verify-commit` succeeds against a known-good key/identity for
the commit reachable from the ref under test. Per docs/03, the before-state check
must be pointed at the pre-rewrite commit object (which will not exist in the final
history after rebase/amend) — this module verifies whatever SHA it's given and does
not attempt to locate the pre-rewrite object itself; that's the caller's job
(reflog / PR API / archived ref resolution).
"""

import subprocess
from pathlib import Path

from scripts.recovery.outcomes import PresenceResult


def check_presence(repo: Path, commit_sha: str) -> PresenceResult:
    result = subprocess.run(
        ["git", "-C", str(repo), "verify-commit", "--raw", commit_sha],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Distinguish "no signature at all" from "signature present but bad" if the
        # git version's stderr makes that possible, so a surfaced verification
        # failure can be scored as lost_surfaced rather than silently_lost.
        surfaced = "no signature" not in result.stderr.lower()
        return PresenceResult(present=False, origin=None, surfaced_failure=surfaced)

    signer = _extract_signer(result.stderr)
    return PresenceResult(present=True, origin=signer)


def _extract_signer(verify_commit_stderr: str) -> str | None:
    for line in verify_commit_stderr.splitlines():
        line = line.strip()
        if line.startswith("[GNUPG:] GOODSIG") or "Good signature from" in line:
            return line
    return None
