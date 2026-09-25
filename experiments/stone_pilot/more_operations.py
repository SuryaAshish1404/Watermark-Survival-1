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
import hashlib
import io
import json
import random
import tokenize
from pathlib import Path

import os

CORPUS_PATH = Path(os.environ.get("WM_CORPUS") or Path(__file__).parent / "data" / "human_corpus.json")
_CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

# See human_mutations.SEED_SALT: varied only by scripts/lifecycle_draw_variance.py.
SEED_SALT = 0


def _rng(src: str) -> random.Random:
    # Stable across processes. Previously hash(src), which Python randomizes per
    # interpreter launch (draws were only stable within one process).
    digest = int(hashlib.sha256(src.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(digest + SEED_SALT)


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


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _colon_positions(src: str):
    """(line, col) of every ':' OP token, char-based."""
    out = []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.OP and t.string == ":":
            out.append(t.start)
    return out


def _char_col(lines, lineno, byte_col):
    return len(lines[lineno - 1].encode("utf-8")[:byte_col].decode("utf-8", errors="ignore"))


def patch_type_hints(src: str) -> str:
    """Same annotations as mut_add_type_hints, inserted as text edits at AST-reported
    positions (header colon located with tokenize). No reserialization: every other
    byte is untouched, so this isolates the annotations from ast.unparse()."""
    orig = ast.parse(src)
    new = ast.parse(src)
    _AddTypeHints(_rng(src)).visit(new)
    lines = src.splitlines(keepends=True)
    colons = _colon_positions(src)
    edits = []  # (line, col, text)
    for fo, fn in zip(_funcs(orig), _funcs(new)):
        for ao, an in zip(fo.args.args, fn.args.args):
            if ao.annotation is None and an.annotation is not None:
                edits.append((ao.end_lineno, _char_col(lines, ao.end_lineno, ao.end_col_offset),
                              ": " + ast.unparse(an.annotation)))
        if fo.returns is None and fn.returns is not None:
            b0 = fo.body[0]
            start = (b0.lineno, _char_col(lines, b0.lineno, b0.col_offset))
            cand = [c for c in colons if c < start and c >= (fo.lineno, 0)]
            edits.append((*cand[-1], " -> " + ast.unparse(fn.returns)))
    for line, col, text in sorted(edits, reverse=True):
        s = lines[line - 1]
        lines[line - 1] = s[:col] + text + s[col:]
    return "".join(lines)



def mut_add_type_hints_patch(src: str, repo) -> str:
    return patch_type_hints(src)


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


# --- Reserialization-free (text-patch) equivalents ------------------------------
# Each applies the same edit as its ast.unparse() sibling (same RNG draw, same content)
# but as text edits at AST-reported positions, so every other byte is untouched. Each is
# validated in scripts/verify_patch_ops.py: ast.dump(parse(patch)) == ast.dump(parse(unparse version)).

def _apply_edits(src: str, edits) -> str:
    """edits: (start_line, start_col_chars, end_line, end_col_chars, replacement); applied bottom-up."""
    lines = src.splitlines(keepends=True)
    for sl, sc, el, ec, text in sorted(edits, reverse=True):
        head = lines[sl - 1][:sc]
        tail = lines[el - 1][ec:]
        lines[sl - 1:el] = [head + text + tail]
    return "".join(lines)


def mut_add_real_docstring_patch(src: str, repo) -> str:
    orig = ast.parse(src)
    new = ast.parse(src)
    _AddDocstring(_rng(src)).visit(new)
    lines = src.splitlines(keepends=True)
    edits = []
    for fo, fn in zip(_funcs(orig), _funcs(new)):
        if ast.get_docstring(fo) is None and ast.get_docstring(fn) is not None:
            b0 = fo.body[0]
            if b0.lineno == fo.lineno:  # one-line def: no clean insertion point
                continue
            col = _char_col(lines, b0.lineno, b0.col_offset)
            doc = ast.get_docstring(fn, clean=False)
            edits.append((b0.lineno, 0, b0.lineno, 0, " " * col + '"""' + doc.replace('"""', '\\"\\"\\"') + '"""\n'))
    return _apply_edits(src, edits)


def mut_targeted_patch_patch(src: str, repo) -> str:
    sym = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
    flip = {"==": "!=", "!=": "==", "<": "<=", "<=": "<", ">": ">=", ">=": ">"}
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    for node in ast.walk(tree):  # ast.walk is BFS; the NodeTransformer is DFS pre-order
        pass
    target = None
    stack = [tree]
    while stack:  # DFS pre-order, matching NodeTransformer visit order
        n = stack.pop()
        if isinstance(n, ast.Compare) and type(n.ops[0]) in sym:
            target = n
            break
        stack.extend(reversed(list(ast.iter_child_nodes(n))))
    if target is None:
        return src
    op = sym[type(target.ops[0])]
    start = (target.left.end_lineno, _char_col(lines, target.left.end_lineno, target.left.end_col_offset))
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.OP and t.string == op and t.start >= start:
            return _apply_edits(src, [(t.start[0], t.start[1], t.end[0], t.end[1], flip[op])])
    return src


def mut_human_rename_patch(src: str, repo) -> str:
    from human_mutations import _RenameToRealIdentifiers
    orig = ast.parse(src)
    new = ast.parse(src)
    tr = _RenameToRealIdentifiers(_rng_h(src))
    tr.visit(new)
    mapping = tr.mapping
    lines = src.splitlines(keepends=True)
    edits = []
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    for n in ast.walk(orig):
        if isinstance(n, ast.Name) and n.id in mapping:
            c = _char_col(lines, n.lineno, n.col_offset)
            edits.append((n.lineno, c, n.lineno, c + len(n.id), mapping[n.id]))
        elif isinstance(n, ast.arg) and n.arg in mapping:
            c = _char_col(lines, n.lineno, n.col_offset)
            edits.append((n.lineno, c, n.lineno, c + len(n.arg), mapping[n.arg]))
        elif isinstance(n, ast.FunctionDef) and n.name in mapping:
            for i, t in enumerate(toks):
                if t.type == tokenize.NAME and t.string == "def" and t.start[0] == n.lineno:
                    nt = toks[i + 1]
                    edits.append((nt.start[0], nt.start[1], nt.end[0], nt.end[1], mapping[n.name]))
                    break
    return _apply_edits(src, edits)


def _rng_h(src: str):
    import human_mutations
    return human_mutations._rng(src)


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
