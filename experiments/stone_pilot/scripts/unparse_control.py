"""Decisive control for Finding 8: is the first-step signal loss caused by the type
annotations, or by the whole-file ast.unparse() reserialization?

Three first-step variants on IDENTICAL baseline texts and identical annotation draws:
  A  ast_roundtrip           parse + unparse, no content change
  B  type hints via unparse  the lifecycle chain's existing step
  C  type hints via patch    same annotations inserted as text at AST-reported positions,
                             header colon found with tokenize; every other byte untouched

C is validated: ast.dump(parse(C)) must equal ast.dump(parse(B)), i.e. the same program.
Tokenizer-only detection (STONE/KGW), so it is cheap.

Usage: python scripts/unparse_control.py --repo <lutris> [--draws 40] [--scheme stone]
"""

import argparse
import ast
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import more_operations  # noqa: E402
from more_operations import mut_add_type_hints, patch_type_hints  # noqa: E402
from run_pilot import mut_ast_roundtrip  # noqa: E402
from schemes import MODEL_NAME, build_scheme  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=40)
    ap.add_argument("--scheme", default="stone")
    ap.add_argument("--texts", type=Path, default=HERE.parent / "control_texts.json")
    ap.add_argument("--out", type=Path, default=HERE.parent / "unparse_control_results.json")
    args = ap.parse_args()

    if args.texts.exists():
        texts = json.loads(args.texts.read_text(encoding="utf-8"))
    else:
        texts = [r["generated_code"] for r in json.loads(
            (HERE.parent / "full_battery_results.json").read_text(encoding="utf-8"))["runs"]]

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    det = build_scheme(args.scheme, None, tok)

    results = []
    for ti, text in enumerate(texts):
        base = det.detect_watermark(text)
        if not base["is_watermarked"]:
            print(f"text {ti}: baseline not detected, skipped")
            continue
        rt = det.detect_watermark(mut_ast_roundtrip(text, args.repo))
        recs = []
        for s in range(args.draws):
            more_operations.SEED_SALT = s
            b_text = mut_add_type_hints(text, args.repo)
            c_text = patch_type_hints(text)
            same = ast.dump(ast.parse(b_text)) == ast.dump(ast.parse(c_text))
            b = det.detect_watermark(b_text)
            c = det.detect_watermark(c_text)
            recs.append(dict(salt=s, same_program=same, b=b["score"], b_ok=bool(b["is_watermarked"]),
                             c=c["score"], c_ok=bool(c["is_watermarked"])))
        n = len(recs)
        r = dict(text_index=ti, chars=len(text), baseline=base["score"],
                 A_roundtrip=rt["score"], A_ok=bool(rt["is_watermarked"]),
                 draws=n, all_same_program=all(x["same_program"] for x in recs),
                 B_mean=statistics.mean(x["b"] for x in recs), B_retained=sum(x["b_ok"] for x in recs) / n,
                 C_mean=statistics.mean(x["c"] for x in recs), C_retained=sum(x["c_ok"] for x in recs) / n)
        results.append(r)
        print(f"text {ti} ({r['chars']}c) base z={r['baseline']:.2f} | A roundtrip z={r['A_roundtrip']:.2f} "
              f"| B unparse+hints z={r['B_mean']:.2f} ret={r['B_retained']:.0%} "
              f"| C patch+hints z={r['C_mean']:.2f} ret={r['C_retained']:.0%} | same_program={r['all_same_program']}")
    more_operations.SEED_SALT = 0
    args.out.write_text(json.dumps(dict(scheme=args.scheme, results=results), indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
