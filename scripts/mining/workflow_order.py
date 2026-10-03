"""Extract observed operation order from GitHub Actions workflow step sequences.

Used to compose operations in the orders real projects apply them, rather than
an invented order. A step is classified as an
instance of an operation class if its `name` or `run` field contains one of that
class's step_keywords (detectors.py); classification is best-effort and only as
strong as the keyword list, so false negatives (an unrecognized step) are silently
skipped rather than guessed at, and every extracted order is tied to the workflow
file it came from.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from scripts.mining.detectors import ALL_SIGNALS


@dataclass(frozen=True)
class ObservedOrder:
    workflow_file: str
    job_name: str
    operation_sequence: tuple[str, ...]  # operation ids, in step order, dupes allowed


def _classify_step(step: dict) -> str | None:
    haystack = " ".join(
        str(step.get(key, "")) for key in ("name", "run")
    ).lower()
    if not haystack.strip():
        return None
    for signal in ALL_SIGNALS:
        for keyword in signal.step_keywords:
            if keyword.lower() in haystack:
                return signal.id
    return None


def extract_orders(repo_root: Path) -> list[ObservedOrder]:
    orders: list[ObservedOrder] = []
    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return orders

    for wf_path in list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")):
        try:
            doc = yaml.safe_load(wf_path.read_text(encoding="utf-8", errors="ignore"))
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        rel = wf_path.relative_to(repo_root).as_posix()
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps") or []
            if not isinstance(steps, list):
                continue
            sequence = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                op = _classify_step(step)
                if op:
                    sequence.append(op)
            if sequence:
                orders.append(ObservedOrder(rel, str(job_name), tuple(sequence)))
    return orders
