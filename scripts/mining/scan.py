"""Scan a single repository for operation-class configuration signals.

Every match is recorded with the file that produced it, so a catalogue entry can
always be traced back to a cited configuration file.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from scripts.mining.detectors import ALL_SIGNALS, OperationSignal


@dataclass(frozen=True)
class Evidence:
    operation_id: str
    file_path: str  # relative to repo root, forward-slash normalized
    matched_snippet: str | None  # None when the signal is existence-only


@dataclass(frozen=True)
class RepoScanResult:
    repo_root: str
    evidence: tuple[Evidence, ...]

    def operations_present(self) -> set[str]:
        return {e.operation_id for e in self.evidence}


def _iter_matches(repo_root: Path, glob: str) -> list[Path]:
    try:
        return [p for p in repo_root.glob(glob) if p.is_file()]
    except (OSError, ValueError):
        return []


def _check_signal(repo_root: Path, signal: OperationSignal) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen_files: set[Path] = set()

    for glob in signal.exist_globs:
        for path in _iter_matches(repo_root, glob):
            if path in seen_files:
                continue
            seen_files.add(path)
            rel = path.relative_to(repo_root).as_posix()
            evidence.append(Evidence(signal.id, rel, None))

    if signal.content_pattern is None:
        return evidence

    for glob in signal.content_globs:
        for path in _iter_matches(repo_root, glob):
            if path in seen_files:
                continue
            seen_files.add(path)
            rel = path.relative_to(repo_root).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            match = re.search(signal.content_pattern, text, re.IGNORECASE)
            if match:
                snippet = text[max(0, match.start() - 20): match.end() + 20].strip()
                evidence.append(Evidence(signal.id, rel, snippet))
    return evidence


def scan_repo(repo_root: Path) -> RepoScanResult:
    evidence: list[Evidence] = []
    for signal in ALL_SIGNALS:
        evidence.extend(_check_signal(repo_root, signal))
    return RepoScanResult(repo_root=str(repo_root), evidence=tuple(evidence))
