"""Full-SDLC-cycle chain: cumulative survival, not independent single operations.

Every other script in this project mutates the *original* watermarked baseline
once, independently, per operation — 30 separate branches off one root. That
answers "does operation X break it in isolation" but not the brief's actual
Phase 5 ask: "Test realistic chains such as: AI-generated code -> commit -> PR
-> squash -> formatting -> build -> package -> release. Measure cumulative
survival rather than only individual operations."

This script applies one realistic step order, *in sequence*, and re-checks
detection after every single step — so degradation (or survival) compounds
the way it actually would in a real release pipeline, not the way 30
independent what-if branches do.

The order below is a plausible real-world sequence (write -> polish -> review
-> merge -> CI -> release), not mined from observed CI configs the way
scripts/mining/workflow_order.py derives real orders for the measured arm —
that's a real difference in evidentiary weight, disclosed here and in
RESULTS.md/BENCHMARK.md rather than presented as equally strong.

Usage: python experiments/run_lifecycle.py --repo <lutris checkout> --runs N --schemes stone,kgw
"""

import argparse
import ast
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from human_mutations import mut_add_real_comment  # noqa: E402
from more_operations import mut_add_real_docstring, mut_add_type_hints, mut_add_type_hints_patch, mut_targeted_patch  # noqa: E402
from human_mutations import mut_human_rename  # noqa: E402
from run_pilot import mut_format, mut_lint_autofix, _largest_parseable_prefix  # noqa: E402
from run_full_battery import _git, _init_git_scenario  # noqa: E402
from schemes import MODEL_NAME, MODEL_REVISION, SCHEME_KWARGS, build_scheme, assert_single_family  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

PROMPT = (
    '"""Utilities for locating a game\'s installed executable and save-data '
    'directory on disk."""\n'
    "import os\n\n\n"
    "def get_game_executable_path(game_id):\n"
    '    """Return the absolute path to the executable for the given game id, '
    'or None if not installed."""\n'
)


PROMPTS = [
    PROMPT,
    '"""Helpers for reading and validating a launcher configuration file."""\nimport json\n\n\ndef load_config(path):\n    """Load the JSON configuration at path and return it as a dict, raising ValueError if it is malformed."""\n',
    '"""Small utilities for formatting and parsing playtime values."""\nimport re\n\n\ndef parse_playtime(text):\n    """Convert a string such as "3h 20m" into a total number of minutes."""\n',
    '"""Filesystem helpers for managing per-game cache directories."""\nimport os\n\n\ndef clean_cache_dir(cache_dir, max_age_days):\n    """Delete files in cache_dir older than max_age_days and return the number of files removed."""\n',
    '"""Networking helpers used when downloading game installers."""\nimport hashlib\n\n\ndef verify_checksum(file_path, expected_sha256):\n    """Return True if the SHA-256 digest of the file at file_path matches expected_sha256."""\n',
]


def _git_squash_current_content(content: str, tmp: Path, repo_cfg: Path) -> str:
    """Squash-merges a feature branch whose final commit is the *given*
    (already-mutated) content — unlike run_full_battery.py's
    git_squash_with_reformat, which always starts from a fresh, unmutated
    generation. This is what makes it usable mid-chain.

    Reformats on the feature branch before merging (matching real review
    workflows) but only commits that pass if it actually changed something —
    by the time this step runs, `ci_format` has usually already run earlier
    in the chain, so a second `ruff format` pass is frequently a no-op, and
    `git commit` fails ("nothing to commit") if forced regardless."""
    repo = _init_git_scenario(tmp, content)
    _git(repo, "checkout", "-q", "-b", "feature")
    path = repo / "mark_pilot_watermarked.py"
    reformatted = mut_format(content, repo_cfg)
    if reformatted != content:
        path.write_text(reformatted, encoding="utf-8", newline="")
        _git(repo, "commit", "-q", "-am", "style: reformat before merge")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--squash", "feature")
    status = _git(repo, "status", "--porcelain")
    if status.strip():
        _git(repo, "commit", "-q", "-m", "squash: merge feature")
    return path.read_bytes().decode("utf-8")


def _build_wheel_current_content(content: str, tmp: Path) -> str:
    from run_full_battery import republish_build_wheel
    import zipfile

    wheel_path = republish_build_wheel(content, tmp)
    with zipfile.ZipFile(wheel_path) as zf:
        return zf.read("mark_pilot_watermarked.py").decode("utf-8")


LIFECYCLE_STEPS = [
    # (step name, kind, callable)  kind in {"text", "git", "package"}
    ("agent_add_type_hints", "text", mut_add_type_hints),
    ("agent_add_docstring", "text", mut_add_real_docstring),
    ("review_targeted_patch", "text", mut_targeted_patch),
    ("review_rename", "text", mut_human_rename),
    ("review_add_comment", "text", mut_add_real_comment),
    ("ci_format", "text", mut_format),
    ("ci_lint_autofix", "text", mut_lint_autofix),
    ("merge_squash_with_reformat", "git", _git_squash_current_content),
    ("release_build_wheel", "package", _build_wheel_current_content),
]


def steps_for(hints: str):
    """hints='unparse' is the original chain; 'patch' swaps step 1 for the same annotations
    inserted by targeted text patch (no ast.unparse reserialization)."""
    if hints == "unparse":
        return LIFECYCLE_STEPS
    return [("agent_add_type_hints_patch", "text", mut_add_type_hints_patch)] + LIFECYCLE_STEPS[1:]


def classify(is_watermarked: bool, parse_ok: bool) -> str:
    if not parse_ok:
        return "build_failure"
    return "retained" if is_watermarked else "silently_lost"


def _apply_steps(stone, content: str, repo_cfg: Path, steps, chain: list) -> str:
    for step_name, kind, fn in steps:
        entry = {"step": step_name}
        try:
            with tempfile.TemporaryDirectory() as tmp_str:
                tmp = Path(tmp_str)
                if kind == "text":
                    content = fn(content, repo_cfg)
                elif kind == "git":
                    content = fn(content, tmp, repo_cfg)
                elif kind == "package":
                    content = fn(content, tmp)

            parse_ok = True
            try:
                ast.parse(content)
            except SyntaxError as e:
                parse_ok = False
                entry["syntax_error"] = str(e)

            detection = stone.detect_watermark(content) if parse_ok else {"is_watermarked": False, "score": None}
            entry.update(
                {
                    "score": detection["score"],
                    "is_watermarked": detection["is_watermarked"],
                    "outcome": classify(bool(detection["is_watermarked"]), parse_ok),
                    "chars": len(content),
                }
            )
        except Exception as e:  # noqa: BLE001
            entry.update({"error": str(e), "outcome": "tool_error"})
        chain.append(entry)
        print(f"  after {step_name:28s} -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)
    return content


def run_chain(stone, repo_cfg: Path, run_index: int, hints: str = "unparse", prompt_id: int = 0) -> dict:
    """hints in {unparse, patch, both}. 'both' runs the two first-step variants from the
    SAME generated baseline (matched design); the patch chain is stored as chain_patch."""
    print(f"\n=== Lifecycle run {run_index} (prompt {prompt_id}, hints={hints}) ===", file=sys.stderr)
    generated = stone.generate_watermarked_text(PROMPTS[prompt_id])
    content = _largest_parseable_prefix(generated)
    print(f"Generated {len(content)} chars", file=sys.stderr)

    baseline = stone.detect_watermark(content)
    print(f"Step 0 (baseline): {baseline}", file=sys.stderr)

    def fresh_chain():
        return [{"step": "baseline", "score": baseline["score"], "is_watermarked": baseline["is_watermarked"], "code": content}]

    rec = {"run_index": run_index, "prompt_id": prompt_id, "chain": fresh_chain()}
    if not baseline["is_watermarked"]:
        rec["excluded"] = "baseline_never_emitted"
        return rec

    variants = {"unparse": "chain", "patch": "chain_patch"}
    which = ["unparse", "patch"] if hints == "both" else [hints]
    if hints == "patch":
        variants = {"patch": "chain"}
    for v in which:
        chain = rec["chain"] if variants[v] == "chain" else fresh_chain()
        final = _apply_steps(stone, content, repo_cfg, steps_for(v), chain)
        chain.append({"step": "final_code", "code": final})
        rec[variants[v]] = chain
    return rec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--schemes", type=str, default="stone")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "lifecycle_results.json")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--multi-prompt", action="store_true", help="cycle run i over 5 distinct prompts")
    parser.add_argument("--hints", choices=["unparse", "patch", "both"], default="unparse")
    args = parser.parse_args()

    scheme_names = [s.strip() for s in args.schemes.split(",") if s.strip()]
    assert_single_family(scheme_names)

    print(f"Loading {MODEL_NAME} ...", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, revision=MODEL_REVISION)
    import torch as _torch
    from schemes import DEVICE
    _dtype = _torch.float16 if DEVICE.startswith("cuda") else _torch.float32
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, revision=MODEL_REVISION, torch_dtype=_dtype).to(DEVICE)
    model.eval()

    by_scheme = {}
    if not args.fresh and args.out.exists():
        try:
            by_scheme = json.loads(args.out.read_text(encoding="utf-8")).get("schemes", {})
        except (json.JSONDecodeError, OSError):
            by_scheme = {}

    def _save():
        args.out.write_text(
            json.dumps({"model": MODEL_NAME, "steps": [s[0] for s in steps_for("unparse" if args.hints != "patch" else "patch")], "schemes": by_scheme}, indent=2, default=str),
            encoding="utf-8",
        )

    for scheme_name in scheme_names:
        print(f"\n########## SCHEME: {scheme_name} ##########", file=sys.stderr)
        scheme = build_scheme(scheme_name, model, tokenizer)
        runs = []
        for i in range(1, args.runs + 1):
            runs.append(run_chain(scheme, args.repo, i, args.hints, (i - 1) % len(PROMPTS) if args.multi_prompt else 0))
            by_scheme[scheme_name] = {"scheme_config": SCHEME_KWARGS[scheme_name], "runs": runs}
            _save()

        # How far did each run get before first breaking?
        scored = [r for r in runs if not r.get("excluded")]
        print(f"\n=== {scheme_name}: {len(scored)}/{len(runs)} runs had a usable baseline ===", file=sys.stderr)
        for r in scored:
            steps = [c for c in r["chain"] if "outcome" in c]
            first_break = next((c["step"] for c in steps if c["outcome"] != "retained"), None)
            print(
                f"  run {r['run_index']}: "
                + (f"first broke at '{first_break}'" if first_break else "survived the entire chain"),
                file=sys.stderr,
            )

    print(f"\nWrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
