"""Mines real, human-written identifiers/comments/exception-type-names from a
local repo checkout, for use by human_mutations.py.

This is what makes the "human-style" mutations defensible as not-AI-authored:
every piece of text content those mutations inject is copied verbatim from
here, not generated per-call. Run this once against a real checkout; the
resulting corpus is committed so human_mutations.py needs no repo access at
runtime.

Usage: python experiments/stone_pilot/scripts/mine_human_corpus.py <repo_path> [--out PATH]
"""

import argparse
import ast
import json
import re
from pathlib import Path


def mine(repo_path: Path) -> dict:
    py_files = list(repo_path.rglob("*.py"))

    identifiers: set[str] = set()
    comments: list[str] = []
    except_types: set[str] = set()
    docstring_openers: list[str] = []
    param_annotations: set[str] = set()
    return_annotations: set[str] = set()

    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for m in re.finditer(r'#\s*([A-Z][a-zA-Z0-9 ,\'".\-()]{10,60})$', text, re.MULTILINE):
            c = m.group(1).strip()
            if c not in comments:
                comments.append(c)

        for m in re.finditer(r"except\s+([A-Za-z_]+)(?:\s+as\s+\w+)?\s*:", text):
            except_types.add(m.group(1).strip())

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if 3 <= len(node.id) <= 20 and node.id.islower() and node.id.isidentifier():
                    identifiers.add(node.id)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    first_line = doc.strip().split("\n")[0].strip()
                    if 8 <= len(first_line) <= 90 and first_line not in docstring_openers:
                        docstring_openers.append(first_line)
                for arg in node.args.args:
                    if arg.annotation is not None:
                        try:
                            param_annotations.add(ast.unparse(arg.annotation))
                        except Exception:
                            pass
                if node.returns is not None:
                    try:
                        return_annotations.add(ast.unparse(node.returns))
                    except Exception:
                        pass

    return {
        "source": f"{repo_path.name}, mined from a local checkout — real "
        "identifiers/comments/exception-type-names/docstrings/type-hints as "
        "written by the project's own contributors, not generated",
        "identifiers": sorted(identifiers),
        "comments": sorted(comments),
        "except_types": sorted(except_types),
        "docstring_openers": sorted(docstring_openers),
        "param_annotations": sorted(param_annotations),
        "return_annotations": sorted(return_annotations),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "data" / "human_corpus.json"
    )
    args = parser.parse_args()

    corpus = mine(args.repo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(
        f"identifiers={len(corpus['identifiers'])} "
        f"comments={len(corpus['comments'])} "
        f"except_types={len(corpus['except_types'])} "
        f"docstring_openers={len(corpus['docstring_openers'])} "
        f"param_annotations={len(corpus['param_annotations'])} "
        f"return_annotations={len(corpus['return_annotations'])} -> {args.out}"
    )


if __name__ == "__main__":
    main()
