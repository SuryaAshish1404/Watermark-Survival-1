"""Observed lint/format order in real CI workflows.

Fetches only `.github/workflows` from each repository in `data/ci_order_repos.json`
at its pinned commit, extracts every job's operation sequence with
`scripts/mining/workflow_order.py`, and counts how often each operation precedes
another within a job. The lifecycle runs both lint/format orders; this script
reports which one real projects use.

Usage: python experiments/scripts/mine_ci_order.py [--workdir DIR] [--out PATH]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from scripts.mining.workflow_order import extract_orders  # noqa: E402

REPOS_FILE = HERE.parent / "data" / "ci_order_repos.json"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def fetch_workflows(repo: str, commit: str, dest: Path) -> None:
    """Sparse, blob-filtered fetch of `.github/workflows` at one commit."""
    if (dest / ".git").exists():
        return
    dest.mkdir(parents=True)
    _git(dest, "init", "-q")
    _git(dest, "remote", "add", "origin", f"https://github.com/{repo}")
    _git(dest, "sparse-checkout", "set", ".github/workflows")
    _git(dest, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit)
    _git(dest, "checkout", "-q", "FETCH_HEAD")


def precedence(sequences) -> Counter:
    """(a, b) -> number of times operation a appears before a different operation b
    within the same job."""
    prec = Counter()
    for seq in sequences:
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                if seq[i] != seq[j]:
                    prec[(seq[i], seq[j])] += 1
    return prec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, default=None,
                    help="where to keep the workflow checkouts (default: a temporary directory)")
    ap.add_argument("--out", type=Path, default=HERE.parent / "results" / "ci_order_results.json")
    args = ap.parse_args()

    repos = json.loads(REPOS_FILE.read_text(encoding="utf-8"))["repos"]
    tmp = None if args.workdir else tempfile.TemporaryDirectory()
    workdir = args.workdir or Path(tmp.name)

    per_repo, sequences = {}, []
    for entry in repos:
        dest = workdir / entry["repo"].replace("/", "__")
        fetch_workflows(entry["repo"], entry["commit"], dest)
        orders = extract_orders(dest)
        per_repo[entry["repo"]] = len(orders)
        sequences.extend(o.operation_sequence for o in orders)

    prec = precedence(sequences)
    lint_first = prec[("lint_autofix", "format")]
    format_first = prec[("format", "lint_autofix")]
    result = {
        "repos": len(repos),
        "job_sequences": len(sequences),
        "lint_autofix_before_format": lint_first,
        "format_before_lint_autofix": format_first,
        "majority_order": "lint_then_format" if lint_first > format_first else "format_then_lint",
        "job_sequences_per_repo": per_repo,
        "operation_counts": dict(Counter(op for s in sequences for op in s).most_common()),
    }
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{result['repos']} repositories, {result['job_sequences']} job sequences")
    print(f"lint_autofix before format: {lint_first}; format before lint_autofix: {format_first}")
    print(f"wrote {args.out}")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
