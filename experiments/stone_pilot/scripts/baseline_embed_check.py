"""Repeated baseline-embedding check: for each requested scheme, generate N times
and record whether a detectable watermark was produced. Loads the model once per
process, so schemes must all belong to the same vendor family (see schemes.py).

Usage: python scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from schemes import DEVICE, MODEL_NAME, assert_single_family, build_scheme

PROMPTS = [
    ('"""Utilities for locating a game\'s installed executable and save-data '
     'directory on disk."""\nimport os\n\n\ndef get_game_executable_path(game_id):\n'
     '    """Return the absolute path to the executable for the given game id, '
     'or None if not installed."""\n'),
    ('"""Helpers for reading and validating a launcher configuration file."""\n'
     'import json\n\n\ndef load_config(path):\n    """Load the JSON configuration at '
     'path and return it as a dict, raising ValueError if it is malformed."""\n'),
    ('"""Small utilities for formatting and parsing playtime values."""\nimport re\n\n\n'
     'def parse_playtime(text):\n    """Convert a string such as "3h 20m" into a total '
     'number of minutes."""\n'),
    ('"""Filesystem helpers for managing per-game cache directories."""\nimport os\n\n\n'
     'def clean_cache_dir(cache_dir, max_age_days):\n    """Delete files in cache_dir '
     'older than max_age_days and return the number of files removed."""\n'),
    ('"""Networking helpers used when downloading game installers."""\nimport hashlib\n\n\n'
     'def verify_checksum(file_path, expected_sha256):\n    """Return True if the SHA-256 '
     'digest of the file at file_path matches expected_sha256."""\n'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemes", required=True, help="comma-separated, one vendor family")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    names = [s.strip() for s in args.schemes.split(",") if s.strip()]
    assert_single_family(names)

    dtype = torch.float16 if DEVICE.startswith("cuda") else torch.float32
    print(f"Loading {MODEL_NAME} on {DEVICE} ...", file=sys.stderr)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(DEVICE)
    model.eval()

    results = {}
    for name in names:
        sch = build_scheme(name, model, tok)
        runs = []
        for i in range(args.n):
            prompt = PROMPTS[i % len(PROMPTS)]
            try:
                gen = sch.generate_watermarked_text(prompt)
                det = sch.detect_watermark(gen)
                runs.append(dict(i=i, chars=len(gen), score=det.get("score"),
                                  is_watermarked=bool(det.get("is_watermarked"))))
            except Exception as e:  # noqa: BLE001
                runs.append(dict(i=i, error=repr(e)[:300]))
        n_ok = sum(r.get("is_watermarked") is True for r in runs)
        n_err = sum("error" in r for r in runs)
        scores = [r["score"] for r in runs if r.get("score") is not None]
        results[name] = dict(runs=runs, detected=n_ok, total=len(runs), errors=n_err,
                             mean_score=(sum(scores) / len(scores) if scores else None))
        print(f"{name:10s} detected {n_ok}/{len(runs)}  errors {n_err}  "
              f"mean_score={results[name]['mean_score']}", file=sys.stderr)

    out = args.out or (Path(__file__).resolve().parent.parent /
                        f"baseline_embed_{'_'.join(names)}.json")
    out.write_text(json.dumps({"model": MODEL_NAME, "results": results}, indent=2), encoding="utf-8")
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
