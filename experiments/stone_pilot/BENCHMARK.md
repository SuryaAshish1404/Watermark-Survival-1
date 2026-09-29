# Watermark Mutation-Survival Benchmark

A self-contained benchmark of code-watermark survival under ordinary developer
operations, run to inform the anticipatory arm of "Do the Marks Survive the
Pipeline?" (FSE 2027). Written to drop into the paper largely as-is — methods,
metrics, and a results table — not as an internal lab notebook. For the full
narrative, per-run detail, and honest hedging, see `RESULTS.md`; this file is the
condensed, citable version.

## 1. Method

### 1.1 Schemes under test

Nine green-list / distortion-free watermarking schemes, drawn from two related
open-source implementation families so that scheme identity is the only
varying factor and no reimplementation risk is introduced. Family 1:
`github.com/inistory/STONE-watermarking`, commit `bb5d809`. Family 2:
`github.com/THU-BPM/MarkLLM` — the upstream library Family 1 forked its
structure from, with ~25 schemes under the same API. Both Apache-2.0, vendored
unmodified except one disclosed 3-line fix (see `vendor/VENDORED.md`).

| Scheme | Family | Token selection / construction | Detection needs the model? |
|---|---|---|---|
| **STONE** (Kim, Park & Han, EACL 2026 Findings) | 1 | Syntax-aware: biases only non-syntax tokens | No |
| **KGW** (Kirchenbauer et al., ICML 2023) | 1 | None: biases every generated token | No |
| **SWEET** (Lee et al.) | 1 | Entropy-gated: biases only tokens above a fixed entropy cutoff | Yes |
| **EWD** | 1 | Entropy-weighted: biases every token, weights each by entropy at detection | Yes |
| **Unigram** (Zhao et al., 2023) | 2 | *Static* green list — same list at every position, not re-derived per token | No |
| **Unbiased** (Hu et al.) | 2 | Distortion-free: reweights the sampling distribution via a randomized strategy, doesn't skew the output distribution | No |
| **DIP** | 2 | Distortion-free, permutation-based, with its own history-context handling | No |
| **SynthID** (Google DeepMind, mean-detector variant) | 2 | Gumbel-sampling-based, as published; `MeanDetector` scoring, no trained Bayesian detector | No |
| **PF** (Permute-and-Flip) | 2 | Distortion-free, hash-table-seeded sampling, different construction again | No |

Three schemes were evaluated for inclusion and excluded on concrete grounds,
not convenience:
- **SrcMarker**: no released pretrained checkpoint (requires training a
  BiGRU encoder/decoder from scratch); official tree-sitter parser support
  covers Java, C++, and JavaScript only — no Python grammar, incompatible with
  this benchmark's host language.
- **CodeIP**: uses a fundamentally different detection paradigm (multi-bit
  message encoding with a two-tokenizer remapping and hash-chained message
  seeds, decoded via bit-accuracy) rather than the green-list z-score interface
  the other schemes share. Integrating it would mean writing a new adapter
  layer, not configuring an existing one — deferred rather than rushed.
- **EXPGumbel** (Family 2): its reference implementation allocates a
  `(vocab_size × prefix_length) × vocab_size` lookup table at initialization —
  for the generation model's ~49k-token vocabulary this is a confirmed ~19 GB
  allocation (a direct `RuntimeError` on this host, not a config mistake). A
  real scalability limit of this particular implementation for
  large-vocabulary code models, kept vendored as documentation of the finding
  (see `schemes.py`).

**Coverage vs. depth, disclosed explicitly**: STONE and KGW have full repeated-run
samples (10 each). SWEET, EWD, and Unigram were run to completion but mostly or
entirely failed to produce a usable sample (§2.3, §2.4) — a finding in itself,
not a gap. **Unbiased, DIP, SynthID, and PF are confirmed working end-to-end
through the real harness (smoke-tested, not simulated) but have not yet been
run through the full repeated battery** — this is a scope/time boundary of this
benchmark pass, not a claim about their robustness either way. The
infrastructure (`schemes.py`, `run_full_battery.py --schemes unbiased,dip,synthid,pf`)
is ready for that run.

### 1.2 Configuration

Family 1 schemes ran with `gamma=0.5, delta=4.0, hash_key=15485863,
prefix_length=1, z_threshold=4.0` (SWEET additionally: `entropy_threshold=0.9`).
`delta=4.0` is above STONE's paper-typical range (0.5–2.0); raised to keep the
generation model's watermark reliably detectable given its size (see §1.3). The
same value was used for every Family 1 scheme, so it does not bias the
*comparison* between them, but no rate in §2 should be read as that scheme's
robustness at its own paper-recommended defaults. Family 2 schemes ran with
their own published default configuration (vendored `config/*.json`), since
their detection statistics (p-values, scheme-specific thresholds) aren't on
the same z-score scale as Family 1's and forcing one shared `delta` onto them
wouldn't be meaningful — Unigram is the one exception, given a `delta=4.0`
override since it shares Family 1's z-score mechanism closely enough for the
comparison to mean something.

### 1.3 Generation

Model: `bigcode/tiny_starcoder_py` (164M parameters, CPU inference). Prompt: a
docstring + signature for a Lutris-style utility function
(`get_game_executable_path`). `do_sample=True, top_k=50, temperature=0.7,
max_new_tokens=160`. Generations are trimmed to their largest syntactically
valid prefix before any mutation, so length variance across runs reflects real
model output, not a truncation artifact.

### 1.4 Host repository

`lutris/lutris`, chosen because it was already hand-verified against this
study's measured-arm sampling criteria (`data/sampling/candidates.md`: 193 real
agent-trailer commits, 88 tagged releases) — reusing a vetted repo rather than
introducing an unverified one, and giving the anticipatory-arm result a
realistic host with real linting/formatting configuration
(`ruff.toml`; confirmed via CI that the project uses `ruff format`, not
`black`, before writing the mutation battery).

### 1.5 Operation battery

22 operations across three layers, chosen to cover every class in this study's
mined operation catalogue (`scripts/mining/detectors.py`) that is mechanically
applicable to a single Python file — `transpile` and `bundle` are confirmed
not applicable to a pure-Python codebase (no standard tooling) and excluded on
that basis, not omitted by oversight.

- **History** (real git operations against a temp repo, not simulated diffs):
  squash (plain, and with a reformat pass in the squashed commit), rebase,
  cherry-pick, fork-sync.
- **Source, tool-based**: `ruff format`, `ruff check --fix`, AST-based variable
  renaming (`_v1`/`_v2` style), dead-code insertion, `python-minifier` (mild
  and aggressive settings), AST round-trip (`ast.parse` → `ast.unparse`), and
  a stacked combination of four of the above.
- **Source, human-sourced** (`human_mutations.py`): six operations chosen to
  emulate real reviewer/refactorer edits rather than tool passes — variable
  renaming, a prepended comment, error-handling wrapping, return-expression
  extraction, guard-clause conversion, and independent-statement reordering.
  What distinguishes these from an LLM inventing plausible edits: every piece
  of *injected text* (identifier names, the comment, the exception type name)
  is copied verbatim from `data/human_corpus.json`, mined by
  `scripts/mine_human_corpus.py` from lutris/lutris's own real source (3,326
  real identifiers, 757 real comments, 36 real exception type names, all
  written by the project's actual contributors) — which real token is
  sampled is seeded by the input text and never generated. **Caveat, discovered
  2026-09-24:** the seed originally came from Python's builtin `hash()`, which
  is randomized per interpreter launch, so a given input got the same draw
  *within* one process but a different draw in each new process — every
  result generated before that date is not bit-reproducible across runs. Fixed
  (stable SHA-256 digest); the effect on results is quantified in §2.6. The other three
  (extract-variable, guard-clause, reorder) inject no vocabulary at all —
  purely structural AST rearrangements of tokens already present in the input
  — so they carry no content-authorship question in the first place.
- **Packaging**: bytecode-only compilation (`py_compile`, no source shipped),
  source-preserving zip repackage, and a real wheel build via the PyPA `build`
  frontend (`republish`).

### 1.6 Metric: retention rate under repeated generation

For each (scheme, operation) pair: `detect_watermark()` is run on the mutated
text and classified retained / silently-lost / destroyed-structurally, per this
study's outcome taxonomy (`docs/01-outcome-definitions.md`). This is repeated
across independent generations (STONE: 10 on the 16-operation battery, 5 on the
22-operation battery with human-sourced operations added; KGW: 10 and 5
respectively; SWEET: 8; EWD: 8; Unigram: 5) because detection is a statistical
test, not a deterministic property — a single run's result is not reported as
a rate. A run whose *baseline* (pre-mutation) text does not itself clear the
detection threshold is excluded from that scheme's denominator and logged
separately (§3.2), per the taxonomy's "never emitted"
category — scoring it as mutation damage would misattribute a generation-time
failure to the mutation step.

## 2. Results

### 2.1 Retention by operation — STONE vs. KGW

The only two schemes with a usable sample (§3.2 explains why SWEET and EWD are
reported separately rather than in this table).

| Operation | Layer | STONE (n=10) | KGW (n=7 usable/10) |
|---|---|---|---|
| rename | source | 10/10 | 0/7 |
| minify | source | 9/10 | 0/7 |
| aggressive_minify | source | 0/10 | 0/7 |
| dead_code_insert | source | 10/10 | 2/7 |
| stacked_adversarial | source | 10/10 | 0/7 |
| ast_roundtrip | source | 1/10 | 3/7 |
| format | source | 4/10 | 7/7 |
| lint_autofix | source | 10/10 | 7/7 |
| squash_with_reformat | history | 4/10 | 7/7 |
| squash_plain / rebase_plain / cherry_pick_plain / fork_sync | history | 10/10 each | 7/7 each |
| repackage_zip_with_source | packaging | 10/10 | 7/7 |
| republish_wheel | packaging | 10/10 | 6/7 |
| rebuild_bytecode_only | packaging | 0/10 | 0/7 |

**Finding 1 — opposite weak spots under identical configuration.** STONE is
robust to identifier-level transforms (rename, dead-code insertion,
stacked_adversarial: 10/10) and fragile to whitespace/structural regeneration
(ast_roundtrip: 1/10, format: 4/10). KGW shows close to the inverse: fragile to
identifier-level transforms (rename, minify, aggressive_minify,
stacked_adversarial: 0/7) and robust to formatting (format, lint_autofix: 7/7).
Since both schemes share every configuration parameter, the only variable is
*which tokens each scheme biases* — STONE skips syntax tokens, KGW does not —
which isolates this as a selection-rule effect rather than a tuning artifact.

**Finding 2 — packaging has one categorical failure mode.** Both schemes are
fully robust to source-preserving packaging (zip, wheel: 10/10 and 6–7/7) and
fully destroyed by bytecode-only compilation (0/10, 0/7) — not a threshold
failure but a structural one: no source text survives for the detector to
query. This failure mode needs its own column in any survival table, not a
merge into "did not survive."

**Finding 3 — git-history operations are a non-event for this carrier class.**
Squash, rebase, cherry-pick, and fork-sync never affected either scheme (10/10,
7/7 in every case) when applied without an accompanying content edit, because
none of them touch the file text a code-embedded watermark's signal lives in.
This is the sharpest possible contrast with this study's measured arm
(commit trailers, signatures), where these same operations are the dominant
destruction mechanism — the carrier type determines which pipeline layer is
the threat, a cross-arm claim this benchmark can now make with evidence rather
than assertion.

### 2.2 Sequence-length correlation

Baseline (pre-mutation) detection strength correlates with how much code was
generated:

| Scheme | n | Pearson r (chars vs. baseline z-score) |
|---|---|---|
| STONE | 10 | **0.987** |
| KGW | 7 | **0.882** |

**Finding 4.** Two independent schemes, same relationship, effectively
indistinguishable from a perfect linear relationship for STONE. **Any reported
survival rate for a statistical code watermark is incomplete without stating
the scored-sequence length it was measured on** — comparing two rates measured
at different generation lengths is comparing different points on this curve,
not different robustness.

### 2.3 Entropy-based selection: two failure modes, not one

SWEET and EWD both failed to produce a usable sample, but for a shared root
cause with different severity:

| Scheme | Usable runs | Selection mechanism | Baseline z-scores observed |
|---|---|---|---|
| SWEET | 1/8 | Hard gate: bias only tokens above a fixed entropy threshold | −2.06 to 5.33 |
| EWD | 0/8 | Soft weight: bias every token, weight each by entropy relative to the sequence's minimum | −2.03 to 3.67 |

**Finding 5.** `bigcode/tiny_starcoder_py` produces low-entropy (confident,
repetitive) next-token distributions when writing short, syntactically
constrained Python — there are rarely enough high-entropy positions for SWEET's
gate to admit, and EWD's weighting (which subtracts each sequence's own minimum
entropy) collapses even further toward zero when entropy varies little across
a sequence, as it does here. **The soft-weighted variant was not a mitigation
for the hard-gated variant's problem — it was worse (0/8 vs. 1/8 usable)**,
which argues against "make the entropy condition continuous instead of binary"
as a general fix for small-model compatibility. This is a model-compatibility
finding, independent of mutation robustness, and neither scheme's robustness
can be fairly assessed until it is resolved (larger/less-deterministic
generation model).

### 2.4 A static green list needs more tokens than a hash-chained one

Unigram (Family 2, static green list — the same list at every position rather
than re-derived from the previous token) was run at `delta=4.0` z_threshold=4.0`,
identical to STONE/KGW's Family 1 configuration, for a direct comparison. Result:
**0/5 usable runs** — every one of the 5 generations landed in the same
~244-character completion mode this prompt/model combination produces, and at
that exact length, Unigram's baseline never cleared 4.0 (best: z ≈ −0.13),
while **STONE and KGW's baseline reliably clears 4.0 at this identical length**
(STONE: z ≈ 4.71 at 244 chars, repeatedly — see §2.2's data). Same delta, same
length, same model — the static list needs more scored tokens to reach the
same confidence a hash-chained list reaches. This is consistent with why the
watermarking literature moved from static (Unigram, 2023) toward hash-chained
schemes (KGW and after): a static list's "expected fraction green" signal
doesn't accumulate distinguishing power from position to position the way a
hash-chained list's re-randomization does.

**Not yet benchmarked at scale**: Unbiased, DIP, SynthID, PF (§1.1) — confirmed
working, no results to report yet.

### 2.5 Human-sourced operations: a real nuance, and a real confound

Ran the 6 human-sourced operations (§1.5) against STONE (n=5) and KGW (n=4
usable/5) alongside the existing tool-based operations, for direct comparison:

| Operation | STONE | KGW | Comparable tool-based operation |
|---|---|---|---|
| human_add_comment | 5/5 | 4/4 | — (prepended outside the function; expected to be a non-event, confirmed) |
| human_rename | 2/5 | 1/4 | rename (mechanical, `_v1`-style): STONE 5/5 (n=10 battery) or 5/5 (n=5 battery), KGW 1/4 |
| human_add_error_handling | 1/5 | 0/4 | no tool-based equivalent |
| human_extract_variable | 1/5 | 2/4 | ast_roundtrip: STONE 1/5, KGW 2/4 |
| human_guard_clause | 1/5 | 2/4 | ast_roundtrip: STONE 1/5, KGW 2/4 |
| human_reorder_statements | 1/5 | 2/4 | ast_roundtrip: STONE 1/5, KGW 2/4 |

**Finding 6 — realistic identifier names may be more disruptive than
mechanical ones, for STONE specifically.** `human_rename` (real, often
multi-subword identifiers sampled from Lutris's own source) retained the
watermark 2/5 for STONE, versus the mechanical `rename` mutation's 5/5 in the
same battery pass. KGW shows the opposite direction but from an already-low
base (1/4 vs. 1/4 — no discernible difference). At this sample size (n=5) this
is a nuance to flag and re-test at scale, not a confirmed general result —
but it is mechanistically plausible: `_v1`/`_v2`-style names tokenize to a
small, uniform set of subword tokens, while real identifiers vary widely in
subword-tokenization length and content, perturbing more of the hash chain
STONE's green-list derivation depends on.

**Finding 7 — a confound, disclosed rather than hidden.** `human_extract_variable`,
`human_guard_clause`, and `human_reorder_statements` track `ast_roundtrip`'s
retention rate almost exactly, for both schemes. This is very likely because
all four share an implementation detail: each ends with `ast.unparse()`,
which fully re-serializes the function regardless of what structural change
was made. **The fragility measured for these three "human-style" operations
may be substantially attributable to the AST re-serialization step, not to
the human-style refactor itself.** A methodologically cleaner version would
preserve original formatting outside the changed region (e.g., targeted
source-text patching instead of full-tree unparse) — noted here as a concrete
improvement for the full Phase 4 run rather than corrected retroactively in
this pilot, since disclosing a real confound is more useful than a rewrite
that would cost the ability to say what was actually measured.

### 2.6 Cumulative full-lifecycle survival — the brief's actual Phase 5 ask

> **Findings 8, 10 and 11 below are further superseded by §2.8 (2026-09-26),** which
> ran the reserialization control this section lists as "not yet run". Read §2.8
> first; this section is kept as the history of how the conclusions moved.
>
> **Revised 2026-09-24.** This section originally reported an n=5 pilot. A
> 25-run rerun and two follow-up controls overturned several of its claims;
> the corrections are listed at the end of the section rather than silently
> replaced. The numbers below are the n=25 numbers.

Every result above measures one operation applied to the *original* baseline,
independently. That answers "does operation X break it alone," not the brief's
Phase 5 requirement: *"Test realistic chains such as: AI-generated code →
commit → PR → squash → formatting → build → package → release. Measure
cumulative survival rather than only individual operations."*
`run_lifecycle.py` applies one chain in sequence and re-checks detection after
*every* step:

```
generate → agent adds type hints → agent adds docstring → review: targeted
patch → review: rename → review: add comment → CI format → CI lint autofix
→ squash merge (with review-branch reformat) → release: build a real wheel
```

(The order is a plausible real-world sequence, not mined from observed CI
configs the way `scripts/mining/workflow_order.py` derives orders for the
measured arm — weaker evidence than that arm's methodology, disclosed rather
than presented as equal.)

**Sample structure — read this before the tables.** STONE: 25 runs, all with a
usable baseline, but **only 9 distinct generations**: 17 of the 25 are the
same byte-identical 244-character completion (baseline z = 4.71, barely above
the 4.0 threshold), because under this model, prompt and `delta=4.0` STONE's
sampling collapses onto one output about two-thirds of the time. Confidence
intervals that assume 25 independent samples are therefore **not valid for
STONE** and none are reported for it. KGW: 25 attempted, 18 usable (7 excluded,
baseline never emitted), **18 distinct generations**, so KGW's n is real.

**Table 2.6a — as-run, n=25 attempted per scheme**

| | STONE | KGW |
|---|---|---|
| Usable baselines | 25/25 (9 distinct) | 18/25 (18 distinct) |
| Broke at step 1, `agent_add_type_hints` | 21/25 (84%) | 12/18 (67%) |
| Broke first at another step | 0 | `review_rename` 3, `ci_format` 1 |
| Never dropped below threshold at any step | 4/25 (16%) | 2/18 (11%) [95% CI 3–33%] |
| Retained after the squash merge (pre-packaging) | 23/25 (92%) | 2/18 (11%) |
| Retained at the final wheel | 23/25 (92%) | 2/18 (11%) |
| Runs whose retained/lost outcome flipped at packaging | 0/25 | 0/18 |

Per-step retention (fraction of usable runs above threshold after each step):

| Step | STONE | KGW |
|---|---|---|
| type hints / docstring / patch | 16% / 16% / 16% | 33% / 33% / 33% |
| rename | 16% | 17% |
| add comment | 88% | 17% |
| ci format / lint / squash / wheel | 88% / 92% / 92% / 92% | 11% / 11% / 11% / 11% |

**Finding 8 — the first chain step costs about half the signal, but that
cannot be attributed to type hints.** After step 1 the z-score has lost a mean
of 45% (range 34–86%) for STONE and 49% (24–95%) for KGW. `agent_add_type_hints`
is implemented with `ast.unparse()`, the same full-tree reserialization
confound flagged for the human-sourced operations in Finding 7 — and this was
not flagged when the step was first added. A control on five saved STONE
generations (`scripts/lifecycle_draw_variance.py`) separates the two:

| Text | Baseline z | After `ast.unparse` alone | After type hints (mean of 60 draws; range) | Share of loss from unparse alone |
|---|---|---|---|---|
| 0 (392 ch) | 12.12 | 7.57 | 5.75 (2.74–8.57) | 71% |
| 1 (672 ch) | 21.50 | 9.37 | 8.06 (5.80–10.41) | 90% |
| 2 (788 ch) | 21.17 | 16.87 | 15.45 (12.70–17.88) | 75% |
| 3 (547 ch) | 9.98 | 7.90 | 7.15 (4.19–9.00) | 73% |
| 4 (244 ch) | 4.71 | 3.74 | 2.57 (0.39–6.00) | 45% |

Reserialization alone accounts for roughly 45–90% (mean about 71%) of the loss.
The annotations add a smaller increment on top. "Adding type hints is the most
destructive single operation" is **not supported**; the supported claim is that
*any* step ending in a full `ast.unparse()` costs a large share of the signal.
The decisive follow-up — type hints inserted by targeted text patching, with no
reserialization — was run on 2026-09-26; see §2.8 (it confirms the reserialization
attribution).

**Finding 9 — survival is decided mainly by baseline headroom, and for
borderline texts by an uncontrolled random draw.** The five saved texts
above, run through the seven text-only chain steps under 60 different random
draws of the real-corpus tokens each (neither the squash step nor the wheel
step flipped an individual outcome in any of the 43 lifecycle runs, so they
are omitted):

| Text | Baseline z | Never broke, over 60 draws | Retained at end, over 60 draws |
|---|---|---|---|
| 0 | 12.12 | 85% | 100% |
| 1 | 21.50 | 92% | 98% |
| 2 | 21.17 | 100% | 100% |
| 3 | 9.98 | 98% | 98% |
| 4 (the dominant 244-char mode) | 4.71 | **10%** | **70%** |

Longer generations survive the whole chain almost regardless of the draw. The
dominant short generation does not: only 10% of draws never break and 70% end
retained, with retention climbing draw by draw across the steps (10% after
step 1, 20% after rename, 35% after the comment, 40% after format, 70% after
lint). This explains why the n=5 pilot and the n=25 run disagreed about the
*same* text: the mutation RNG used Python's per-process-randomized `hash()`
(see §1.5), so each process drew a different comment, annotation set and
docstring for identical input — the pilot's process drew an unlucky one, the
n=25 process a lucky one. In the as-run n=25 data, the 4 STONE runs that never
broke had a mean baseline z of 20.4 against 5.9 for the rest.

**Finding 10 — checking only at the end still overstates survival, by a wide
margin.** As run, STONE was above threshold at *every* step in 16% of runs but
above threshold at the final artifact in 92%. Marginalizing over the draw and
weighting the 244-character mode at its observed 17/25, the estimate is about
23% never-broke against about 72% retained-at-end (approximate: the eight
non-dominant runs each contribute a single draw). Either way, the gap between
"checked at every step" and "checked at release" is roughly 50–75 points, and
scores are not monotone — they mostly recover after dipping. **The recovery
mechanism is not explained**; it is reported as an open observation. KGW shows
no recovery (11% at every step, 11% at the end).

**Finding 11 — the Windows line-ending conversion is real but explains
nothing here.** `republish_build_wheel()` writes the file with
`Path.write_text(code, encoding="utf-8")`, no `newline=""`, so on Windows `\n`
becomes `\r\n`; reproduced directly (a 54-character LF sample became 59
characters through the same path). It shifts individual scores, but **it
flipped the retained/lost outcome in 0 of 43 runs**, and STONE was already
retained at the squash step in 23 of 25. The n=5 pilot's claim that this
conversion "explains" STONE's end-of-chain retention is retracted. It stays
recorded as a platform-dependence flag: the same pattern appears at two other
call sites (`_init_git_scenario`, the pyproject write) and should be audited.

**STONE vs. KGW at the lifecycle level.** The as-run difference is large
(pre-packaging 92% vs 11%; about 72% vs 11% draw-marginalized) but **confounded
with baseline headroom**: KGW's usable baselines cluster around z ≈ 6.5
(median 6.49, none in the 4.71 mode), while STONE's are bimodal (4.71, or 9–27).
A first step that costs about half the signal leaves KGW near 3.4 on average
(below threshold) and STONE's longer texts well above it. The lifecycle result
therefore does not isolate scheme design; a comparison at matched baseline z
would.

**What changed from the n=5 pilot (kept for the record):**
1. "`agent_add_type_hints` broke 100% of usable runs, zero exceptions" →
   84% (STONE) and 67% (KGW); and the attribution to type hints is confounded
   with `ast.unparse` (Finding 8).
2. "Cumulative survival is ~20% for both schemes" → STONE 92% as-run / about
   72% marginalized, KGW 11%; the pilot drew mostly the 244-character mode
   and one unlucky random draw.
3. "STONE's 5/5 final-artifact retention is almost entirely a Windows CRLF
   artifact" → retracted (Finding 11).
4. "Type hints strip 52–84% of the signal" → that was a four-run subset; the
   full-sample mean is 45% (34–86%).
5. "Mutation sampling is deterministic" → true within a process only, until fixed.
6. "The STONE/KGW difference is an illusion of where you check" → there is a real
   difference at n=25, though confounded with headroom.

**What held:** checking only the released artifact overstates survival
substantially (Finding 10); watermark strength/headroom is the dominant
predictor of survival, consistent with §2.2; KGW retains poorly through the
chain; and 5 of 9 schemes never embed on this model (§2.7).

### 2.7 All 9 schemes through the lifecycle chain: where does each one break

The remaining 7 schemes ran through the identical chain (5 attempts each, one
scheme per process). STONE and KGW use the n=25 data above.

| Scheme | Usable / attempted | First-break operation(s) | Never broke |
|---|---|---|---|
| STONE | 25/25 (9 distinct) | `agent_add_type_hints` 21 | 4/25 |
| KGW | 18/25 | `agent_add_type_hints` 12, `review_rename` 3, `ci_format` 1 | 2/18 |
| EWD | 1/5 | `agent_add_type_hints` | 0/1 |
| DIP | 1/5 | `agent_add_type_hints` | 0/1 |
| SWEET, Unigram, Unbiased, SynthID, PF | 0/5 each | no usable baseline | — |

**Finding 12 — a model-compatibility wall, and a weaker "first break"
pattern than first reported.** (a) Of nine schemes, only four ever produced a
detectable baseline on `bigcode/tiny_starcoder_py`, and EWD and DIP managed it
once in five tries; SWEET, Unigram, Unbiased, SynthID and PF never did across
25 combined attempts. This spans entropy-gated, static-list, distortion-free and
production (SynthID) constructions, so it is a property of the small
low-entropy model rather than of any one mechanism; robustness of most of the
scheme set cannot be assessed until a larger model is used. (b) Where a scheme
could be tested, the first break is usually at step 1 — but with one usable run
each, EWD and DIP cannot support any rate, and the STONE/KGW figures above
show the step-1 pattern is common (67–84%), not universal, and confounded with
`ast.unparse` (Finding 8). The earlier "100%, zero exceptions across 11 runs"
statement is withdrawn.

### 2.8 Round 2 (2026-09-26): the controls that decide Findings 8-11

§2.6 ended with three open items: the type-hint step was confounded with
`ast.unparse()`, STONE's samples were pseudo-replicated, and the chain order was
hand-designed. This section closes them as far as this host allows. **It
supersedes Findings 8, 10 and 11 of §2.6 where they conflict.** The one-line
summary: **whole-file reserialization is what destroys the signal; the content edits
(type hints, docstrings, renames, comments, formatting) cost far less, and STONE and
KGW differ mainly in how they tolerate reserialization.**

**New machinery.**
- *Reserialization-free operations* (`more_operations.py`): type hints, docstring,
  flip-one-comparison and rename re-implemented as text edits at AST-reported
  positions (header colons found with `tokenize`). Each takes the same random draw
  as its `ast.unparse` sibling and is checked by `scripts/verify_patch_ops.py`:
  `ast.dump` of the two outputs is identical in 75/75 cases per operation.
- *Five distinct prompts* (`run_lifecycle.py --multi-prompt`) instead of one. STONE:
  23/25 usable, **13 distinct baselines** (was 9 distinct from 25); KGW: 17/25
  usable, 17 distinct. Pseudo-replication is reduced, not removed, and baselines,
  never runs, are the unit of analysis below.
- *Matched design* (`--hints both`): both first-step variants run from the same
  generated baseline.
- *Model-free factorial* (`scripts/offline_matrix.py`): saved baselines replayed
  through the chain, 20 random draws each, detection needs only the tokenizer.
  Draws are averaged within a baseline first and baselines are then bootstrapped.
- *Mined CI order* (`scripts/mining/workflow_order.py` over 20 real Python
  repositories' workflows, 281 job step sequences): `lint_autofix` precedes `format`
  29 times, the reverse 15 times. The hand-designed chain used the minority order.
  Both orders are run.
- *Platform fix:* `newline=""` on every code write site, `core.autocrlf=false` in the
  scratch git repos, and byte-exact reads. Verified: wheel and squash steps now
  return byte-identical text.

**Finding 8 (replaces §2.6 Finding 8) — type hints themselves cost little;
`ast.unparse` costs most of the first-step loss.** Same annotations, same draws, on
identical baselines, tokenizer-only detection, 30 draws per baseline
(`scripts/unparse_control.py`). Signal kept = z after step / baseline z (share of
baselines still detected in brackets):

| | ast_roundtrip only | type hints via `ast.unparse` | type hints via text patch |
|---|---|---|---|
| STONE, 13 baselines | 77% (12/13) | 59% (86%) | **81%** (93%) |
| KGW, 17 baselines | 50% (7/17) | 41% (40%) | **90%** (95%) |

In every draw the two type-hint variants produce the same program. For KGW the
annotation itself costs about 10% of the signal; reserialization costs about half.
The n=25 result that "step 1 costs about half the signal" is true, but the cause is
the reserialization the step was implemented with. In the live multi-prompt run the
first break moves accordingly: swapping only step 1 for the patch version changes
KGW's mean step-1 loss from 60% to 11% and moves its first break from
`agent_add_type_hints` (10/17) to `agent_add_docstring` (10/17), the next step that
reserializes.

**Finding 13 — the reserialization effect carries through the whole chain.**
Offline factorial, 13 STONE and 17 KGW distinct baselines, 20 draws each
(`offline_matrix_stone.json`, `offline_matrix_kgw.json`). Intervals are 95%
bootstrap over baselines.

| | Chain | Never below threshold | Above threshold at end | End z / baseline z |
|---|---|---|---|---|
| STONE | all steps reserialize | 84% [67-97] | 97% [94-100] | 68% [58-78] |
| STONE | same edits as text patches | 92% [78-99] | 98% [95-100] | 82% [74-91] |
| STONE | one `ast.unparse`, nothing else | 85% [62-100] | 92% [77-100] | 83% [71-95] |
| KGW | all steps reserialize | **4%** [1-8] | **4%** [1-9] | 19% [12-27] |
| KGW | same edits as text patches | **65%** [46-82] | **65%** [46-82] | 67% [57-77] |
| KGW | one `ast.unparse`, nothing else | 35% [12-59] | 41% [18-65] | 46% [30-62] |

Two consequences. (a) For KGW the difference between "an agent that edits text" and
"a tool that reserializes" is 65% vs 4% survival, with intervals that do not
overlap. (b) The reserialization-free chain still costs KGW a third of its signal,
so the content edits are not free; the rename step and the CI formatter account for
most of that (per-step means in the JSON). CI step order made no difference (the two
orders differ by at most 0.1 z), so the hand-designed order was not distorting the
result.

**Finding 14 — STONE tolerates reserialization better than KGW, and this is not
just headroom.** Baseline headroom differs (STONE mean baseline z 15.6, KGW 7.8),
so absolute survival is confounded. The normalised measure, share of baseline z
retained at the end of the fully reserializing chain, is 68% [58-78] for STONE
against 19% [12-27] for KGW, non-overlapping. Within KGW that share is uncorrelated
with baseline z (r = -0.06), so KGW's low retention is not a low-headroom artifact;
for STONE it is negatively correlated (r = -0.70) because a longer text has more
headroom above the floor. A tighter matched-baseline test is not possible with
these data: only two STONE baselines fall in the z 4-10 range that most KGW
baselines occupy (both retained). The direction is consistent with STONE's design
(it skips syntax tokens, which reserialization rewrites), but that is a hypothesis
this experiment does not test.

**Finding 10 (revised) — the "end vs every step" gap shrinks once baselines are
diverse.** With five prompts, STONE never broke in 14/23 runs and was retained at
the end in 23/23, so the earlier 16% vs 92% gap was largely the 244-character
degenerate mode. The direction survives, its size does not.

**Recovery, partly explained.** Scores rise after `ci_format` in several chains
(for example STONE 3.68 to 4.64 in one run). A candidate mechanism: `ruff format`
rewrites reserialized text back toward the style the model emitted. Test
(`scripts/format_recovery_check.py`): `format(unparse(x))` is byte-identical to
`format(x)` for 4/13 STONE and 0/17 KGW baselines. Consistent with STONE recovering
more than KGW, but it does not establish the mechanism; reported as a partial
explanation only.

**Finding 11 (revised).** Even with the platform fix, no retained/lost outcome
flipped at the squash or wheel step; those steps remain no-ops for these schemes.

**Robustness to the edit-content source.** The whole factorial was repeated with
edit content (comments, identifiers, annotations, docstring openers) mined from
Flask instead of Lutris (`data/human_corpus_flask.json`, `WM_CORPUS`). KGW: 3% vs
61% never-broke (reserializing vs patch chain), 3% vs 63% at end; STONE: 80% vs 90%
never-broke, 93% vs 96% at end. The conclusions do not depend on Lutris's vocabulary.

**Not done, and why.** (a) A larger generation model: not available on this host at
the time; a preliminary baseline-embedding check on a larger model has since been
run — see §2.9 — but the mutation battery and lifecycle chain have not yet been
repeated on it. (b) A Linux host: none available; the newline fix removes the known
platform dependence but a native rerun is still worth doing. (c) A second
*generation* host repository: prompts vary in task but not in codebase; only the
edit corpus was swapped. (d) A chain order mined end-to-end from CI: the mined data
fix only the lint/format order, because most CI steps in real workflows (build,
test, publish) do not modify source.

### 2.9 A larger model changes which schemes can even be tested (preliminary, 2026-09-29)

Everything above uses `bigcode/tiny_starcoder_py` (164M parameters, CPU). A GPU
became available (6 GB VRAM) partway through this study, which changes the binding
constraint identified in Finding 12 and threat 4/12 below. As a first check, not
yet a full rerun, the baseline-embedding step (generate, then detect on the
unmutated output — no mutations applied) was repeated on `deepseek-ai/deepseek-coder-1.3b-instruct`
(1.3B parameters, fp16, ~2.7 GB VRAM used), 15 attempts per scheme across 5
prompts, same `delta=4.0`/threshold config as elsewhere in this document. This
surfaced and fixed one real bug: `Unigram`'s green-list mask was sized off
`len(tokenizer)` (32,022), but this model's output embedding is padded to 32,256
for tensor-core efficiency; the mismatch produced an out-of-bounds CUDA write that
corrupted the process's CUDA context, causing an unrelated-looking failure in
whatever scheme ran next in the same process. Fixed by sizing the mask off the
model's actual output width (`model.config.vocab_size`) instead of the tokenizer's
logical vocabulary (`schemes.py`, `build_transformers_config`).

| Scheme | Detected / 15, new model | Detected / attempted, `tiny_starcoder_py` |
|---|---|---|
| STONE | 14/15 | 25/25 |
| KGW | 4/15 | 18/25 |
| SWEET | 0/15 (2/10 on a same-prompt repeat) | 0/25 |
| EWD | 4/15 (4/10 on a same-prompt repeat) | 1/5 |
| Unigram | 0/15 | 0/25 |
| Unbiased | 3/15 | 0/25 |
| DIP | 0/15 | 1/5 |
| SynthID | 1/15 | 0/25 |
| PF | 3/15 | 0/25 |

Three schemes that never once produced a detectable baseline across 25 combined
attempts on the small model — Unbiased, SynthID, PF — now do, at low but nonzero
rates. SWEET and EWD, which were effectively untestable before (0/25 and 1/5),
now show a real, repeatable-but-uncommon detection rate (confirmed by an
independent same-prompt repeat, not a single lucky draw). Unigram alone remains at
0/15 on the larger model, which weakens the earlier hypothesis that a small,
low-entropy generation model was the shared cause of every scheme's failure to
embed — for Unigram specifically the more model-agnostic explanation (a static,
non-hash-chained green list is inherently harder to detect against short outputs;
§2.4) looks more likely than a model-size effect. KGW's rate (4/15, mean z 2.2) is
notably lower than STONE's (14/15, mean z 12.0) on this model, the opposite
ordering of reliability from what raw counts alone would suggest is typical for a
"simpler" scheme — consistent with, though not proof of, the reserialization
sensitivity gap in §2.8.

**Not run yet, so no survival numbers exist for this model:** the 22-operation
battery and the lifecycle chain. Every number in this section is a baseline
embedding check only — no mutation has been applied. PF's own test statistic
(mean 227.75, on its own gamma-distribution scale, not a z-score) is far larger in
absolute terms than seen anywhere else in this document; before trusting a
survival rate for PF on this model, its threshold calibration should be checked
independently, since an uncalibrated threshold would show up as a robustness
finding that is actually a detector-config artifact.

## 3. Threats to validity

1. **Single host repository, single generated function per run.** External
   validity to other repositories/languages/code shapes is untested.
2. **Unequal usable sample sizes** (STONE 10/5, KGW 7/4, SWEET 1, EWD 0,
   Unigram 0) — §2.1 and §2.5's comparisons are not matched-N tests; §2.3 and
   §2.4's schemes have no comparison table at all because there is no sample
   to compare.
3. **`delta=4.0`** is shared across Family 1 schemes and Unigram (fair for that
   comparison) but above at least STONE's published default (not fair as a
   general robustness claim). Family 2's other schemes use their own published
   defaults instead, which makes them internally fair but not directly
   comparable to Family 1 on a shared scale.
4. **One generation model used throughout §2.1-2.8** (164M parameters) — Finding 5
   and §2.4 may be specific to models this small/low-entropy. A preliminary
   baseline-embedding check on a 1.3B model (§2.9) shows 3 of 5 previously-untestable
   schemes now embed at low rates, and one (Unigram) still does not — but the
   mutation battery and lifecycle chain have not yet been repeated on the larger
   model, so no survival number in this document reflects it.
5. **Host memory constraints throughout this project.** Multiple long-lived
   multi-scheme processes segfaulted, traced to host memory exhaustion
   (confirmed via direct memory inspection and reproduced on an isolated,
   mutation-free generation call). Every result in this document is from
   runs that completed cleanly under the one-scheme-per-process pattern
   adopted after that diagnosis, not from a crashed run's recovered log.
6. **The `ast.unparse()` confound (Finding 7)**: three of the six human-sourced
   operations share an implementation detail with `ast_roundtrip`, and their
   fragility may be substantially attributable to that shared detail rather
   than to the human-refactor pattern itself. Disclosed, not corrected, in
   this pass (§2.5).
7. **Four Family 2 schemes (Unbiased, DIP, SynthID, PF) are smoke-tested but
   not yet benchmarked at scale** — infrastructure is ready, results are not.
8. **The lifecycle chain is hand-designed, on one host OS, on one model.**
   §2.8 uses five prompts (STONE 13 distinct baselines from 23 usable runs, KGW
   17), so pseudo-replication is reduced but not removed and baselines, not
   runs, are the unit of analysis. Only the lint/format order is mined from real
   CI (20 repositories); the rest of the order is designed. No confidence
   interval from the single-prompt §2.6 runs should be cited.
9. **Uncontrolled mutation randomness in all results before 2026-09-24.**
   The corpus-token draw used Python's per-process-randomized `hash()`, so
   identical input got different mutations in different processes. Fixed;
   existing datasets were not regenerated. §2.6 quantifies the effect for
   STONE (retained-at-end for the dominant short text ranges 10–70% by draw).
10. **The `ast.unparse()` confound: RESOLVED for type hints, remains elsewhere.**
    The type-hint control was run (§2.8): reserialization, not the annotations,
    drives the first-step loss. The original human-sourced battery (§2.5) still
    contains operations whose fragility is inseparable from reserialization.
11. **STONE-vs-KGW comparison is not matched-baseline.** §2.8 uses the share of
    baseline z retained (a headroom-normalised measure) and shows it is not a
    headroom artifact within KGW, but only two STONE baselines fall in KGW's
    z 4-10 range, so a matched test is not possible with this sample.
12. **One generation host repository, and §1-2.8 use one generation model.**
    Prompts share one codebase (the edit corpus was swapped to Flask as a
    robustness check, the generated code was not). §2.9 checks a second, larger
    model for baseline embedding only; other languages and other host
    repositories remain untested.
13. **Recovery mechanism only partly explained** (format re-canonicalisation
    matches 4/13 STONE and 0/17 KGW baselines exactly).

## 4. Reproducing this benchmark

```
# Family 1 (plain kwargs config)
python experiments/stone_pilot/run_full_battery.py \
  --repo <path to a lutris/lutris checkout> \
  --runs 10 --schemes stone,kgw,sweet,ewd \
  --out experiments/stone_pilot/multischeme_results.json

# Family 2 (JSON config file) — cannot be mixed with Family 1 in one process,
# see schemes.py's module docstring; merges into the same --out either way
python experiments/stone_pilot/run_full_battery.py \
  --repo <path to a lutris/lutris checkout> \
  --runs 10 --schemes unigram,unbiased,dip,synthid,pf \
  --out experiments/stone_pilot/multischeme_results.json

# Full-lifecycle chain (§2.6) — cumulative survival through one realistic order
python experiments/stone_pilot/run_lifecycle.py \
  --repo <path to a lutris/lutris checkout> \
  --runs 5 --schemes stone \
  --out experiments/stone_pilot/lifecycle_results.json

# Round 2 controls (§2.8)
python experiments/stone_pilot/run_lifecycle.py --repo <lutris> --schemes stone \
  --runs 25 --hints both --multi-prompt --out experiments/stone_pilot/lifecycle_v2_results.json
python experiments/stone_pilot/scripts/verify_patch_ops.py
python experiments/stone_pilot/scripts/unparse_control.py --repo <lutris> --scheme kgw \
  --texts experiments/stone_pilot/control_texts_kgw.json
python experiments/stone_pilot/scripts/offline_matrix.py --repo <lutris> --scheme kgw --draws 20
# Flask edit corpus: set WM_CORPUS=experiments/stone_pilot/data/human_corpus_flask.json

# Larger model, baseline embedding only (§2.9) — GPU, one family per process
export WM_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct WM_DEVICE=cuda
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15
```

Add `--fresh` to overwrite rather than merge into an existing results file. Each
scheme can also be run as a separate invocation (default merge mode) — the
approach actually used to produce this benchmark, for memory-constrained hosts.
To regenerate the human-mutation corpus from a fresh checkout:
`python experiments/stone_pilot/scripts/mine_human_corpus.py <repo_path>`.
Raw data: `multischeme_results.json` (16-operation battery),
`human_ops_results.json` (22-operation battery with human-sourced mutations),
`lifecycle_results.json` (cumulative full-chain survival, §2.6).
Vendored scheme code and provenance: `vendor/VENDORED.md`.
