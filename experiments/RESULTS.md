# Watermark Mutation-Survival Pilot — Results

**See `BENCHMARK.md` for the paper-ready version of everything below** — same
data, written as a citable methods+results document rather than a lab
narrative. This file keeps the full session-by-session story, including the
crash/recovery details BENCHMARK.md summarizes in one line.

## Round 2: the reserialization control, five prompts, mined CI order — 2026-09-26 (latest)

User asked to do the items that would make this paper-worthy: the `ast.unparse`
control, more prompts and a bigger model, mined CI order, a platform fix, a
rerun under the fixed RNG. Done except the bigger model (host has 1-1.7 GB free
RAM, no GPU). Full write-up: `BENCHMARK.md` §2.8. The 2026-09-24 entry below is
**partly superseded** where it conflicts (its Finding 8 attribution and its
16%-vs-92% gap in particular).

**The headline changed again.** Whole-file reserialization with `ast.unparse()`,
not the content edits, is what removes the signal.

- **Type-hint control** (same annotations, same draws, identical baselines, 13
  STONE and 17 KGW distinct baselines, 30 draws): signal kept after the step, via
  `ast.unparse` vs via text patch. STONE 59% vs 81%; KGW 41% vs 90%. The two
  variants produce the same program in every draw
  (`scripts/verify_patch_ops.py`: 75/75 per operation). So "type hints are the
  destructive step" is wrong; the annotations cost about 10% for KGW.
- **Whole chain, model-free factorial** (20 draws per baseline; baselines
  bootstrapped): KGW survives the chain in 4% of cases when every step
  reserializes and 65% [46-82] when the same edits are applied as text patches.
  STONE: 84% vs 92% never-broke, 97% vs 98% retained at end.
- **STONE tolerates reserialization better than KGW**: end z / baseline z
  68% [58-78] vs 19% [12-27]. Not a headroom artifact within KGW (r = -0.06 with
  baseline z), though a matched-baseline test is not possible (only two STONE
  baselines in KGW's z 4-10 range).
- **Five prompts** raised STONE from 9 to 13 distinct baselines (23 usable of 25;
  KGW 17 of 25, 17 distinct). STONE never broke in 14/23 and ended retained in
  23/23, so the earlier 16% vs 92% gap was mostly the 244-character degenerate mode.
- **CI order**: real workflows (20 Python repos) put `lint_autofix` before
  `format` 29 times to 15. My chain used the minority order. It made no difference
  (at most 0.1 z).
- **Robust to edit-content source**: rerun with a Flask-mined corpus instead of
  Lutris gives the same picture (KGW 3% vs 61% never-broke).
- **Recovery partly explained**: `format(unparse(x)) == format(x)` for 4/13 STONE
  and 0/17 KGW baselines. Suggestive, not established.

**Fixes made along the way:** `newline=""` on every code write site,
`core.autocrlf=false` and byte-exact reads (wheel and squash now return
byte-identical text); the RNG fix from 2026-09-24 is now in effect for all new
results; the lifecycle runner saves the baseline code so controls can be replayed
without the model.

**What I got wrong in the previous round that this exposed:** I labelled the
type-hint step as the first-break operation. It was only the first step that
reserializes, so it is where the loss appeared. Moving that step to a patch moves
the first break to the next reserializing step (KGW: `agent_add_docstring`,
10/17). The chain was largely measuring one reserialization.

**Still open:** a larger generation model (five schemes never embed); a Linux
run; a second generation host repository; the four unbenchmarked MarkLLM schemes
on the 22-operation battery; a matched-baseline STONE-vs-KGW test with more
low-headroom STONE samples.

---

## (partly superseded by the 2026-09-26 entry above) n=25 rerun of the lifecycle chain, and what it overturned — 2026-09-24

User asked for 20+ repeats on STONE and KGW "for statistical confidence." Ran
25 each (one scheme per process). **The n=5 pilot's headline claims did not
survive**, and chasing the discrepancy turned up two measurement defects. The
two entries below this one (2026-09-22) are kept for the record but are
**superseded** where they conflict with this one; the corrected write-up is
`BENCHMARK.md` §2.6-2.7.

**The numbers (as run).** STONE: 25/25 usable, but only **9 distinct
generations** — 17 of the 25 runs are the same byte-identical 244-character
completion (baseline z = 4.71, barely over the 4.0 threshold). KGW: 18/25
usable, all 18 distinct. STONE broke at step 1 (`agent_add_type_hints`) in
21/25 (84%), never broke in 4/25 (16%), and was above threshold after the squash
merge in 23/25 (92%). KGW broke at step 1 in 12/18, at `review_rename` in 3, at
`ci_format` in 1; never broke in 2/18 (11%); above threshold at the end in
2/18. The wheel step and the squash step flipped **zero** individual outcomes
across all 43 runs.

**What I had to retract, and why:**
1. *"100% of usable runs broke at type hints, zero exceptions."* False at
   n=25 (84% / 67%). The pilot's 100% came from 5 STONE runs that were
   effectively one trajectory (four were the identical 244-char text).
2. *"Cumulative survival is about 20% for both schemes; the STONE/KGW
   difference is an illusion."* STONE is 92% as-run; KGW is 11%.
3. *"STONE's end-of-chain recovery is a Windows CRLF artifact."* Wrong: STONE
   was already retained at the squash step in 23/25, and packaging flipped no
   outcome in 43 runs. The CRLF fact itself is real and was reproduced (54 → 59
   characters via `write_text` without `newline=""`); it stays as a
   platform-dependence flag, not an explanation.
4. *"Type hints strip 52-84% of the signal."* That was a four-run subset of the
   high-baseline runs, chosen by me after seeing the data. Full-sample: mean
   45%, range 34-86%.
5. *"Mutation sampling is deterministic, seeded by the input."* Only within a
   process — see below.

**Defect 1 — pseudo-replication.** 17 identical generations means STONE's
"n=25" is closer to n=9, so confidence intervals treating the runs as
independent are wrong for STONE; none are reported. (KGW's are valid for this
prompt and model.) The collapse itself is a property of the generator: under
this model, prompt and `delta=4.0`, STONE emits one completion about two-thirds
of the time.

**Defect 2 — `hash()` is randomized per process.** `_rng(src)` seeded the
real-corpus draws with `random.Random(hash(src))`. Python randomizes `hash()`
for strings on each interpreter launch (I confirmed two launches printing
different values), so the *same input* got a different comment, annotation set
and docstring in every process. That is why the n=5 process and the n=25
process disagreed about the same 244-character text. Fixed with a SHA-256
digest; existing results were not regenerated.

**Measuring the damage** (`scripts/lifecycle_draw_variance.py`, tokenizer only
so no model load): five saved STONE texts, 60 random draws each, the seven
text-only chain steps. The four longer texts (baseline z 9.98-21.5) were
retained at the end in 98-100% of draws. The dominant short text (z = 4.71):
only **10%** of draws never broke and **70%** ended retained. So for the
dominant mode the as-run outcome is one draw from a wide distribution, and
the "92% retained" figure is inflated: marginalizing over the draw and
weighting that mode at 17/25 gives roughly 23% never-broke and 72%
retained-at-end (approximate; the eight non-dominant runs are one draw each).

**The `ast.unparse` confound was unflagged for the type-hint step.**
`mut_add_type_hints` ends in `ast.unparse()`, the same reserialization issue I
had already flagged for the human-sourced operations. Control on the same five
texts: `ast.unparse` alone reproduces roughly 45-90% (mean about 71%) of the
signal the type-hint step loses (e.g. z 21.5 → 9.37 from unparse alone vs
8.06 with type hints). "Type hints are the most destructive single operation"
is unsupported. The clean test (type hints inserted by targeted text patching,
no reserialization) is not yet run.

**What held:** checking only the released artifact overstates survival by a
wide margin (16% never-broke vs 92% at the end as-run; about 23% vs 72%
marginalized) — the recovery mechanism after the early dip is *unexplained*
and I'm not going to guess at one; baseline headroom is the dominant
predictor (as-run STONE never-broke runs: mean baseline z 20.4 vs 5.9); KGW
retains poorly and doesn't recover; and 5 of 9 schemes never embed on this
model.

**Not isolated:** the STONE-vs-KGW lifecycle gap is confounded with baseline
headroom (KGW clusters near z = 6.5; STONE is bimodal 4.7 / 9-27), so it says
little about scheme design.

---

## (superseded by the entry above where they conflict) All 9 schemes through the lifecycle chain — 2026-09-22

Follow-up to the STONE/KGW lifecycle chain below: user asked directly "run the
other schemes through the lifecycle chain, and where is it breaking (the op
name)." Ran the remaining 7 (SWEET, EWD, Unigram, Unbiased, DIP, SynthID, PF)
through the identical 9-step chain, one scheme per process (memory recovered
enough this session — 2-3.3 GB free throughout — that none of these 7 runs
crashed, unlike the STONE/KGW attempts earlier).

**Direct answer**: 11 usable runs total, across 4 schemes (STONE 5, KGW 4,
EWD 1, DIP 1) — **every single one broke at the identical first step,
`agent_add_type_hints`.** Zero exceptions. SWEET, Unigram, Unbiased, and
SynthID never produced a single usable baseline across 20 combined attempts
(5 each) — a separate, real finding: on this 164M-parameter model, only the
simplest green-list constructions (STONE, KGW) and their close relatives
(EWD, DIP, when they work at all) can even be tested for mutation
robustness. The others fail before the question is askable.

Full table and both findings written up together: `BENCHMARK.md` §2.7.

---

## (superseded by the 2026-09-24 entry where they conflict) Full-SDLC-cycle chain: cumulative survival — 2026-09-22

User asked directly: "check for the entire SDE cycle." Everything before this
entry (30+ operations across 9 schemes) mutates the *original* baseline once,
independently, per operation. That's a huge grid, but it never answers the
brief's actual Phase 5 requirement: *"measure cumulative survival"* through a
realistic chain, not just individual operations in isolation.

Built `run_lifecycle.py`: one plausible real order — generate → agent adds
type hints → agent adds docstring → review: targeted patch → review: rename
→ review: add comment → CI format → CI lint autofix → squash merge → release:
build a real wheel — applied in sequence, with detection re-checked after
*every* step, so loss compounds the way it actually would.

Two crashes on the first attempts (host memory: 0.3-0.8 GB free — the same
constraint that's dogged this whole session). Every step's logic was verified
via a no-model dry run first, which also caught a real bug (the squash step's
internal reformat pass fails with "nothing to commit" when it follows an
already-formatted step — fixed by checking for an actual diff before
committing). Once memory recovered (~2 GB free), the run completed cleanly.

**STONE, 5/5 usable runs**: every run broke at step 1
(`agent_add_type_hints`) and 4/5 stayed broken through the squash merge —
then recovered at the very last step, `release_build_wheel`.

**That recovery turned out to be a real discovery, not luck.** Traced it:
`republish_build_wheel()` writes the file via `Path.write_text(code,
encoding="utf-8")` without `newline=""`, which on Windows silently converts
`\n` to `\r\n`. Confirmed by direct reproduction — a 54-character LF-only
sample became 59 characters after going through the same code path. This is
real Windows packaging behavior, not a simulation bug, but it means the
"recovery" is a platform-dependent side effect, not genuine robustness — and
it isn't even consistent: for KGW's run 2, the identical packaging step
pushed an already-retained score (4.61) back down to lost (3.72), the
opposite direction from STONE.

**KGW, 4/5 usable runs**: also broke at step 1 in every run, and only 1 of 4
ever recovered mid-chain — and that one lost it again at the final packaging
step. **0/4 KGW runs retained the watermark at the actual final artifact.**

**The number that matters**: measured at the score right before packaging
(the realistic estimate of what a Linux CI build — the real-world majority
case — would ship, since Linux text-mode writes don't perform this
conversion), cumulative full-chain survival is **STONE 1/5, KGW 1/4** — both
around 20%. STONE's raw 5/5 "success" at the literal Windows-built artifact
is almost entirely explained by the platform quirk, not by STONE being more
robust than KGW at the pipeline level.

Also: since `agent_add_type_hints` is the very first mutation applied to the
untouched baseline in every run, "score after step 1" doubles as that
operation's isolated single-operation retention rate — **0/5 STONE, 0/4
KGW**. The single most consistently destructive operation found anywhere in
this project; every other operation tested was scheme-dependent (broke one
scheme, not the other).

**The methodological point, stated plainly**: checking provenance only at the
final released artifact can look like success while the signal was destroyed
for nearly the entire pipeline. STONE's chain *looked* fine at the end. It
wasn't, for 4 of 5 runs, until the very last step happened to nudge it back
— on this specific host, for reasons unrelated to the watermark scheme's
actual robustness.

**Follow-up flagged, not yet fixed**: the same `write_text()`-without-
`newline=""` pattern appears at two other call sites in
`run_full_battery.py` — worth auditing before assuming platform-dependence
is controlled for anywhere else in this project.

Full writeup, tables, and the reproduction numbers: `BENCHMARK.md` §2.6.

---

## Nine schemes, 22 operations (independent, single-operation) — 2026-09-21

Expanded from 4 to 9 schemes and from 16 to 22 operations. Full writeup is in
`BENCHMARK.md` §1.1, §1.5, §2.4-2.5 — this section is the short version plus
the session narrative.

**5 more schemes**, vendored from `github.com/THU-BPM/MarkLLM` (the upstream
library the existing 4 schemes' repo forked its structure from — same API,
~25 schemes total): **Unigram** (static green list), **Unbiased** and **DIP**
(distortion-free constructions), **SynthID** (Google DeepMind's published
scheme, mean-detector variant), **PF** (Permute-and-Flip sampling). Ran
Unigram through the full battery (0/5 usable — see below); Unbiased/DIP/
SynthID/PF are confirmed working end-to-end but not yet run at scale, disclosed
as a scope boundary, not hidden.

**EXPGumbel investigated and excluded**: its lookup table needs ~19GB for this
tokenizer's vocabulary — confirmed via a direct `RuntimeError`, not a config
mistake. Kept vendored as documentation of the finding.

**A real cross-vendor bug found and fixed before it caused silently wrong
results**: both vendor trees (the original 4-scheme family and the new
5-scheme family) define identically-named top-level packages
(`watermark`/`utils`/`exceptions`/`visualize`). `run_full_battery.py`'s
existing unconditional import of `run_pilot.py` (for mutation helpers) was
unconditionally binding those names to the old family's versions via
`sys.modules` caching, before `schemes.py` ever got to choose — meaning a
markllm-family run could have silently used the wrong `base.py`/config-loading
logic. Fixed by making `run_pilot.py`'s vendor imports lazy and adding
`assert_single_family()` to `schemes.py`, which now raises immediately rather
than risk a silent wrong-import.

**6 new human-sourced operations** (`human_mutations.py`) directly answer a
concern raised earlier in this project — whether mutation results could be an
artifact of the mutator itself being AI. Every piece of text these operations
inject (identifiers, comments, exception type names) is copied verbatim from
`data/human_corpus.json`, mined from lutris/lutris's own real source (3,326
identifiers, 757 comments, 36 exception types, all written by the project's
actual human contributors) by `scripts/mine_human_corpus.py` — not generated
per-call. Three of the six inject no vocabulary at all (pure AST
rearrangement), so they carry no authorship question regardless.

**Two real findings from running them** (STONE n=5, KGW n=4 usable/5):
1. `human_rename` (real, often multi-subword identifiers) retained the
   watermark 2/5 for STONE, vs. the mechanical `_v1`-style `rename`'s 5/5 in
   the same pass — realistic renames may disturb STONE's hash chain more than
   short mechanical ones do. A nuance at this n, not a confirmed result, but
   mechanistically plausible and worth a larger run.
2. `human_extract_variable`, `human_guard_clause`, and
   `human_reorder_statements` track `ast_roundtrip`'s retention rate almost
   exactly for both schemes — because all four end in `ast.unparse()`. Their
   measured fragility may be substantially attributable to that shared
   re-serialization step, not to the human-refactor pattern itself. Disclosed
   as a real confound (`BENCHMARK.md` §2.5), not smoothed over.

**Unigram's failure adds a between-scheme data point to the sequence-length
finding**: at the identical ~244-character generation length and identical
`delta=4.0` where STONE and KGW's baselines reliably clear the 4.0 threshold,
Unigram's never did (best z ≈ −0.13). Same model, same length, same delta —
a static green list needs more scored tokens than a hash-chained one for
equivalent detection confidence, consistent with why the field moved toward
hash-chained schemes after Unigram (2023).

---

## Four-scheme comparison (STONE, KGW, SWEET, EWD) — 2026-09-21

Added a 4th scheme, **EWD**, from the same vendored repo family: like KGW it
biases every token (no syntax-awareness), but at detection time it *weights*
each token's contribution to the z-score by its entropy, rather than SWEET's
hard entropy gate. Also re-ran SWEET cleanly (the earlier SWEET numbers below
were reconstructed from a crashed run's log; this is a proper completed run).

**EWD's result is a genuine negative finding**: 0/8 runs produced a
detectable baseline watermark at all — worse than SWEET's already-poor 1/8.
Mechanistically: EWD's weight for each token is its entropy minus the
*sequence's own minimum* entropy. On `tiny_starcoder_py`'s low-entropy code
output, entropy barely varies across a sequence, so nearly every weight
collapses toward zero — soft-weighting made the small-model compatibility
problem *worse* than SWEET's fixed cutoff, not better. Both schemes remain
too data-starved to evaluate for mutation robustness; see `BENCHMARK.md` §2.3
for the full writeup.

Two other schemes originally selected for the wider study were evaluated for
inclusion here and ruled out on concrete grounds: **SrcMarker** has no
released pretrained checkpoint (needs training from scratch) and its official
tree-sitter support covers Java/C++/JavaScript only, not Python. **CodeIP**
uses a fundamentally different multi-bit message-encoding detection paradigm,
not the green-list z-score interface the other four schemes share — would
need a new adapter layer, not a config addition, so deferred rather than
rushed into this session.

Also fixed a structural issue the earlier 4-scheme attempt's crashes exposed:
`run_full_battery.py` now merges into an existing results file by default
(`--fresh` to overwrite), so each scheme can run as its own short-lived
process — this is what let SWEET and EWD complete cleanly on a host that was
still memory-constrained (0.7-1.2 GB free during this session).

---

## Multi-scheme comparison (STONE vs. KGW vs. SWEET) — 2026-09-21

Extends the single-scheme battery below to three schemes from the same vendored
repo family (`github.com/inistory/STONE-watermarking`, commit `bb5d809`, same
API, same base model), to test whether *how a scheme picks which tokens to bias*
changes which operations break it. Raw data: `results/multischeme_results.json`.

**Note on provenance**: this run's structured JSON was reconstructed from the
background task's stderr log (`btxeszss8.output`) after the live process
segfaulted partway through SWEET's 10th run — traced to host memory exhaustion
(0.26 GB free of 16 GB at time of crash), not a bug in the harness. STONE (10/10)
and KGW (10/10, logged) had already completed and printed their full per-run,
per-operation detail before the crash, so the reconstruction is a straight parse
of real output, not a re-simulation. The crash also motivated a real fix: results
are now written incrementally after every run (`run_full_battery.py`), not only
at the end, so a future crash won't lose completed data.

### Retention by operation, per scheme

| Operation | Layer | STONE (10 runs) | KGW (7 usable/10) | SWEET (1 usable/7)* |
|---|---|---|---|---|
| rename | source | **10/10** | **0/7** | 0/1 |
| minify | source | **9/10** | **0/7** | 0/1 |
| aggressive_minify | source | 0/10 | 0/7 | 0/1 |
| dead_code_insert | source | 10/10 | 2/7 | 0/1 |
| stacked_adversarial | source | 10/10 | 0/7 | 0/1 |
| ast_roundtrip | source | 1/10 | 3/7 | 0/1 |
| format | source | 4/10 | **7/7** | 1/1 |
| lint_autofix | source | 10/10 | 7/7 | 1/1 |
| squash_with_reformat | history | 4/10 | 7/7 | 1/1 |
| squash_plain, rebase_plain, cherry_pick_plain | history | 10/10 each | 7/7 each | 1/1 |
| fork_sync | history | 10/10 | 7/7 | 0/1 (tool_error, unrelated to scheme) |
| repackage_zip_with_source | packaging | 10/10 | 7/7 | 1/1 |
| republish_wheel | packaging | 10/10 | 6/7 | 0/1 |
| rebuild_bytecode_only | packaging | **0/10** | **0/7** | 0/1 |

*SWEET's denominator is 1, not 7 — see "SWEET's baseline problem" below. Its column
is not a reliable robustness estimate and is included for completeness only.

### The headline pattern: STONE and KGW have opposite weak spots

**STONE** (biases only non-syntax tokens) is rock-solid against **rename** (10/10)
and **minify** (9/10) — the two transforms that mostly touch identifiers and
whitespace, exactly the tokens STONE marks, but apparently not enough to matter
at this delta — while it's fragile against **ast_roundtrip** (1/10), a full
structural regeneration.

**KGW** (biases every token, no syntax-awareness) shows close to the *opposite*
profile: **rename breaks it 0/7, minify breaks it 0/7, aggressive_minify 0/7,
stacked_adversarial 0/7** — but it's rock-solid on **format** (7/7) and
**lint_autofix** (7/7), exactly where STONE is weakest (format 4/10).

This is mechanistically coherent, not coincidental: KGW's green-list bias sits on
syntax tokens too (keywords, operators, delimiters), so any transform that
changes identifier boundaries and re-derives the hash chain through those
positions (renaming, minification) disrupts a much larger fraction of KGW's
signal than STONE's, which never put weight there. Conversely, `ruff format`
mostly moves whitespace and reflows lines without touching identifiers or
keywords — the class of change STONE is more exposed to (its signal sits
entirely in the tokens format touches) and KGW is comparatively insulated
from (formatting doesn't reach the syntax tokens carrying most of KGW's signal
either, but KGW has more total signal to lose from — the net effect favors KGW
here). Both configs used identical `gamma=0.5, delta=4.0, hash_key=15485863,
z_threshold=4.0` — the only variable between them is *which* tokens get biased,
which isolates this as a selection-rule effect, not a tuning difference.

**For an FSE paper, this is the strongest candidate finding from the pilot**:
watermark robustness under ordinary operations is not a scalar property of a
scheme — it's a profile shaped by the scheme's own token-selection rule, and two
schemes can trade first place depending on which operation you ask about. A
robustness claim for one scheme doesn't transfer to another, even from the same
codebase and same underlying green-list mechanism.

### SWEET's baseline problem

SWEET only biases tokens where the model's own next-token distribution is
high-entropy (`entropy_threshold=0.9` nats). Across 7 attempted runs, **6 never
produced a detectable baseline watermark at all** (`is_watermarked: False` before
any mutation ran) — per `docs/01-outcome-definitions.md`, these are excluded as
"never emitted," not scored as mutation damage (this is exactly the gate added to
`run_once()` after this problem first surfaced). The 1 usable run's scores are
included above for completeness but should not be read as a robustness result —
n=1 is not an estimate.

**Why**: a 164M-parameter model writing short, syntactically constrained Python
produces overwhelmingly low-entropy (confident, predictable) next-token
distributions — there's rarely a token uncertain enough to clear a 0.9-nat
threshold, so SWEET's own trigger condition for biasing rarely fires. This is a
real, reportable finding independent of mutation robustness: **entropy-gated
watermarking has a model-size/model-confidence compatibility requirement that
syntax-gated (STONE) and ungated (KGW) schemes don't share.** A fair test of
SWEET would need a larger, less deterministic generation model — out of scope
for this pilot's CPU/time budget.

### Sequence-length correlation, now checked across two schemes

The single-scheme pilot below found baseline z-score correlates strongly with
generated-sequence length (r=0.91 at n=5). At n=10 for STONE alone, that
strengthens to **r=0.987**. KGW, independently, shows the same pattern at
**r=0.882 (n=7)**. Two different schemes, same underlying relationship — this is
no longer a 5-point coincidence. **Any reported robustness number for a
statistical code watermark needs its scored-sequence length reported alongside
it**, or it's not comparable across studies, schemes, or even repeated runs of
the same scheme.

### Honest limitations of the multi-scheme run
- KGW and SWEET's runs are smaller than STONE's effective sample after excluding
  never-emitted baselines (7 and 1 respectively vs. STONE's 10) — the comparison
  table above is suggestive, not a matched-N statistical test.
- The host machine ran low on memory during this session (confirmed via
  `psutil`, 0.26 GB free at time of the second crash) — both crashes are
  attributable to that, verified by reproducing an immediate crash on a bare,
  mutation-free generation call in isolation. This is an infrastructure
  constraint, not a result of anything in the mutation or detection logic, and
  it means SWEET in particular needs a clean re-run on a machine with headroom
  before its numbers can be trusted beyond "the scheme has an embedding problem
  on small models."
- All three schemes share `delta=4.0`, chosen above STONE's paper-typical range
  to compensate for the tiny model (see single-scheme section below) — this
  affects all three equally, so it doesn't bias the *comparison* between
  schemes, but it does mean none of these retention rates should be quoted as
  each scheme's real-world robustness at its own paper-recommended settings.

---

## Single-scheme pilot (STONE only, 5-16 operations, earlier runs)

Three runs are recorded in git history here. `run_pilot.py` (2026-09-21) was the
original 6-mutation smoke test. The first full-battery version covered 14
operations. **This version covers all 12 operation classes in
`scripts/mining/detectors.py`** except `transpile` and `bundle`, which are
genuinely not applicable to a pure-Python codebase (no standard tooling —
confirmed, not assumed, consistent with how the mining detectors already scope
those two to JS/TS ecosystems) — 16 operations total once history-layer variants
are counted, run **5 times** with fresh generations to report variance rather than
trust one run. Raw data: `results/full_battery_results.json`.

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

Full per-run scores (min/mean/max) are in `results/full_battery_results.json`'s `summary`
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
- **delta=4.0** is still above the paper's typical range, chosen to
  compensate for the tiny model's noisier logits —
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
