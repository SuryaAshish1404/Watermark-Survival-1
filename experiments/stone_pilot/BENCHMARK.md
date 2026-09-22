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
  written by the project's actual contributors) — sampling which real token to
  use is deterministic (seeded by the input), never generated. The other three
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

Every result above measures one operation applied to the *original* baseline,
independently — 30 separate branches off one root. That answers "does
operation X break it alone," not the brief's Phase 5 requirement: *"Test
realistic chains such as: AI-generated code → commit → PR → squash →
formatting → build → package → release. Measure cumulative survival rather
than only individual operations."* `run_lifecycle.py` runs exactly that: one
plausible chain, applied in sequence, with detection re-checked after *every*
step, so degradation compounds the way it actually would in a real pipeline —

```
generate → agent adds type hints → agent adds docstring → review: targeted
patch → review: rename → review: add comment → CI format → CI lint autofix
→ squash merge (with review-branch reformat) → release: build a real wheel
```

(This order is a plausible real-world sequence, not mined from observed CI
configs the way `scripts/mining/workflow_order.py` derives real orders for
the measured arm — a real difference in evidentiary weight from that arm's
methodology, disclosed here rather than presented as equally strong.)

**Result, STONE (5 runs, all usable):**

| Run | First broke at | Score right before packaging | Score at final (Windows-built) artifact |
|---|---|---|---|
| 1 | `agent_add_type_hints` | silently_lost | **retained** |
| 2 | `agent_add_type_hints` | silently_lost | **retained** |
| 3 | `agent_add_type_hints` | retained (recovered at `review_rename`) | retained |
| 4 | `agent_add_type_hints` | silently_lost | **retained** |
| 5 | `agent_add_type_hints` | silently_lost | **retained** |

**Result, KGW (4/5 usable — 1 excluded, baseline never emitted):**

| Run | First broke at | Score right before packaging | Score at final (Windows-built) artifact |
|---|---|---|---|
| 1 | `agent_add_type_hints` | silently_lost | silently_lost |
| 2 | `agent_add_type_hints` | retained (recovered at `ci_format`) | **silently_lost** |
| 3 | `agent_add_type_hints` | silently_lost | silently_lost |
| 4 | `agent_add_type_hints` | silently_lost | silently_lost |

**Finding 8 — a single operation breaks it almost universally.**
`agent_add_type_hints` is the *first* mutation applied to the pristine
baseline in every run, so the "score after step 1" column is also that
operation's isolated single-operation retention rate: **0/5 for STONE, 0/4
for KGW.** This is the most consistent breaking operation found anywhere in
this project — every other operation tested (rename, minify, format, ...) was
scheme-dependent, breaking one scheme and not the other. Adding type hints
broke both.

**Finding 9 — a real discovery, not a simulation artifact: packaging on
Windows silently converts line endings.** STONE's score climbs back above
threshold at the final `release_build_wheel` step in 4 of 5 runs that were
broken going in. Traced rather than assumed: `republish_build_wheel()`
(`run_full_battery.py`) writes the watermarked file to disk via
`Path.write_text(code, encoding="utf-8")` without `newline=""`. On Windows,
text-mode file writes silently translate `\n` → `\r\n` — confirmed directly
by reproduction: a 54-character LF-only sample became 59 characters with
`\r\n` after the same code path. **This is authentic Windows packaging
behavior, not a bug — a developer building this same package on a Windows
machine would hit the identical conversion** — but it means the "release
recovers the watermark" result is a platform-dependent side effect, not
genuine robustness, and it isn't even a *consistent* effect: for KGW's run 2,
the same packaging step pushed a retained score (4.61) back down to lost
(3.72) — the opposite direction. **The score immediately before packaging
(the `merge_squash_with_reformat` column above) is the more realistic
estimate of what a Linux CI build — the actual majority case for real release
pipelines — would ship.**

**By that more realistic measure, cumulative full-chain survival is starkly
low for both schemes**: STONE 1/5, KGW 1/4 — both around 20%, despite STONE
showing 5/5 "survival" at the literal artifact this Windows host happened to
produce. This is the paper's central thesis, demonstrated at the full-pipeline
level rather than asserted from individual-operation results: **checking
provenance only at the final released artifact can look like success while
the signal was actually destroyed for nearly the entire pipeline** — the
"recovery" at the end is not evidence the earlier loss didn't happen.

**Follow-up flagged, not yet actioned**: the same `write_text(...)` pattern
without `newline=""` appears at two other call sites in `run_full_battery.py`
(`_init_git_scenario`, the wheel-build pyproject.toml write) — worth auditing
before any platform-dependence elsewhere in this project is assumed to be
controlled for.

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
4. **One generation model** (164M parameters) — Finding 5 and §2.4 may be
   specific to models this small/low-entropy; untested against a larger model.
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
8. **The lifecycle chain (§2.6) is n=5/n=4, one order, two schemes.** The
   Windows-CRLF discovery is real and reproduced directly, but its effect
   *size* on any other prompt, scheme, or host OS is untested — flagged as a
   platform-dependence risk to control for explicitly in any full Phase 4 run,
   not quantified beyond these two schemes here.

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
