"""Model-free factorial over saved baselines: first-step variant x CI order x random draw.

Every step except generation is text-in/text-out, and STONE/KGW detection needs only the
tokenizer, so once baselines are saved the rest of the lifecycle chain can be replayed
cheaply and repeatedly. The unit of analysis is the DISTINCT BASELINE, not the run: draws
within a baseline are averaged first (pseudo-replication fix), then baselines are
bootstrapped.

Factors
  chain    : unparse_chain   agent/review steps reserialize with ast.unparse (as run so far)
             patch_chain     the same edits and draws, applied as text patches (programs verified
                             identical in scripts/verify_patch_ops.py)
             roundtrip_only  one ast.unparse and nothing else, a floor reference
  ci order : format_then_lint (hand-designed chain) | lint_then_format (majority order mined from
             20 real Python repos' workflows: 29 vs 15)
git squash and wheel build were no-ops in every earlier run and need no model, so they are omitted.

Usage: python scripts/offline_matrix.py --repo <lutris> --scheme stone --results lifecycle_v2_results.json [--draws 20]
"""

import argparse
import itertools
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import human_mutations  # noqa: E402
import more_operations  # noqa: E402
from human_mutations import mut_add_real_comment, mut_human_rename  # noqa: E402
from more_operations import (  # noqa: E402
    mut_add_real_docstring, mut_add_real_docstring_patch, mut_add_type_hints, mut_add_type_hints_patch,
    mut_human_rename_patch, mut_targeted_patch, mut_targeted_patch_patch)
from run_pilot import mut_ast_roundtrip, mut_format, mut_lint_autofix  # noqa: E402
from schemes import MODEL_NAME, build_scheme  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

CHAINS = {
    "unparse_chain": [("hints_unparse", mut_add_type_hints), ("add_docstring", mut_add_real_docstring),
                      ("targeted_patch", mut_targeted_patch), ("human_rename", mut_human_rename),
                      ("add_comment", mut_add_real_comment)],
    "patch_chain": [("hints_patch", mut_add_type_hints_patch), ("add_docstring", mut_add_real_docstring_patch),
                    ("targeted_patch", mut_targeted_patch_patch), ("human_rename", mut_human_rename_patch),
                    ("add_comment", mut_add_real_comment)],
    "roundtrip_only": [("ast_roundtrip", mut_ast_roundtrip)],
}
ORDERS = {"format_then_lint": [("ci_format", mut_format), ("ci_lint", mut_lint_autofix)],
          "lint_then_format": [("ci_lint", mut_lint_autofix), ("ci_format", mut_format)]}


def salt(s):
    human_mutations.SEED_SALT = s
    more_operations.SEED_SALT = s


def boot_ci(vals, n=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choices(vals, k=len(vals))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def collect_baselines(path: Path, scheme: str):
    data = json.loads(path.read_text(encoding="utf-8"))["schemes"][scheme]["runs"]
    seen, out = set(), []
    for r in data:
        if r.get("excluded"):
            continue
        code = r["chain"][0]["code"]
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out, len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--scheme", default="stone")
    ap.add_argument("--results", type=Path, default=HERE.parent / "lifecycle_v2_results.json")
    ap.add_argument("--draws", type=int, default=20)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or HERE.parent / f"offline_matrix_{args.scheme}.json"

    texts, n_runs = collect_baselines(args.results, args.scheme)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    det = build_scheme(args.scheme, None, tok)
    print(f"{args.scheme}: {len(texts)} distinct usable baselines from {n_runs} runs")

    cells = {}  # (first, order) -> list per baseline of dict
    for ti, text in enumerate(texts):
        for (fname, csteps), (oname, osteps) in itertools.product(CHAINS.items(), ORDERS.items()):
            never = end = 0
            first_breaks = Counter()
            step_z = Counter()
            for s in range(args.draws):
                salt(s)
                cur, broke = text, False
                steps = csteps + osteps
                for name, fn in steps:
                    cur = fn(cur, args.repo)
                    d = det.detect_watermark(cur)
                    step_z[name] += d["score"]
                    if not d["is_watermarked"] and not broke:
                        broke = True
                        first_breaks[name] += 1
                never += (not broke)
                end += bool(d["is_watermarked"])
            cells.setdefault(f"{fname}|{oname}", []).append(dict(
                baseline_index=ti, chars=len(text), baseline_z=det.detect_watermark(text)["score"],
                never_broke=never / args.draws, end_retained=end / args.draws,
                first_breaks=dict(first_breaks), end_z=step_z[steps[-1][0]] / args.draws,
                step_z={k: v / args.draws for k, v in step_z.items()}))
        print(f"  baseline {ti + 1}/{len(texts)} done")
    salt(0)

    summary = {}
    print(f"\n{'cell':34s} {'never-broke':>22s} {'retained@end':>22s} {'end z':>7s}")
    for key, rows in cells.items():
        nb = [r["never_broke"] for r in rows]
        en = [r["end_retained"] for r in rows]
        nlo, nhi = boot_ci(nb)
        elo, ehi = boot_ci(en)
        summary[key] = dict(n_baselines=len(rows), never_broke=statistics.mean(nb), never_broke_ci=[nlo, nhi],
                            end_retained=statistics.mean(en), end_retained_ci=[elo, ehi],
                            end_z=statistics.mean(r["end_z"] for r in rows))
        print(f"{key:34s} {statistics.mean(nb):6.0%} [{nlo:4.0%},{nhi:4.0%}]      "
              f"{statistics.mean(en):6.0%} [{elo:4.0%},{ehi:4.0%}]  {summary[key]['end_z']:6.2f}")
    out.write_text(json.dumps(dict(scheme=args.scheme, n_baselines=len(texts), draws=args.draws,
                                   summary=summary, cells=cells), indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
