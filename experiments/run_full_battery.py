"""Full operation battery for the STONE mutation-survival pilot.

Extends run_pilot.py's 6-mutation smoke test to cover every operation class named
in the study's operation taxonomy — history layer (squash, rebase,
cherry-pick, done as literal git operations, not just text diffs), source layer
(format, lint_autofix, minify — plus dead-code insertion and a stacked-adversarial
combo from the base paper's threat model), and packaging layer (bytecode
compilation, source-preserving vs. bytecode-only repackaging).

The battery is designed to find where the watermark breaks, so it includes
operations (bytecode compilation) known to be structurally destructive to any
source-level watermark.

Usage: python experiments/run_full_battery.py --repo <lutris checkout>
"""

import argparse
import ast
import json
import py_compile
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from run_pilot import (  # noqa: E402
    _largest_parseable_prefix,
    mut_format,
    mut_lint_autofix,
    mut_minify,
    mut_ast_roundtrip,
    _RenameLocals,
)
from schemes import MODEL_NAME, MODEL_REVISION, SCHEME_KWARGS, build_scheme, assert_single_family  # noqa: E402

PROMPT = (
    '"""Utilities for locating a game\'s installed executable and save-data '
    'directory on disk."""\n'
    "import os\n\n\n"
    "def get_game_executable_path(game_id):\n"
    '    """Return the absolute path to the executable for the given game id, '
    'or None if not installed."""\n'
)


def mut_rename(src: str, repo: Path) -> str:
    tree = ast.parse(src)
    _RenameLocals().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _InsertDeadCode(ast.NodeTransformer):
    """Inserts semantically inert statements at the top of every function body —
    the dead-code-insertion transform class the base paper (Suresh et al.)
    studies as watermark-erasing, alongside identifier renaming."""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        dead = ast.parse("if False:\n    pass\n_unused_marker = 0\n").body
        node.body = dead + node.body
        return node


def mut_dead_code_insert(src: str, repo: Path) -> str:
    tree = ast.parse(src)
    _InsertDeadCode().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def mut_aggressive_minify(src: str, repo: Path) -> str:
    import python_minifier

    return python_minifier.minify(
        src,
        rename_locals=True,
        rename_globals=True,
        remove_literal_statements=True,
        remove_annotations=True,
        remove_asserts=True,
        remove_debug=True,
        combine_imports=True,
    )


def mut_stacked_adversarial(src: str, repo: Path) -> str:
    """Everything at once: dead code -> rename -> aggressive minify -> AST
    round-trip. Modeled on the base paper's approach of composing transformation
    classes rather than testing them one at a time, since single transforms are
    the easy case."""
    out = mut_dead_code_insert(src, repo)
    out = mut_rename(out, repo)
    out = mut_aggressive_minify(out, repo)
    out = mut_ast_roundtrip(out, repo)
    return out


from human_mutations import HUMAN_MUTATIONS  # noqa: E402
from more_operations import MORE_OPERATIONS  # noqa: E402

CONTENT_MUTATIONS = [
    ("format", mut_format),
    ("lint_autofix", mut_lint_autofix),
    ("rename", mut_rename),
    ("dead_code_insert", mut_dead_code_insert),
    ("minify", mut_minify),
    ("aggressive_minify", mut_aggressive_minify),
    ("ast_roundtrip", mut_ast_roundtrip),
    ("stacked_adversarial", mut_stacked_adversarial),
    *HUMAN_MUTATIONS,
    *MORE_OPERATIONS,
]


# --- History layer: literal git operations --------------------------------------

def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def _init_git_scenario(tmp: Path, watermarked_code: str) -> Path:
    repo = tmp / "history_repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "pilot@example.test")
    _git(repo, "config", "user.name", "Pilot")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / "mark_pilot_watermarked.py").write_text(watermarked_code, encoding="utf-8", newline="")
    (repo / "unrelated.py").write_text("x = 1\n", encoding="utf-8", newline="")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base: add watermarked module")
    return repo


def git_squash_plain(watermarked_code: str, tmp: Path) -> str:
    """Feature branch: two commits touching the file, both no-op-adjacent
    (comment-only additions), squash-merged into main. Content-identical case —
    the baseline for what git-layer operations do to a code-embedded mark."""
    repo = _init_git_scenario(tmp, watermarked_code)
    _git(repo, "checkout", "-q", "-b", "feature")
    path = repo / "mark_pilot_watermarked.py"
    path.write_text(watermarked_code + "\n# reviewed by teammate\n", encoding="utf-8", newline="")
    _git(repo, "commit", "-q", "-am", "review: add note")
    path.write_text(watermarked_code + "\n# reviewed by teammate\n# approved\n", encoding="utf-8", newline="")
    _git(repo, "commit", "-q", "-am", "review: approve")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--squash", "feature")
    _git(repo, "commit", "-q", "-m", "squash: merge feature")
    return path.read_bytes().decode("utf-8")


def git_squash_with_reformat(watermarked_code: str, tmp: Path, repo_cfg: Path) -> str:
    """Realistic case: the squashed feature branch's last commit is a reviewer's
    reformat pass (ruff format), not a no-op — this is what actually happens in
    review workflows, unlike the plain no-op case above."""
    repo = _init_git_scenario(tmp, watermarked_code)
    _git(repo, "checkout", "-q", "-b", "feature")
    path = repo / "mark_pilot_watermarked.py"
    reformatted = mut_format(watermarked_code, repo_cfg)
    path.write_text(reformatted, encoding="utf-8", newline="")
    _git(repo, "commit", "-q", "-am", "style: reformat")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--squash", "feature")
    _git(repo, "commit", "-q", "-m", "squash: merge feature (reformatted)")
    return path.read_bytes().decode("utf-8")


def git_rebase_plain(watermarked_code: str, tmp: Path) -> str:
    """Feature branch rebased onto main after main advances with an unrelated
    file — no conflict, watermarked file untouched by the rebase itself."""
    repo = _init_git_scenario(tmp, watermarked_code)
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "feature_only.py").write_text("y = 2\n", encoding="utf-8", newline="")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "feature: add unrelated file")
    _git(repo, "checkout", "-q", "main")
    (repo / "unrelated.py").write_text("x = 2\n", encoding="utf-8", newline="")
    _git(repo, "commit", "-q", "-am", "main: advance unrelated file")
    _git(repo, "checkout", "-q", "feature")
    _git(repo, "rebase", "-q", "main")
    return (repo / "mark_pilot_watermarked.py").read_bytes().decode("utf-8")


def git_cherry_pick_plain(watermarked_code: str, tmp: Path) -> str:
    """Cherry-pick the commit introducing the watermarked file onto a fresh
    branch with different history."""
    repo = _init_git_scenario(tmp, watermarked_code)
    base_commit = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-q", "--orphan", "other")
    _git(repo, "rm", "-rf", "-q", ".")
    (repo / "other_base.py").write_text("z = 3\n", encoding="utf-8", newline="")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "other: unrelated root commit")
    _git(repo, "cherry-pick", base_commit)
    return (repo / "mark_pilot_watermarked.py").read_bytes().decode("utf-8")


def git_fork_sync(watermarked_code: str, tmp: Path) -> str:
    """Fork = a second clone with its own history; sync = pulling upstream's new
    commits into the fork via merge, the operation `fork_sync` in
    scripts/mining/detectors.py actually detects in CI configs. Upstream adds an
    unrelated commit after the fork point; the fork merges it in."""
    upstream = _init_git_scenario(tmp / "upstream", watermarked_code)
    fork = tmp / "fork"
    _git(tmp, "clone", "-q", str(upstream), str(fork))
    _git(fork, "config", "user.email", "pilot@example.test")
    _git(fork, "config", "user.name", "Pilot")
    (upstream / "upstream_only.py").write_text("w = 4\n", encoding="utf-8", newline="")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-q", "-m", "upstream: unrelated advance")
    _git(fork, "pull", "-q", "origin", "main")
    return (fork / "mark_pilot_watermarked.py").read_bytes().decode("utf-8")


# --- Packaging layer -------------------------------------------------------------

def build_bytecode(watermarked_code: str, tmp: Path) -> Path:
    src_path = tmp / "mark_pilot_watermarked.py"
    src_path.write_text(watermarked_code, encoding="utf-8", newline="")
    pyc_path = tmp / "mark_pilot_watermarked.pyc"
    py_compile.compile(str(src_path), cfile=str(pyc_path), doraise=True)
    return pyc_path


def repackage_zip_with_source(watermarked_code: str, tmp: Path) -> Path:
    zpath = tmp / "package_with_source.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("pkg/mark_pilot_watermarked.py", watermarked_code)
    return zpath


def repackage_zip_bytecode_only(watermarked_code: str, tmp: Path) -> Path:
    pyc_path = build_bytecode(watermarked_code, tmp)
    zpath = tmp / "package_bytecode_only.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(pyc_path, "pkg/mark_pilot_watermarked.pyc")
    return zpath


_PYPROJECT_TEMPLATE = """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mark-pilot-republish-test"
version = "0.0.1"

[tool.setuptools]
py-modules = ["mark_pilot_watermarked"]
"""


def republish_build_wheel(watermarked_code: str, tmp: Path) -> Path:
    """Real `republish`: builds an actual wheel with the standard PyPA `build`
    frontend + setuptools backend — the operation scripts/mining/detectors.py
    detects via `npm publish|pypi|twine upload|...` in real CI configs. Returns
    the built .whl path; the driver extracts the shipped .py from inside it."""
    pkg_dir = tmp / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "pyproject.toml").write_text(_PYPROJECT_TEMPLATE, encoding="utf-8", newline="")
    (pkg_dir / "mark_pilot_watermarked.py").write_text(watermarked_code, encoding="utf-8", newline="")
    dist_dir = tmp / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(pkg_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"build --wheel failed: {result.stderr[-2000:]}")
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"no wheel produced: {result.stdout[-2000:]}")
    return wheels[0]


# --- Driver ------------------------------------------------------------------------

def classify(is_watermarked, parse_ok, source_available):
    if not source_available:
        return "destroyed_no_source (structurally undetectable — not a threshold question)"
    if not parse_ok:
        return "build_failure (outside the 3-way taxonomy — code no longer parses)"
    return "retained" if is_watermarked else "silently_lost"


def run_content_mutation(stone, name, fn, generated_code, repo_cfg, results):
    entry = {"mutation": name, "layer": "source"}
    try:
        mutated = fn(generated_code, repo_cfg)
        parse_ok = True
        try:
            ast.parse(mutated)
        except SyntaxError as e:
            parse_ok = False
            entry["syntax_error"] = str(e)
        detection = (
            stone.detect_watermark(mutated) if parse_ok else {"is_watermarked": False, "score": None}
        )
        entry.update(
            {
                "code": mutated,
                "is_watermarked": detection["is_watermarked"],
                "score": detection["score"],
                "parse_ok": parse_ok,
                "outcome": classify(bool(detection["is_watermarked"]), parse_ok, True),
            }
        )
    except Exception as e:  # noqa: BLE001
        entry.update({"error": str(e), "outcome": "tool_error"})
    results.append(entry)
    print(f"  [source]    {name:24s} -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)


def run_git_op(stone, name, fn, generated_code, tmp, results, extra_args=()):
    entry = {"mutation": name, "layer": "history"}
    try:
        content = fn(generated_code, tmp, *extra_args)
        parse_ok = True
        try:
            ast.parse(content)
        except SyntaxError as e:
            parse_ok = False
            entry["syntax_error"] = str(e)
        detection = stone.detect_watermark(content) if parse_ok else {"is_watermarked": False, "score": None}
        entry.update(
            {
                "code": content,
                "content_changed": content != generated_code,
                "is_watermarked": detection["is_watermarked"],
                "score": detection["score"],
                "parse_ok": parse_ok,
                "outcome": classify(bool(detection["is_watermarked"]), parse_ok, True),
            }
        )
    except Exception as e:  # noqa: BLE001
        entry.update({"error": str(e), "outcome": "tool_error"})
    results.append(entry)
    print(f"  [history]   {name:24s} -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)


def run_packaging_op(stone, name, source_available, extractor, generated_code, tmp, results):
    entry = {"mutation": name, "layer": "packaging", "source_available": source_available}
    try:
        if source_available:
            content = extractor(generated_code, tmp)
            detection = stone.detect_watermark(content)
            entry.update(
                {
                    "code": content,
                    "is_watermarked": detection["is_watermarked"],
                    "score": detection["score"],
                    "outcome": classify(bool(detection["is_watermarked"]), True, True),
                }
            )
        else:
            extractor(generated_code, tmp)  # still build the artifact, for the record
            entry.update(
                {
                    "is_watermarked": False,
                    "score": None,
                    "outcome": classify(False, False, False),
                }
            )
    except Exception as e:  # noqa: BLE001
        entry.update({"error": str(e), "outcome": "tool_error"})
    results.append(entry)
    print(f"  [packaging] {name:24s} -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)


def _signature_only(src: str) -> str | None:
    """Returns the def line (+ docstring, if present) with the body dropped —
    what's left of a function after an agent keeps the interface but throws
    away the implementation to rewrite it. Ends with a newline and the body's
    indentation started, ready for the model to complete. None if there's no
    function to work with."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node, clean=False)
            body = [ast.Expr(value=ast.Constant(value=docstring))] if docstring else []
            body.append(ast.Pass())
            sig_only = ast.FunctionDef(
                name=node.name, args=node.args, body=body,
                decorator_list=[], returns=node.returns,
            )
            full = ast.Module(body=[sig_only], type_ignores=[])
            ast.fix_missing_locations(full)
            rendered = ast.unparse(full)
            # Drop the synthetic trailing `pass` — the model completes from
            # right after the signature/docstring, not from a `pass` token.
            return rendered.rsplit("\n    pass", 1)[0] + "\n    "
    return None


def run_agent_rewrite(stone, generated_code, repo, results):
    """Special step, not a text-in-text-out mutation like everything else in
    CONTENT_MUTATIONS: keeps only the watermarked function's signature (and
    docstring, if any), then asks the *same model* to regenerate the body
    from scratch via generate_unwatermarked_text() — no green-list bias
    applied to the new tokens. This is the most "agent-like" operation in the
    battery: a coding agent given watermarked code and asked to reimplement
    it, keeping the interface. Expected to be a categorical loss: fresh
    sampling has no reason to reproduce the specific green-list draws in the
    original."""
    entry = {"mutation": "agent_rewrite", "layer": "agent"}
    try:
        sig = _signature_only(generated_code)
        if sig is None:
            entry.update({"error": "no function found", "outcome": "tool_error"})
        else:
            rewritten = stone.generate_unwatermarked_text(sig)
            parse_ok = True
            try:
                ast.parse(rewritten)
            except SyntaxError:
                rewritten = _largest_parseable_prefix(rewritten)
                parse_ok = bool(rewritten.strip())
            detection = stone.detect_watermark(rewritten) if parse_ok and rewritten.strip() else {
                "is_watermarked": False, "score": None
            }
            entry.update(
                {
                    "code": rewritten,
                    "is_watermarked": detection["is_watermarked"],
                    "score": detection["score"],
                    "parse_ok": parse_ok,
                    "outcome": classify(bool(detection["is_watermarked"]), parse_ok, True),
                }
            )
    except Exception as e:  # noqa: BLE001
        entry.update({"error": str(e), "outcome": "tool_error"})
    results.append(entry)
    print(f"  [agent]     agent_rewrite            -> {entry.get('outcome')} (score={entry.get('score')})", file=sys.stderr)


def run_once(stone, repo: Path, run_index: int) -> dict:
    print(f"\n=== Run {run_index} ===", file=sys.stderr)
    print("Generating watermarked module ...", file=sys.stderr)
    generated = stone.generate_watermarked_text(PROMPT)
    generated_code = _largest_parseable_prefix(generated)
    print(f"Trimmed to {len(generated_code)}/{len(generated)} chars", file=sys.stderr)

    baseline = stone.detect_watermark(generated_code)
    print(f"Baseline: {baseline}", file=sys.stderr)

    results = {
        "run_index": run_index,
        "generated_code": generated_code,
        "generated_chars": len(generated_code),
        "baseline": baseline,
        "operations": [],
    }

    if not baseline["is_watermarked"]:
        # Per docs/01-outcome-definitions.md: a claim not confirmed present before
        # the operation is "never emitted," not "lost." Scoring every mutation as
        # a break here would misattribute a failed embedding to mutation damage.
        results["excluded"] = "baseline_never_emitted"
        print(
            f"  SKIPPED mutations: baseline not watermarked (score={baseline['score']}) "
            "-> excluded from aggregate, not scored as loss",
            file=sys.stderr,
        )
        return results

    target_file = repo / "lutris" / "mark_pilot_watermarked.py"
    target_file.write_text(generated_code, encoding="utf-8", newline="")
    ops = results["operations"]

    print("\n--- Source layer ---", file=sys.stderr)
    for name, fn in CONTENT_MUTATIONS:
        run_content_mutation(stone, name, fn, generated_code, repo, ops)

    print("\n--- History layer (real git operations) ---", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        run_git_op(stone, "squash_plain", lambda c, t: git_squash_plain(c, t), generated_code, tmp / "s1", ops)
        run_git_op(
            stone,
            "squash_with_reformat",
            lambda c, t: git_squash_with_reformat(c, t, repo),
            generated_code,
            tmp / "s2",
            ops,
        )
        run_git_op(stone, "rebase_plain", lambda c, t: git_rebase_plain(c, t), generated_code, tmp / "s3", ops)
        run_git_op(
            stone, "cherry_pick_plain", lambda c, t: git_cherry_pick_plain(c, t), generated_code, tmp / "s4", ops
        )
        run_git_op(stone, "fork_sync", lambda c, t: git_fork_sync(c, t), generated_code, tmp / "s5", ops)

    print("\n--- Packaging layer ---", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)

        def extract_zip_source(code, t):
            zpath = repackage_zip_with_source(code, t)
            with zipfile.ZipFile(zpath) as zf:
                return zf.read("pkg/mark_pilot_watermarked.py").decode("utf-8")

        def build_pyc_only(code, t):
            repackage_zip_bytecode_only(code, t)

        def extract_wheel_source(code, t):
            wheel_path = republish_build_wheel(code, t)
            with zipfile.ZipFile(wheel_path) as zf:
                return zf.read("mark_pilot_watermarked.py").decode("utf-8")

        run_packaging_op(stone, "repackage_zip_with_source", True, extract_zip_source, generated_code, tmp, ops)
        run_packaging_op(stone, "rebuild_bytecode_only", False, build_pyc_only, generated_code, tmp, ops)
        run_packaging_op(stone, "republish_wheel", True, extract_wheel_source, generated_code, tmp, ops)

    print("\n--- Agent layer ---", file=sys.stderr)
    run_agent_rewrite(stone, generated_code, repo, ops)

    broke = [o for o in ops if o["outcome"] != "retained"]
    print(f"\nRun {run_index}: {len(ops) - len(broke)}/{len(ops)} operations retained.", file=sys.stderr)
    for o in broke:
        print(f"  BROKE: {o['mutation']} ({o['layer']}) -> {o['outcome']}", file=sys.stderr)

    return results


def aggregate(all_runs: list[dict]) -> dict:
    """Per-operation retention rate and score spread across repeated runs — the
    'recovery variance across repeated runs' metric for statistical detectors,
    rather than trusting any single run's number."""
    by_op: dict[str, list[dict]] = {}
    for run in all_runs:
        for op in run["operations"]:
            by_op.setdefault(op["mutation"], []).append(op)

    summary = []
    for name, entries in by_op.items():
        layer = entries[0]["layer"]
        n = len(entries)
        retained = sum(1 for e in entries if e["outcome"] == "retained")
        scores = [e["score"] for e in entries if isinstance(e.get("score"), (int, float))]
        summary.append(
            {
                "mutation": name,
                "layer": layer,
                "n_runs": n,
                "retained": retained,
                "retention_rate": retained / n if n else None,
                "score_min": min(scores) if scores else None,
                "score_max": max(scores) if scores else None,
                "score_mean": sum(scores) / len(scores) if scores else None,
                "distinct_outcomes": sorted({e["outcome"] for e in entries}),
            }
        )
    summary.sort(key=lambda s: (s["layer"], s["retention_rate"] if s["retention_rate"] is not None else -1))
    excluded = sum(1 for r in all_runs if r.get("excluded"))
    return {
        "n_runs": len(all_runs),
        "n_excluded_baseline_never_emitted": excluded,
        "n_scored_runs": len(all_runs) - excluded,
        "per_operation": summary,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="Path to a lutris checkout (for real ruff config)")
    parser.add_argument("--runs", type=int, default=1, help="Number of repeated generations to run, per scheme")
    parser.add_argument(
        "--schemes", type=str, default="stone", help="Comma-separated scheme names: stone,kgw,sweet,ewd"
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "full_battery_results.json")
    parser.add_argument(
        "--fresh", action="store_true",
        help="Overwrite --out instead of merging into it. Default merges, so each "
             "scheme can be run as its own process invocation (see run_all_schemes.sh) "
             "without one long-lived process accumulating memory across schemes.",
    )
    args = parser.parse_args()

    scheme_names = [s.strip() for s in args.schemes.split(",") if s.strip()]
    assert_single_family(scheme_names)  # raises early, not mid-battery, if families are mixed

    print(f"Loading {MODEL_NAME} (shared across schemes) ...", file=sys.stderr)
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

    def _save(by_scheme):
        output = {"model": MODEL_NAME, "prompt": PROMPT, "schemes": by_scheme}
        args.out.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    for scheme_name in scheme_names:
        print(f"\n########## SCHEME: {scheme_name} ##########", file=sys.stderr)
        scheme = build_scheme(scheme_name, model, tokenizer)
        all_runs = []
        # Written after every run, not just after a scheme (or the whole battery)
        # completes, so a crash partway through a scheme keeps every
        # already-finished run's structured data.
        for i in range(1, args.runs + 1):
            all_runs.append(run_once(scheme, args.repo, i))
            by_scheme[scheme_name] = {
                "scheme_config": SCHEME_KWARGS[scheme_name],
                "runs": all_runs,
                "summary": aggregate(all_runs),
            }
            _save(by_scheme)

        summary = by_scheme[scheme_name]["summary"]
        print(
            f"\n=== {scheme_name}: summary across {summary['n_runs']} run(s) "
            f"({summary['n_excluded_baseline_never_emitted']} excluded: baseline never emitted) ===",
            file=sys.stderr,
        )
        for s in summary["per_operation"]:
            print(
                f"  [{s['layer']:9s}] {s['mutation']:24s} "
                f"{s['retained']}/{s['n_runs']} retained  "
                f"score[min={s['score_min']}, mean={s['score_mean']}, max={s['score_max']}]  "
                f"outcomes={s['distinct_outcomes']}",
                file=sys.stderr,
            )

    print(f"\nWrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
