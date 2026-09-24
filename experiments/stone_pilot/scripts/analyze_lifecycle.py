"""Summary statistics for lifecycle_results.json.

Prints, per scheme: usable baselines, where each run first broke, full-chain
survivors, survival at the pre-packaging step vs the final (Windows-built)
artifact, per-step mean score, baseline-headroom vs survival, and how much of
the z-score signal the first step cost. Used to keep every doc citing the same
numbers instead of hand-copying them.

Usage: python experiments/stone_pilot/scripts/analyze_lifecycle.py [results.json]
"""

import json
import statistics
import sys
from pathlib import Path

DEFAULT = Path(__file__).parent.parent / "lifecycle_results.json"


def analyze(scheme: str, runs: list[dict]) -> dict:
    usable = [r for r in runs if not r.get("excluded")]
    out = {"scheme": scheme, "attempted": len(runs), "usable": len(usable)}
    if not usable:
        return out

    first_breaks: dict[str, int] = {}
    survivors, breakers = [], []
    pre_pkg_retained = final_retained = 0
    step_scores: dict[str, list[float]] = {}
    signal_loss = []

    for r in usable:
        chain = r["chain"]
        base = chain[0]["score"]
        steps = [c for c in chain if "outcome" in c]
        brk = next((c["step"] for c in steps if c["outcome"] != "retained"), None)
        if brk is None:
            survivors.append(base)
        else:
            breakers.append(base)
            first_breaks[brk] = first_breaks.get(brk, 0) + 1
        by_name = {c["step"]: c for c in steps}
        if by_name.get("merge_squash_with_reformat", {}).get("outcome") == "retained":
            pre_pkg_retained += 1
        if by_name.get("release_build_wheel", {}).get("outcome") == "retained":
            final_retained += 1
        for c in chain:
            if c.get("score") is not None:
                step_scores.setdefault(c["step"], []).append(c["score"])
        first = steps[0] if steps else None
        if first and base > 0 and first.get("score") is not None:
            signal_loss.append(1 - first["score"] / base)

    out.update(
        first_breaks=first_breaks,
        never_broke=len(survivors),
        pre_package_retained=pre_pkg_retained,
        final_retained=final_retained,
        survivor_baseline_mean=statistics.mean(survivors) if survivors else None,
        breaker_baseline_mean=statistics.mean(breakers) if breakers else None,
        step_means={k: statistics.mean(v) for k, v in step_scores.items()},
        type_hint_signal_loss_mean=statistics.mean(signal_loss) if signal_loss else None,
        type_hint_signal_loss_range=(min(signal_loss), max(signal_loss)) if signal_loss else None,
    )
    return out


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, sdata in data["schemes"].items():
        res = analyze(name, sdata["runs"])
        print(f"\n=== {name}: {res['usable']}/{res['attempted']} usable ===")
        if not res["usable"]:
            continue
        n = res["usable"]
        print(f"  first-break ops: {res['first_breaks']}")
        print(f"  never broke:               {res['never_broke']}/{n}")
        print(f"  retained pre-packaging:    {res['pre_package_retained']}/{n}")
        print(f"  retained at final wheel:   {res['final_retained']}/{n}")
        if res["survivor_baseline_mean"] is not None:
            print(f"  survivor baseline mean z:  {res['survivor_baseline_mean']:.2f}")
        if res["breaker_baseline_mean"] is not None:
            print(f"  breaker baseline mean z:   {res['breaker_baseline_mean']:.2f}")
        lo, hi = res["type_hint_signal_loss_range"]
        print(f"  type-hint signal loss:     mean {res['type_hint_signal_loss_mean']:.0%} (range {lo:.0%}..{hi:.0%})")
        print("  per-step mean score:")
        for step, m in res["step_means"].items():
            print(f"    {step:28s} {m:6.2f}")


if __name__ == "__main__":
    main()
