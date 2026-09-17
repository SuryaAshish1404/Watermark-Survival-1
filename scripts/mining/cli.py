"""CLI: python -m scripts.mining.cli <repo_path> [<repo_path> ...] [--out PATH]

Regenerates the operation catalogue from a list of local repo checkouts. This is
the "regenerates from the repository list without manual editing" requirement in
the brief's technical task table — the JSON output is derived, never hand-edited.
"""

import argparse
import sys
from pathlib import Path

from scripts.mining.catalogue import build_catalogue, write_catalogue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="+", type=Path, help="Local repo checkout paths")
    parser.add_argument(
        "--out", type=Path, default=Path("catalogue/measured/operation_catalogue.json")
    )
    args = parser.parse_args(argv)

    missing = [r for r in args.repos if not r.is_dir()]
    if missing:
        print(f"Not a directory: {missing}", file=sys.stderr)
        return 1

    catalogue = build_catalogue(args.repos)
    write_catalogue(catalogue, args.out)
    print(f"Scanned {catalogue.total_repos_scanned} repos -> {args.out}")
    for entry in catalogue.entries:
        print(f"  {entry.operation_id:14s} {entry.repo_prevalence:5.0%}  ({entry.layer})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
