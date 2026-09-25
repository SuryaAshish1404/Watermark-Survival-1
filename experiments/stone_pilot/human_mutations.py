"""Human-sourced mutations: operations that don't just mechanically apply a tool,
but emulate what a human reviewer/refactorer might actually do to a function —
built so the *mutation content itself* isn't AI-authored.

The concern this answers: every mutation elsewhere in this project (rename to
`_v1`, minify, AST round-trip) is either a real third-party tool or a small
mechanical AST transform with no invented vocabulary. But a "human-style rename"
or "add a docstring" mutation, done naively, means an LLM (this session) writing
plausible-sounding identifier names or comments — which is exactly the kind of
mutation source an FSE reviewer should be suspicious of, symmetric to the
question already raised earlier in this project about whether mutation results
could be an artifact of the mutator being AI too.

The fix: every piece of *text content* these mutations inject (identifier names,
comments, exception type names) is copied verbatim from `data/human_corpus.json`
— real tokens mined from lutris/lutris's actual source, written by its human
contributors, not generated on the fly. Sampling which real token to use is
deterministic (seeded), not generated. The *structural* transforms (guard-clause
conversion, statement reordering, variable extraction) inject no new vocabulary
at all — they only rearrange tokens already present in the input, so there's no
content-authorship question for them either.

Run `scripts/mine_human_corpus.py` (documented below) to regenerate the corpus
from a fresh checkout; the corpus itself is committed so this module doesn't
need network/repo access to run.
"""

import ast
import hashlib
import json
import random
from pathlib import Path

import os

CORPUS_PATH = Path(os.environ.get("WM_CORPUS") or Path(__file__).parent / "data" / "human_corpus.json")
_CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

# Varied only by scripts/lifecycle_draw_variance.py, to sample the distribution of
# outcomes over different random draws of the real corpus tokens. Leave at 0 for
# ordinary runs so a given input always yields the same mutation.
SEED_SALT = 0


def _rng(src: str) -> random.Random:
    # Seeded by a stable digest of the input text: the same input gives the same
    # draw in every process. (Until 2026-09-24 this used the builtin hash(), which
    # Python randomizes per interpreter launch — so draws were only stable *within*
    # one process, and results generated before that date are not bit-reproducible
    # across runs. See BENCHMARK.md section 3.)
    digest = int(hashlib.sha256(src.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(digest + SEED_SALT)


# --- Mutations sourcing real, human-written content --------------------------

class _RenameToRealIdentifiers(ast.NodeTransformer):
    """Renames local variables and the function name to real identifiers mined
    from lutris/lutris's own source — not `_v1`/`_v2` (that's the mechanical
    rename mutation elsewhere) and not LLM-invented "descriptive" names."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.mapping: dict[str, str] = {}
        self.used: set[str] = set()

    def _new_name(self, old: str) -> str:
        if old not in self.mapping:
            pool = [n for n in _CORPUS["identifiers"] if n not in self.used]
            choice = self.rng.choice(pool)
            self.used.add(choice)
            self.mapping[old] = choice
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


def mut_human_rename(src: str, repo) -> str:
    tree = ast.parse(src)
    _RenameToRealIdentifiers(_rng(src)).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def mut_add_real_comment(src: str, repo) -> str:
    """Prepends a real comment line, copied verbatim from Lutris's own source,
    above the function — the kind of drive-by documentation a human reviewer
    leaves without touching any logic."""
    rng = _rng(src)
    comment = rng.choice(_CORPUS["comments"])
    return f"# {comment}\n{src}"


class _WrapErrorHandling(ast.NodeTransformer):
    """Wraps each function body in try/except, using a real exception type name
    mined from the repo — the kind of defensive-programming edit a human
    reviewer makes after a bug report, not a mechanical tool pass."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        exc_type = self.rng.choice(_CORPUS["except_types"])
        handler = ast.ExceptHandler(
            type=ast.Name(id=exc_type, ctx=ast.Load()),
            name=None,
            body=[ast.Raise()],
        )
        try_node = ast.Try(body=node.body, handlers=[handler], orelse=[], finalbody=[])
        node.body = [try_node]
        return node


def mut_add_error_handling(src: str, repo) -> str:
    tree = ast.parse(src)
    _WrapErrorHandling(_rng(src)).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# --- Mechanical human-refactor patterns (no injected vocabulary at all) -------

class _ExtractReturnExpression(ast.NodeTransformer):
    """Splits `return <expr>` into `<name> = <expr>; return <name>` — the single
    most common "readability" refactor a human reviewer requests in code review,
    and purely structural: reuses the function's own real name for the extracted
    variable (`result`), injecting no new vocabulary."""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        new_body = []
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value is not None and not isinstance(stmt.value, ast.Name):
                target = ast.Name(id="result", ctx=ast.Store())
                assign = ast.Assign(targets=[target], value=stmt.value)
                new_body.append(assign)
                new_body.append(ast.Return(value=ast.Name(id="result", ctx=ast.Load())))
            else:
                new_body.append(stmt)
        node.body = new_body
        return node


def mut_extract_variable(src: str, repo) -> str:
    tree = ast.parse(src)
    _ExtractReturnExpression().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _GuardClause(ast.NodeTransformer):
    """Converts `if COND:\n    return A\nelse:\n    return B` into a guard
    clause (`if COND: return A` followed by `return B` at the outer indent) —
    a real, common human refactor for reducing nesting. Purely structural."""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        new_body = []
        for stmt in node.body:
            if (
                isinstance(stmt, ast.If)
                and len(stmt.body) == 1
                and isinstance(stmt.body[0], ast.Return)
                and len(stmt.orelse) == 1
                and isinstance(stmt.orelse[0], ast.Return)
            ):
                new_body.append(ast.If(test=stmt.test, body=stmt.body, orelse=[]))
                new_body.append(stmt.orelse[0])
            else:
                new_body.append(stmt)
        node.body = new_body
        return node


def mut_guard_clause(src: str, repo) -> str:
    tree = ast.parse(src)
    _GuardClause().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _ReorderIndependentStatements(ast.NodeTransformer):
    """Swaps the order of two adjacent independent statements at the top of the
    function body (e.g. two unrelated assignments) — a real, common human
    edit-for-flow-reasons change with zero new vocabulary, purely a reordering."""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        body = node.body
        # Only reorder simple Assign statements to keep independence a safe bet
        # without doing real dependency analysis.
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if isinstance(a, ast.Assign) and isinstance(b, ast.Assign):
                a_targets = {t.id for t in a.targets if isinstance(t, ast.Name)}
                b_names_used = {n.id for n in ast.walk(b.value) if isinstance(n, ast.Name)}
                if not (a_targets & b_names_used):
                    body[i], body[i + 1] = b, a
                    break
        return node


def mut_reorder_statements(src: str, repo) -> str:
    tree = ast.parse(src)
    _ReorderIndependentStatements().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


HUMAN_MUTATIONS = [
    ("human_rename", mut_human_rename),
    ("human_add_comment", mut_add_real_comment),
    ("human_add_error_handling", mut_add_error_handling),
    ("human_extract_variable", mut_extract_variable),
    ("human_guard_clause", mut_guard_clause),
    ("human_reorder_statements", mut_reorder_statements),
]
