# STONE Mutation-Survival Pilot — Results

Run: 2026-09-21. Full config and raw output in `results.json` (committed alongside
this file — small enough to keep, and it's the actual evidence, not a derived
summary).

## Setup actually used
- **Scheme**: STONE (vendored subset, commit `bb5d809`, see `vendor/VENDORED.md`)
- **Generation model**: `bigcode/tiny_starcoder_py` (164M, CPU)
- **Config**: gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1,
  z_threshold=4.0, language=python, skipping_rule=all_pl, watermark_on_pl=False
- **Host repo**: lutris/lutris (fresh shallow clone, 2026-09-21)
- **Prompt**: a Lutris-style docstring + function signature
  (`get_game_executable_path`)

## What got generated
The model produced a short, syntactically real (if logically imperfect — it
references an undefined `game` variable) function:

```python
"""Return the absolute path to a game's installed executable, or None if the game has not been installed yet."""
def get_game_executable_path(game_id):
	if (hasattr(game, 'game')):
		return os.path.join(game.game.application_path, game.game.name + ".exe")

	return None
```

The raw generation ran to 610 characters before trailing off mid-statement (a
164M model at 160 max_new_tokens does this) — trimmed to the largest syntactically
valid prefix (270 chars) before any mutation was applied, so the pilot measures
mutation survival, not a generation-length artifact.

## Baseline sanity check
`detect_watermark` on the untouched generation: **`is_watermarked: True`,
z-score 4.91** (threshold 4.0). Passed — the pilot is measuring something real.

## Mutation results

| Mutation | Tool | z-score | Watermarked? | Outcome |
|---|---|---|---|---|
| (baseline) | — | 4.91 | ✅ | retained |
| format | `ruff format` (Lutris's real config) | 6.46 | ✅ | retained |
| lint_autofix | `ruff check --fix` (Lutris's real config) | 4.91 | ✅ | retained |
| rename | AST local-variable renaming | 7.25 | ✅ | retained |
| minify | `python-minifier` | 5.89 | ✅ | retained |
| ast_roundtrip | `ast.parse` → `ast.unparse` | 6.05 | ✅ | retained |
| composed (format→lint→rename→minify) | all four in sequence | 7.16 | ✅ | retained |

**Every mutation retained detectability in this single run.** `lint_autofix` alone
made no textual change at all (ruff's autofix had nothing to fix once formatting
was separated out — Lutris's only lint issues on this snippet were formatting,
handled by `ruff format`), which is why its score is identical to baseline.

## Why the z-score goes *up* under some mutations, not just survives
This isn't noise or a bug: STONE's detector recomputes the green/red list fresh
from the token sequence it's given — it has no memory of the original generation.
Renaming a variable or reflowing whitespace changes token IDs at the positions
STONE's hash function keys on (`hash_key * previous_token_id`), which can shift
which tokens land in the green list for the *mutated* sequence, sometimes
increasing the apparent signal. This is a real property of hash-based green-list
watermarks, not an artifact of this pilot's tooling.

## Honest limitations of this pilot
- **N=1 generated function.** One prompt, one sampling run, one repo. This is a
  proof that the measurement method works end-to-end, not a survival-rate
  estimate — Decision #11's full anticipatory-arm run explicitly requires
  repeated generations to report variance, which this pilot does not do.
- **Very short scored sequence.** ~15-20 tokens scored per mutation after
  excluding syntax tokens (STONE's `skipping_rule=all_pl` skips keywords/
  operators/delimiters). Z-scores from this few tokens are noisy; a single
  green-token flip can move the score by more than 1. The fact that every
  mutation cleared the 4.0 threshold here should not be read as "STONE is
  robust" — it should be read as "this measurement pipeline correctly re-scores
  mutated code and reports what it finds," which is the thing this pilot set
  out to prove.
- **delta=4.0 is stronger than the paper's typical range** (0.5–2.0), chosen to
  compensate for tiny_starcoder_py's noisier logits at 164M params — a pilot-only
  deviation, flagged in PLAN.md, not a recommendation for the full run.
- **No composed-operation-order derivation from real CI here** — the `composed`
  mutation's order (format→lint→rename→minify) was chosen by us for this pilot,
  not pulled from `scripts/mining`'s observed-order extraction the way Phase 5
  requires for the real study.

## What this pilot actually establishes
The full chain — vendor a real scheme unmodified, generate with a real model,
place the result in a real repo, run real mutation tools using that repo's real
config, re-run the scheme's own detector, and get a structured
retained/silently-lost classification out — works without modification to
`scripts/recovery/outcomes.py`'s taxonomy or any of the Phase 0-3 groundwork.
That was the open question; it's now closed. Scaling this to N>1, multiple
schemes, and mining-derived operation orders is Phase 4 proper, not this pilot.
