"""How much of the lifecycle-chain outcome is decided by the random draw of real
corpus tokens (comment, annotations, docstring, identifiers), rather than by the
watermark scheme?

Motivation: the n=25 lifecycle run contained only 9 distinct STONE trajectories —
17/25 runs were the same byte-identical generation — and the mutation RNG used
Python's per-process-randomized hash(), so the outcome of that dominant text
depended on one uncontrolled draw per process. This script makes that dependence
measurable: same text, many draws.

Needs only the tokenizer (STONE detection never touches the model), so it is
cheap and memory-safe. Text-only chain steps (the git squash and wheel build did
not change a single retained/lost outcome across 43 lifecycle runs, so they are
skipped here).

Also runs the ast.unparse control on the same texts: first-step score after
(A) ast_roundtrip alone vs (B) add_type_hints, which itself ends in ast.unparse.

Usage: python experiments/stone_pilot/scripts/lifecycle_draw_variance.py --repo <lutris> [--draws 60]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import human_mutations  # noqa: E402
import more_operations  # noqa: E402
from human_mutations import mut_add_real_comment, mut_human_rename  # noqa: E402
from more_operations import mut_add_real_docstring, mut_add_type_hints, mut_targeted_patch  # noqa: E402
from run_pilot import mut_ast_roundtrip, mut_format, mut_lint_autofix  # noqa: E402
from schemes import MODEL_NAME, build_scheme  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

STEPS = [
    ("agent_add_type_hints", mut_add_type_hints),
    ("agent_add_docstring", mut_add_real_docstring),
    ("review_targeted_patch", mut_targeted_patch),
    ("review_rename", mut_human_rename),
    ("review_add_comment", mut_add_real_comment),
    ("ci_format", mut_format),
    ("ci_lint_autofix", mut_lint_autofix),
]


def set_salt(s: int) -> None:
    human_mutations.SEED_SALT = s
    more_operations.SEED_SALT = s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=60)
    ap.add_argument("--out", type=Path, default=HERE.parent / "draw_variance_results.json")
    args = ap.parse_args()

    src_file = HERE.parent / "full_battery_results.json"
    texts = [r["generated_code"] for r in json.loads(src_file.read_text(encoding="utf-8"))["runs"]]

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    stone = build_scheme("stone", None, tok)  # detection needs the tokenizer only

    results = []
    for ti, text in enumerate(texts):
        base = stone.detect_watermark(text)
        rec = {"text_index": ti, "chars": len(text), "baseline": base["score"],
               "baseline_detected": bool(base["is_watermarked"])}
        set_salt(0)
        rt = stone.detect_watermark(mut_ast_roundtrip(text, args.repo))
        rec["ast_roundtrip_score"] = rt["score"]

        per_step_retained = [0] * len(STEPS)
        first_step_scores, end_scores, never_broke, end_retained = [], [], 0, 0
        for s in range(args.draws):
            set_salt(s)
            cur, broke = text, False
            for si, (name, fn) in enumerate(STEPS):
                cur = fn(cur, args.repo)
                det = stone.detect_watermark(cur)
                ok = bool(det["is_watermarked"])
                per_step_retained[si] += ok
                broke = broke or not ok
                if si == 0:
                    first_step_scores.append(det["score"])
                if si == len(STEPS) - 1:
                    end_scores.append(det["score"])
                    end_retained += ok
            never_broke += (not broke)
        n = args.draws
        rec.update(
            draws=n,
            retained_at_step={STEPS[i][0]: per_step_retained[i] / n for i in range(len(STEPS))},
            never_broke=never_broke / n,
            retained_at_end=end_retained / n,
            type_hints_score_mean=statistics.mean(first_step_scores),
            type_hints_score_range=[min(first_step_scores), max(first_step_scores)],
            end_score_range=[min(end_scores), max(end_scores)],
        )
        results.append(rec)
        print(f"text {ti} ({rec['chars']} chars, baseline z={rec['baseline']:.2f}, detected={rec['baseline_detected']}):")
        print(f"   ast_roundtrip alone -> z={rec['ast_roundtrip_score']:.2f} | add_type_hints -> mean z={rec['type_hints_score_mean']:.2f} "
              f"(range {rec['type_hints_score_range'][0]:.2f}..{rec['type_hints_score_range'][1]:.2f})")
        print(f"   over {n} draws: never broke {rec['never_broke']:.0%}, retained at end {rec['retained_at_end']:.0%}")
        print("   retained by step: " + ", ".join(f"{k.split('_',1)[1][:10]}={v:.0%}" for k, v in rec["retained_at_step"].items()))

    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
