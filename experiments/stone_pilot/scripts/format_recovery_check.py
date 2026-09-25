"""Candidate mechanism for the mid-chain 'recovery': ast.unparse rewrites style (quotes, spacing,
blank lines); ruff format rewrites it back toward the style a code model emits. If
format(unparse(x)) == format(x), formatting fully undoes the reserialization damage."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_pilot import mut_ast_roundtrip, mut_format
repo = Path(sys.argv[1])
d = json.loads((HERE.parent / "lifecycle_v2_results.json").read_text(encoding="utf-8"))["schemes"]
for scheme in ("stone", "kgw"):
    seen, same, tot, fmt_noop = set(), 0, 0, 0
    for r in d[scheme]["runs"]:
        if r.get("excluded"):
            continue
        code = r["chain"][0]["code"]
        if code in seen:
            continue
        seen.add(code)
        tot += 1
        a = mut_format(mut_ast_roundtrip(code, repo), repo)
        b = mut_format(code, repo)
        same += (a == b)
        fmt_noop += (b == code)
    print(f"{scheme}: format(unparse(x)) == format(x) in {same}/{tot}; format(x)==x (already canonical) in {fmt_noop}/{tot}")
