"""Every number reported in the paper, recomputed from the committed result files.

Reads only experiments/results/*.json; loads no model and runs no experiment.
Numbers that need an external tool are produced by their own scripts:
  - AST-equivalence check (75/75 per operation): scripts/verify_patch_ops.py
  - format(unparse(x)) == format(x) check:        scripts/format_recovery_check.py
  - observed lint/format order (281, 29 vs 15):   scripts/mine_ci_order.py

Usage: python experiments/scripts/paper_numbers.py
"""

import json
import random
import statistics as st
from collections import Counter
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
ORDER = "format_then_lint"  # CI order behind the reported lifecycle values


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def pct(x):
    return f"{100 * x:.1f}%"


def boot_ci(values, n=2000, seed=0):
    """Percentile bootstrap over baselines, as in scripts/offline_matrix.py."""
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def score(baseline):
    return baseline["score"] if isinstance(baseline, dict) else baseline


def usable(runs):
    return [r for r in runs if not r.get("excluded")]


def section(title):
    print(f"\n=== {title} ===")


def compatibility():
    section("Table: baseline compatibility (usable / attempted)")
    lifecycle = load("lifecycle_results.json")["schemes"]
    deepseek = {}
    for f in ("baseline_embed_stone_kgw_sweet_ewd.json",
              "baseline_embed_unigram_unbiased_dip_synthid_pf.json"):
        deepseek.update(load(f)["results"])
    small, large = [], []
    for scheme in ("stone", "kgw", "sweet", "ewd", "unigram", "unbiased", "dip", "synthid", "pf"):
        runs = lifecycle[scheme]["runs"]
        u, n = len(usable(runs)), len(runs)
        d = deepseek[scheme]
        small.append(u / n)
        large.append(d["detected"] / d["total"])
        print(f"  {scheme:9s} 164M {u}/{n} ({u / n:.0%})   1.3B {d['detected']}/{d['total']} "
              f"({d['detected'] / d['total']:.0%})")
    print(f"  Pearson r, 164M vs 1.3B compatibility: {st.correlation(small, large):.2f}")


def deepseek_single_prompt():
    section("DeepSeek single-prompt check (gpu_battery_results.json)")
    schemes = load("gpu_battery_results.json")["schemes"]
    for scheme in ("stone", "kgw"):
        runs = schemes[scheme]["runs"]
        z = [score(r["baseline"]) for r in usable(runs)]
        line = f"  {scheme:5s} usable {len(z)}/{len(runs)}"
        if z:
            line += f", mean baseline z {st.mean(z):.1f}, range {min(z):.1f}-{max(z):.1f}"
        print(line)


def lifecycle_counts():
    section("Lifecycle runs and distinct baselines (lifecycle_v2_results.json)")
    schemes = load("lifecycle_v2_results.json")["schemes"]
    for scheme in ("stone", "kgw"):
        runs = usable(schemes[scheme]["runs"])
        distinct = {r["chain"][0]["code"] for r in runs}
        print(f"  {scheme:5s} {len(runs)} usable runs, {len(distinct)} distinct baselines")


def controlled_comparison(corpus=""):
    label = "Flask corpus" if corpus else "lutris corpus"
    section(f"RQ1/RQ3: controlled comparison, {label} (offline_matrix_*.json, {ORDER})")
    for scheme in ("stone", "kgw"):
        data = load(f"offline_matrix_{corpus}{scheme}.json")
        cells, summary = data["cells"], data["summary"]
        print(f"  {scheme.upper()} ({data['n_baselines']} baselines, {data['draws']} draws each)")
        for chain, name in (("unparse_chain", "reserialization"), ("patch_chain", "targeted patch"),
                            ("roundtrip_only", "single unparse")):
            key = f"{chain}|{ORDER}"
            c = cells[key]
            cont = [x["never_broke"] for x in c]
            lo, hi = boot_ci(cont)
            norm = st.mean(x["end_z"] / x["baseline_z"] for x in c)
            print(f"    {name:16s} continuous {pct(st.mean(cont))} [95% CI {pct(lo)}, {pct(hi)}]"
                  f"  final {pct(st.mean(x['end_retained'] for x in c))}"
                  f"  normalized final score {norm:.0%}")
        patch = {x["baseline_index"]: x["never_broke"] for x in cells[f"patch_chain|{ORDER}"]}
        diffs = [patch[x["baseline_index"]] - x["never_broke"] for x in cells[f"unparse_chain|{ORDER}"]]
        lo, hi = boot_ci(diffs)
        print(f"    paired patch-minus-reserialization difference in continuous retention: "
              f"{100 * st.mean(diffs):+.1f} pp [95% CI {100 * lo:+.1f}, {100 * hi:+.1f}]")
        other = "lint_then_format"
        delta = max(abs(summary[f"{ch}|{ORDER}"]["never_broke"] - summary[f"{ch}|{other}"]["never_broke"])
                    for ch in ("unparse_chain", "patch_chain", "roundtrip_only"))
        print(f"    max change in continuous retention when the CI order is reversed: {100 * delta:.1f} pp")


def type_hint_control():
    section("Type-hint control (unparse_control_*.json)")
    for scheme in ("stone", "kgw"):
        r = load(f"unparse_control_{scheme}.json")["results"]
        draws = sum(x["draws"] for x in r)
        identical = sum(x["draws"] for x in r if x["all_same_program"])
        print(f"  {scheme.upper()} ({len(r)} baselines): normalized score "
              f"AST round-trip {st.mean(x['A_roundtrip'] / x['baseline'] for x in r):.1%}, "
              f"type hints via unparse {st.mean(x['B_mean'] / x['baseline'] for x in r):.1%}, "
              f"via patch {st.mean(x['C_mean'] / x['baseline'] for x in r):.1%}; detection "
              f"unparse {st.mean(x['B_retained'] for x in r):.0%}, patch {st.mean(x['C_retained'] for x in r):.0%}; "
              f"identical programs {identical}/{draws}")


def live_lifecycle():
    section("Live lifecycle: step-1 loss and first break (lifecycle_v2_results.json)")
    schemes = load("lifecycle_v2_results.json")["schemes"]
    for scheme in ("kgw", "stone"):
        runs = usable(schemes[scheme]["runs"])
        for key, name in (("chain", "reserialization"), ("chain_patch", "targeted patch")):
            loss = st.mean(1 - r[key][1]["score"] / r[key][0]["score"] for r in runs)
            first = Counter(next((c["step"] for c in r[key][1:] if c.get("outcome") != "retained"), "never")
                            for r in runs)
            print(f"  {scheme.upper():5s} {name:16s} mean step-1 loss {loss:.0%}; first break {dict(first)}")
    for scheme, v in schemes.items():
        for i, r in enumerate(v["runs"]):
            chain = r.get("chain") or []
            for a, b in zip(chain, chain[1:]):
                if (a.get("score") is not None and b.get("score") is not None
                        and not a.get("is_watermarked") and b.get("is_watermarked") and b["step"] == "ci_format"):
                    print(f"  recovery example: {scheme.upper()} run {i}, {a['step']} z={a['score']:.2f} "
                          f"-> {b['step']} z={b['score']:.2f}")
                    return


def operation_level():
    section("Operation-level retention (multischeme_results.json)")
    schemes = load("multischeme_results.json")["schemes"]
    for scheme in ("stone", "kgw"):
        runs = usable(schemes[scheme]["runs"])
        counts = Counter()
        for r in runs:
            for o in r["operations"]:
                counts[o["mutation"]] += o["outcome"] == "retained"
        print(f"  {scheme.upper()} (n={len(runs)}): " + ", ".join(f"{op} {k}/{len(runs)}" for op, k in counts.items()))


def human_sourced():
    section("Human-sourced operations (human_ops_results.json)")
    schemes = load("human_ops_results.json")["schemes"]
    for scheme in ("stone", "kgw"):
        runs = usable(schemes[scheme]["runs"])
        counts = Counter()
        for r in runs:
            for o in r["operations"]:
                if o["mutation"].startswith("human_"):
                    counts[o["mutation"]] += o["outcome"] == "retained"
        print(f"  {scheme.upper()} (n={len(runs)}): " + ", ".join(f"{op[6:]} {k}/{len(runs)}" for op, k in counts.items()))


def length_correlation():
    section("RQ2: generated length vs baseline score (multischeme_results.json)")
    schemes = load("multischeme_results.json")["schemes"]
    for scheme in ("stone", "kgw"):
        runs = usable(schemes[scheme]["runs"])
        x = [r["generated_chars"] for r in runs]
        y = [score(r["baseline"]) for r in runs]
        print(f"  {scheme.upper()}: Pearson r = {st.correlation(x, y):.3f} (n = {len(runs)})")


def ci_order():
    section("Observed CI order (ci_order_results.json, from scripts/mine_ci_order.py)")
    d = load("ci_order_results.json")
    print(f"  {d['repos']} repositories, {d['job_sequences']} job sequences; lint autofix before "
          f"formatting {d['lint_autofix_before_format']} times, the reverse {d['format_before_lint_autofix']} times")


if __name__ == "__main__":
    compatibility()
    deepseek_single_prompt()
    lifecycle_counts()
    controlled_comparison()
    controlled_comparison("flask_")
    type_hint_control()
    live_lifecycle()
    operation_level()
    human_sourced()
    length_correlation()
    ci_order()
