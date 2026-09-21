# STONE Mutation-Survival Pilot — Full Battery Results

Two runs are recorded here. `run_pilot.py` (2026-09-21) was the original 6-mutation
smoke test — see the version of this file in git history for that run. This
version covers the **full operation battery** (`run_full_battery.py`), covering
every layer named in ACTION_PLAN.md's Phase 3 list, run **5 times** with fresh
generations to report variance rather than trust one run. Raw data:
`full_battery_results.json`.

## Setup
- Scheme: STONE (vendored, commit `bb5d809`)
- Model: `bigcode/tiny_starcoder_py` (164M, CPU)
- Config: gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0
- Host repo: lutris/lutris (fresh shallow clone)
- 5 independent generations from the same prompt (`do_sample=True`, so each run
  produces different code and a different scored-token count)

## Headline finding: the watermark does break, and it breaks unevenly

| Layer | Operation | Retained | Notes |
|---|---|---|---|
| source | **aggressive_minify** | **0/5** | Breaks every time — the clearest real failure |
| packaging | **rebuild_bytecode_only** | **0/5** | Breaks every time — structural, not statistical |
| source | ast_roundtrip | 2/5 | Breaks more often than not |
| source | format | 3/5 | Breaks a real minority of runs |
| history | squash_with_reformat | 3/5 | Tracks format's rate exactly — it composes it |
| source | minify (mild) | 5/5 | Always retained |
| source | rename | 5/5 | Always retained |
| source | dead_code_insert | 5/5 | Always retained |
| source | lint_autofix | 5/5 | Always retained (ruff --fix made no textual change here) |
| source | stacked_adversarial | 5/5 | Always retained, despite combining rename+dead-code+aggressive-minify+roundtrip |
| history | squash_plain, rebase_plain, cherry_pick_plain | 5/5 each | Always retained |
| packaging | repackage_zip_with_source | 5/5 | Always retained |

Full per-run scores (min/mean/max) are in `full_battery_results.json`'s `summary`
block.

## Two genuinely different ways the watermark breaks

**1. Structural destruction (packaging layer).** `rebuild_bytecode_only` compiles
the source to `.pyc` and packages only the bytecode — there is no source text left
to tokenize, so `detect_watermark` cannot even be asked the question, let alone
answer "no." This isn't a threshold failure; it's the carrier and the detector
requiring an artifact type (source text) the operation removed entirely. Every
other packaging/history operation tested preserves the `.py` source byte-for-byte
or with only benign changes, so this is the one operation in the whole battery
where the failure mode is categorical, not statistical.

**2. Statistical loss (source layer).** `aggressive_minify`, `ast_roundtrip`, and
`format` sometimes/always push the z-score below the 4.0 threshold. This is the
kind of loss the base paper (Suresh et al.) documents for identifier renaming and
dead-code insertion — except here, renaming and dead-code insertion were the two
transforms that *never* broke it (5/5 retained each), while whitespace/AST-level
rewrites and aggressive minification were the ones that did. That's worth taking
seriously as a real, if small-N, finding: for STONE specifically, the risk is
concentrated in transformations that touch non-syntax token *boundaries and
whitespace* at scale (minification strips/renames aggressively; `ast.unparse`
regenerates all formatting from scratch; `ruff format` reflows every line) —
not in the transforms the adversarial literature usually leads with (identifier
renaming).

## Why format and ast_roundtrip break sometimes, not always
This tracks generated-sequence length directly. Runs that produced longer
generations (more scored tokens after excluding syntax tokens) had far higher
baseline z-scores (up to 18.8) and survived every mutation; runs with shorter
generations had baselines close to the threshold (as low as 4.7) and a single
reformatting pass was enough to tip them under. **The dominant variable in this
battery wasn't the mutation — it was how much watermarked text existed before the
mutation ran.** This is a methodology finding as much as a robustness finding: any
survival number for a statistical code watermark is meaningless without reporting
the scored-sequence length it was measured on.

## `stacked_adversarial` staying robust looks surprising — read it carefully
Composing four transforms (dead code → rename → aggressive minify → AST
round-trip) retained the watermark 5/5, while aggressive minify *alone* broke it
5/5. This is not evidence that stacking helps. `stacked_adversarial` applies
`ast.unparse` **after** minifying, which reformats the minified code back into
normally-spaced source — the AST round-trip step re-expands what minification had
compressed, changing the token sequence yet again in a way that happened, in this
run, to land back above threshold. This is exactly the kind of order-dependent,
non-monotonic result that the brief's composed-operations requirement (Phase 5)
exists to catch — single-operation results do not compose predictably, and this
is real evidence of that, not just a claim from the brief.

## Honest limitations
- **Still N=5 generations, one model, one scheme, one repo.** Real variance
  reporting per Decision #11 would want more runs and, ideally, longer/more
  varied generations so the "sequence length dominates" confound can be
  controlled for rather than just observed.
- **`cherry_pick_plain`, `rebase_plain`, `squash_plain` don't touch file content
  by construction** — git history operations alone can't threaten a
  code-embedded watermark (unlike trailers/signatures, which live in the
  metadata these operations rewrite). The pilot confirms this rather than
  assuming it, but 5/5 retained here is a foregone conclusion once the
  content is unchanged, not a robustness finding about STONE.
- **delta=4.0** is still above the paper's typical range, for the reason
  given in PLAN.md (compensating for the tiny model's noisier logits) —
  this likely inflates every retention number here relative to STONE's
  paper-reported configuration.

## What this establishes
A concrete, reproducible answer to "when does this watermark break": aggressive
minification and bytecode-only rebuilds are the two operations in this battery
that reliably destroy STONE's signal — one statistically, one structurally — while
identifier renaming, dead-code insertion, and pure git-history rewrites do not
touch it at all, and format/AST-rewrite sit in a genuinely unstable middle
governed more by how much code exists than by what the transform does. That
instability is itself the finding worth carrying into the full Phase 4 run.
