# STONE Mutation-Survival Pilot — Full Battery Results

Three runs are recorded in git history here. `run_pilot.py` (2026-09-21) was the
original 6-mutation smoke test. The first full-battery version covered 14
operations. **This version covers all 12 operation classes in
`scripts/mining/detectors.py`** except `transpile` and `bundle`, which are
genuinely not applicable to a pure-Python codebase (no standard tooling —
confirmed, not assumed, consistent with how the mining detectors already scope
those two to JS/TS ecosystems) — 16 operations total once history-layer variants
are counted, run **5 times** with fresh generations to report variance rather than
trust one run. Raw data: `full_battery_results.json`.

**Coverage check against the catalogue**: squash_merge ✓ (2 variants), rebase ✓,
cherry_pick ✓, fork_sync ✓, format ✓, lint_autofix ✓, transpile — N/A, bundle —
N/A, minify ✓ (2 variants), rebuild ✓, repackage ✓ (2 variants: source-preserving
and bytecode-only), republish ✓ (real wheel build). `fork_sync` and `republish`
were added in this revision after being flagged as missing.

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
| source | format | 4/5 | Breaks a real minority of runs |
| source | minify (mild) | 4/5 | Breaks a real minority of runs |
| source | ast_roundtrip | 4/5 | Breaks a real minority of runs |
| history | squash_with_reformat | 4/5 | Tracks format's rate — it composes it |
| source | lint_autofix | 5/5 | Always retained (ruff --fix made no textual change here) |
| source | rename | 5/5 | Always retained |
| source | dead_code_insert | 5/5 | Always retained |
| source | stacked_adversarial | 5/5 | Always retained, despite combining rename+dead-code+aggressive-minify+roundtrip |
| history | squash_plain, rebase_plain, cherry_pick_plain, fork_sync | 5/5 each | Always retained — none of these touch file content |
| packaging | repackage_zip_with_source | 5/5 | Always retained |
| packaging | republish_wheel | 5/5 | Always retained — a real `build`-frontend wheel ships the source unchanged |

Full per-run scores (min/mean/max) are in `full_battery_results.json`'s `summary`
block. Exact break counts vary run-to-run (an earlier battery invocation, kept in
git history, showed 2/5 and 3/5 for some of these) — see "Why format and
ast_roundtrip break sometimes" below for why that variance itself is the finding,
not noise to average away.

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
- **`cherry_pick_plain`, `rebase_plain`, `squash_plain`, `fork_sync` don't touch
  file content by construction** — git history operations alone can't threaten a
  code-embedded watermark (unlike trailers/signatures, which live in the
  metadata these operations rewrite). The pilot confirms this rather than
  assuming it, but 5/5 retained here is a foregone conclusion once the
  content is unchanged, not a robustness finding about STONE.
- **`transpile` and `bundle` are untested, deliberately** — no standard
  transpiler or bundler exists for a pure-Python codebase, so forcing a weak
  analog (as opposed to skipping honestly) would have manufactured a result
  rather than measured one. This matches how `scripts/mining/detectors.py`
  already scopes both to JS/TS ecosystems.
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
