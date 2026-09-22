"""A second wave of operations, added to cover realistic actions a human or an
AI coding agent can take that the first 22-operation battery didn't touch:

- Whitespace/line-ending changes that never go through `ast.unparse()` — the
  first battery's structural mutations all reserialize the whole tree, which
  RESULTS.md/BENCHMARK.md already flag as a confound. These two isolate pure
  formatting effects from that confound.
- Content-adding operations that weren't covered: a real docstring, real type
  hints (both sourced from `data/human_corpus.json`, same non-AI-authorship
  discipline as `human_mutations.py`).
- A genuine second-order structural refactor (extract helper function) beyond
  the existing extract-variable/guard-clause/reorder set.
- The smallest possible edit: a single-line targeted patch, the shape of most
  real code-review suggestions.
- A no-op control (file rename only, content untouched) — confirms rather than
  assumes that renaming a file doesn't affect a carrier that lives in content.
- `agent_rewrite` is NOT in this module's mutation list — it needs the live
  generation model (asking the model to paraphrase its own output), so it's
  wired directly into run_full_battery.py's run_once() as a distinct step,
  not a text-in-text-out function like everything else here.
"""

import ast
import json
import random
from pathlib import Path

CORPUS_PATH = Path(__file__).parent / "data" / "human_corpus.json"
_CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _rng(src: str) -> random.Random:
    return random.Random(hash(src) & 0xFFFFFFFF)


# --- Whitespace-only, no AST reparse -----------------------------------------

def mut_crlf_line_endings(src: str, repo) -> str:
    """Converts LF to CRLF — what `git checkout` on Windows with
    `core.autocrlf=true` does to every file, silently, on every clone."""
    return src.replace("\n", "\r\n")


def mut_tabs_to_spaces(src: str, repo) -> str:
    """Converts leading tabs to 4 spaces, line by line — the single most
    common "fix my editor settings" edit, and deliberately implemented as
    pure text replacement, not an AST round-trip, so it can't inherit
    ast_roundtrip's confound."""
    lines = src.splitlines(keepends=True)
    out = []
    for line in lines:
        stripped = line.lstrip("\t")
        n_tabs = len(line) - len(stripped)
        out.append(("    " * n_tabs) + stripped)
    return "".join(out)


# --- Content-adding, sourced from the real corpus -----------------------------

class _AddDocstring(ast.NodeTransformer):
    def __init__(self, rng: random.Random):
        self.rng = rng

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        if ast.get_docstring(node) is None:
            doc = self.rng.choice(_CORPUS["docstring_openers"])
            node.body.insert(0, ast.Expr(value=ast.Constant(value=doc)))
        return node


def mut_add_real_docstring(src: str, repo) -> str:
    """Adds a real docstring, verbatim from Lutris's own functions, as the
    first statement — the agent/human action of "document this function" —
    only when one isn't already present."""
    tree = ast.parse(src)
    _AddDocstring(_rng(src)).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


class _AddTypeHints(ast.NodeTransformer):
    def __init__(self, rng: random.Random):
        self.rng = rng

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        for arg in node.args.args:
            if arg.annotation is None and _CORPUS["param_annotations"]:
                ann = self.rng.choice(_CORPUS["param_annotations"])
                try:
                    arg.annotation = ast.parse(ann, mode="eval").body
                except SyntaxError:
                    continue
        if node.returns is None and _CORPUS["return_annotations"]:
            ann = self.rng.choice(_CORPUS["return_annotations"])
            try:
                node.returns = ast.parse(ann, mode="eval").body
            except SyntaxError:
                pass
        return node


def mut_add_type_hints(src: str, repo) -> str:
    """Adds type hints to parameters and return value, using real annotation
    expressions mined from Lutris's own type-hinted functions (258 param
    annotations, 241 return annotations available) — the single most common
    thing an AI coding agent is asked to do to legacy Python today."""
    tree = ast.parse(src)
    _AddTypeHints(_rng(src)).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# --- Structural: extract helper function --------------------------------------

class _ExtractHelperFunction(ast.NodeTransformer):
    """Moves the function's last statement into a new top-level helper
    function and replaces it with a call to that helper — the "split this
    into two functions" refactor, distinct from extracting a local variable.
    """

    def __init__(self):
        self.helper_def: ast.FunctionDef | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        if self.helper_def is not None or len(node.body) < 2:
            return node
        last = node.body[-1]
        if isinstance(last, ast.Return) and last.value is not None:
            helper_name = f"_{node.name}_helper"
            helper = ast.FunctionDef(
                name=helper_name,
                args=ast.arguments(
                    posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                    kw_defaults=[], kwarg=None, defaults=[],
                ),
                body=[ast.Return(value=last.value)],
                decorator_list=[],
                returns=None,
            )
            self.helper_def = helper
            node.body[-1] = ast.Return(
                value=ast.Call(func=ast.Name(id=helper_name, ctx=ast.Load()), args=[], keywords=[])
            )
        return node


def mut_extract_helper_function(src: str, repo) -> str:
    tree = ast.parse(src)
    transformer = _ExtractHelperFunction()
    transformer.visit(tree)
    ast.fix_missing_locations(tree)
    if transformer.helper_def is not None:
        tree.body.append(transformer.helper_def)
        ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# --- Smallest possible edit: a targeted single-line patch ---------------------

class _FlipFirstComparison(ast.NodeTransformer):
    """Flips the first comparison operator found (== -> !=, < -> <=, etc.) —
    the shape of the smallest realistic code-review suggestion: "should this
    be <= instead of <?". Touches exactly one token."""

    _FLIP = {
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
        ast.Lt: ast.LtE, ast.LtE: ast.Lt,
        ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    }

    def __init__(self):
        self.done = False

    def visit_Compare(self, node: ast.Compare):
        if not self.done and type(node.ops[0]) in self._FLIP:
            node.ops[0] = self._FLIP[type(node.ops[0])]()
            self.done = True
        return node


def mut_targeted_patch(src: str, repo) -> str:
    tree = ast.parse(src)
    _FlipFirstComparison().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# --- Control: no content change at all -----------------------------------------

def mut_file_rename_only(src: str, repo) -> str:
    """A no-op on content — the control case for "the file got renamed/moved,
    nothing inside it changed." Included explicitly rather than assumed,
    matching this project's standard of confirming trivial cases rather than
    skipping them."""
    return src


MORE_OPERATIONS = [
    ("crlf_line_endings", mut_crlf_line_endings),
    ("tabs_to_spaces", mut_tabs_to_spaces),
    ("add_real_docstring", mut_add_real_docstring),
    ("add_type_hints", mut_add_type_hints),
    ("extract_helper_function", mut_extract_helper_function),
    ("targeted_patch", mut_targeted_patch),
    ("file_rename_only", mut_file_rename_only),
]
