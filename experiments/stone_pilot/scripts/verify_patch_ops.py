"""Each text-patch op must produce the same program as its ast.unparse sibling (same draw)."""
import ast, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import human_mutations, more_operations as mo
from human_mutations import mut_human_rename

PAIRS = [("type_hints", mo.mut_add_type_hints, mo.mut_add_type_hints_patch),
         ("docstring", mo.mut_add_real_docstring, mo.mut_add_real_docstring_patch),
         ("targeted", mo.mut_targeted_patch, mo.mut_targeted_patch_patch),
         ("rename", mut_human_rename, mo.mut_human_rename_patch)]
texts = [r["generated_code"] for r in json.loads((HERE.parent / "full_battery_results.json").read_text(encoding="utf-8"))["runs"]]
bad = 0
for name, a, b in PAIRS:
    ok = n = 0
    for t in texts:
        for s in range(15):
            mo.SEED_SALT = human_mutations.SEED_SALT = s
            n += 1
            try:
                same = ast.dump(ast.parse(a(t, None))) == ast.dump(ast.parse(b(t, None)))
            except Exception as e:  # noqa: BLE001
                same = False
                print(name, "error", repr(e)[:100])
            ok += same
    print(f"{name:12s} {ok}/{n} identical programs")
    bad += n - ok
sys.exit(1 if bad else 0)
