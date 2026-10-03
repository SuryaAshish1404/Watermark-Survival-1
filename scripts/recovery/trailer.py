"""Agent/co-authorship trailer presence check, per docs/01 and docs/03.

Walks a git ref's reachable commit messages looking for trailers matching the
validated census vocabulary (arXiv:2606.24429), rather than inventing a new pattern.
"""

import re
import subprocess
from pathlib import Path

from scripts.recovery.outcomes import PresenceResult

# Ported from the census paper's trailer vocabulary (arXiv:2606.24429).
TRAILER_KEY_PATTERN = re.compile(
    r"^(Co-Authored-By|Assisted-By|Generated-By)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _git_log(repo: Path, ref: str, extra_args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "log", ref, "--format=%H%n%B%n---COMMIT-END---", *extra_args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout


def find_trailer_commits(repo: Path, ref: str) -> list[tuple[str, str]]:
    """Return [(commit_sha, matched_origin_string), ...] for every commit reachable
    from ref that carries a trailer matching TRAILER_KEY_PATTERN."""
    log = _git_log(repo, ref, [])
    hits = []
    for block in log.split("---COMMIT-END---"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        sha, body = lines[0], "\n".join(lines[1:])
        match = TRAILER_KEY_PATTERN.search(body)
        if match:
            hits.append((sha, match.group(2).strip()))
    return hits


def check_presence(repo: Path, ref: str) -> PresenceResult:
    """Presence test for docs/01: trailer key present in a commit message reachable
    from `ref`. Returns the first match's origin string as the claimed origin.

    Caller is responsible for supplying the *correct* ref per docs/03 (pre-rewrite
    chain for a before-state check, the shipped release ref for an after-state
    check) — this function does not know which state it's being asked about.
    """
    hits = find_trailer_commits(repo, ref)
    if not hits:
        return PresenceResult(present=False, origin=None)
    return PresenceResult(present=True, origin=hits[0][1])
