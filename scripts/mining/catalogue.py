"""Aggregate per-repo scans into the operation catalogue with a prevalence ranking.

Records how many repositories were scanned and ranks each operation class by
the share of repositories configuring it, with the files that provide the
evidence.
"""

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.mining.detectors import ALL_SIGNALS
from scripts.mining.scan import RepoScanResult, scan_repo
from scripts.mining.workflow_order import ObservedOrder, extract_orders

_DESCRIPTIONS = {s.id: s.description for s in ALL_SIGNALS}
_LAYERS = {s.id: s.layer for s in ALL_SIGNALS}


@dataclass(frozen=True)
class CatalogueEntry:
    operation_id: str
    layer: str
    description: str
    repo_count: int
    repo_prevalence: float  # repo_count / total repos scanned
    evidence_files: tuple[str, ...]  # example citing file paths, deduped, capped


@dataclass(frozen=True)
class Catalogue:
    total_repos_scanned: int
    repos: tuple[str, ...]
    entries: tuple[CatalogueEntry, ...]  # sorted by repo_prevalence, descending
    observed_orders: tuple[ObservedOrder, ...]

    def to_dict(self) -> dict:
        return {
            "total_repos_scanned": self.total_repos_scanned,
            "repos": list(self.repos),
            "entries": [asdict(e) for e in self.entries],
            "observed_orders": [asdict(o) for o in self.observed_orders],
        }


def build_catalogue(repo_paths: list[Path]) -> Catalogue:
    scans: list[RepoScanResult] = [scan_repo(p) for p in repo_paths]
    orders: list[ObservedOrder] = []
    for p in repo_paths:
        orders.extend(extract_orders(p))

    repo_counts: Counter = Counter()
    evidence_by_op: dict[str, list[str]] = defaultdict(list)
    for scan in scans:
        present = scan.operations_present()
        for op_id in present:
            repo_counts[op_id] += 1
        for ev in scan.evidence:
            if len(evidence_by_op[ev.operation_id]) < 5:
                cited = f"{Path(scan.repo_root).name}:{ev.file_path}"
                if cited not in evidence_by_op[ev.operation_id]:
                    evidence_by_op[ev.operation_id].append(cited)

    total = len(scans)
    entries = []
    for op_id in _DESCRIPTIONS:
        count = repo_counts.get(op_id, 0)
        entries.append(
            CatalogueEntry(
                operation_id=op_id,
                layer=_LAYERS[op_id],
                description=_DESCRIPTIONS[op_id],
                repo_count=count,
                repo_prevalence=(count / total) if total else 0.0,
                evidence_files=tuple(evidence_by_op.get(op_id, [])),
            )
        )
    entries.sort(key=lambda e: e.repo_prevalence, reverse=True)

    return Catalogue(
        total_repos_scanned=total,
        repos=tuple(Path(s.repo_root).name for s in scans),
        entries=tuple(entries),
        observed_orders=tuple(orders),
    )


def write_catalogue(catalogue: Catalogue, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalogue.to_dict(), indent=2), encoding="utf-8")
