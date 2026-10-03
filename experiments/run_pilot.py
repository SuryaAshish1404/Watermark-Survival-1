"""STONE mutation-survival pilot: the original single-scheme smoke test.

Usage: python experiments/run_pilot.py --repo <path to lutris checkout>

Generates one STONE-watermarked Python function with a small real code model,
writes it into the given repo checkout, runs it through a battery of real
mutations (ruff format, ruff --fix, AST variable renaming, minification, AST
round-trip, and a composed pipeline), and reports whether STONE's own detector
still fires after each one.
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

# Deliberately NOT done at module level: this module is imported by run_full_battery.py purely for its mutation
# helper functions, which need none of STONE's vendor tree. An unconditional
# sys.path insert + `watermark`/`utils` import here would bind those package
# names in sys.modules to the stone_watermarking tree regardless of which
# scheme family the caller actually wants, breaking markllm-family schemes
# (see schemes.py's module docstring for why the two vendor trees can't
# coexist in one process). build_stone() below imports lazily instead.
MODEL_NAME = "bigcode/tiny_starcoder_py"

STONE_KWARGS = dict(
    gamma=0.5,
    delta=4.0,
    hash_key=15485863,
    prefix_length=1,
    z_threshold=4.0,
    language="python",
    skipping_rule="all_pl",
    watermark_on_pl="False",
)

PROMPT = (
    '"""Return the absolute path to a game\'s installed executable, or None if '
    'the game has not been installed yet."""\n'
    "def get_game_executable_path(game_id):\n"
)


def build_stone():
    vendor_root = Path(__file__).parent / "vendor" / "stone_watermarking"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from utils.transformers_config import TransformersConfig
    from watermark.stone.stone import STONE

    print(f"Loading {MODEL_NAME} ...", file=sys.stderr)
    import torch as _torch
    from schemes import DEVICE, MODEL_REVISIONS
    revision = MODEL_REVISIONS[MODEL_NAME]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, revision=revision)
    _dtype = _torch.float16 if DEVICE.startswith("cuda") else _torch.float32
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, revision=revision, torch_dtype=_dtype).to(DEVICE)
    model.eval()
    transformers_config = TransformersConfig(
        model=model,
        tokenizer=tokenizer,
        vocab_size=len(tokenizer),
        device="cpu",
        max_new_tokens=160,
        do_sample=True,
        top_k=50,
        temperature=0.7,
        num_beams=1,
    )
    return STONE(transformers_config, **STONE_KWARGS)


def _largest_parseable_prefix(code: str) -> str:
    """The tiny model's generation is length-capped and often trails off
    mid-statement. Trim trailing lines until the code is valid Python, so the
    pilot measures watermark survival under mutation, not a generation-cutoff
    artifact."""
    lines = code.splitlines()
    for cut in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:cut])
        try:
            ast.parse(candidate)
            return candidate
        except SyntaxError:
            continue
    raise RuntimeError("No syntactically valid prefix found in generated code")


# --- Mutations ----------------------------------------------------------------

def mut_format(src: str, repo: Path) -> str:
    return _run_tool_stdin(["ruff", "format", "--config", str(repo / "ruff.toml"), "-"], src)


def mut_lint_autofix(src: str, repo: Path) -> str:
    return _run_tool_stdin(
        ["ruff", "check", "--config", str(repo / "ruff.toml"), "--fix", "--exit-zero", "-"], src
    )


class _RenameLocals(ast.NodeTransformer):
    """Deterministically renames local variables and the function name itself —
    the exact transformation class (identifier renaming) the base paper
    (Suresh et al.) studies as watermark-erasing."""

    def __init__(self):
        self.counter = 0
        self.mapping: dict[str, str] = {}

    def _new_name(self, old: str) -> str:
        if old not in self.mapping:
            self.counter += 1
            self.mapping[old] = f"_v{self.counter}"
        return self.mapping[old]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.name = self._new_name(node.name)
        for arg in node.args.args:
            arg.arg = self._new_name(arg.arg)
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        elif isinstance(node.ctx, ast.Store):
            node.id = self._new_name(node.id)
        return node


def mut_rename(src: str, repo: Path) -> str:
    tree = ast.parse(src)
    _RenameLocals().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def mut_minify(src: str, repo: Path) -> str:
    import python_minifier

    return python_minifier.minify(src, rename_locals=True, rename_globals=False)


def mut_ast_roundtrip(src: str, repo: Path) -> str:
    return ast.unparse(ast.parse(src))


def mut_composed(src: str, repo: Path) -> str:
    out = mut_format(src, repo)
    out = mut_lint_autofix(out, repo)
    out = mut_rename(out, repo)
    out = mut_minify(out, repo)
    return out


MUTATIONS = [
    ("format", mut_format),
    ("lint_autofix", mut_lint_autofix),
    ("rename", mut_rename),
    ("minify", mut_minify),
    ("ast_roundtrip", mut_ast_roundtrip),
    ("composed", mut_composed),
]


def _run_tool_stdin(cmd: list[str], src: str) -> str:
    result = subprocess.run(
        cmd, input=src, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr}")
    return result.stdout


# --- Pilot driver ---------------------------------------------------------------

def classify(is_watermarked: bool, parse_ok: bool) -> str:
    if not parse_ok:
        return "build_failure (outside the 3-way taxonomy — code no longer parses)"
    return "retained" if is_watermarked else "silently_lost"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="Path to a lutris checkout")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "results.json")
    args = parser.parse_args()

    stone = build_stone()

    print("Generating watermarked function ...", file=sys.stderr)
    generated = stone.generate_watermarked_text(PROMPT)
    generated_code = _largest_parseable_prefix(generated)
    print(f"Trimmed to {len(generated_code)}/{len(generated)} chars (largest parseable prefix)", file=sys.stderr)

    baseline = stone.detect_watermark(generated_code)
    print(f"Baseline (raw generation): {baseline}", file=sys.stderr)

    target_file = args.repo / "lutris" / "mark_pilot_watermarked.py"
    target_file.write_text(generated_code, encoding="utf-8")
    print(f"Wrote generated function to {target_file}", file=sys.stderr)

    results = {
        "model": MODEL_NAME,
        "stone_config": STONE_KWARGS,
        "prompt": PROMPT,
        "generated_code": generated_code,
        "baseline": baseline,
        "mutations": [],
    }

    for name, fn in MUTATIONS:
        entry = {"mutation": name}
        try:
            mutated = fn(generated_code, args.repo)
            parse_ok = True
            try:
                ast.parse(mutated)
            except SyntaxError as e:
                parse_ok = False
                entry["syntax_error"] = str(e)
            detection = stone.detect_watermark(mutated) if parse_ok else {"is_watermarked": False, "score": None}
            entry.update(
                {
                    "code": mutated,
                    "is_watermarked": detection["is_watermarked"],
                    "score": detection["score"],
                    "parse_ok": parse_ok,
                    "outcome": classify(bool(detection["is_watermarked"]), parse_ok),
                }
            )
        except Exception as e:  # noqa: BLE001
            entry.update({"error": str(e), "outcome": "tool_error"})
        results["mutations"].append(entry)
        print(f"  {name:14s} -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)

    args.out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
