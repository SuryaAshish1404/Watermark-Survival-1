# Watermark Mutation-Survival Benchmark

A self-contained benchmark of code-watermark survival under ordinary developer
operations, run to inform the anticipatory arm of "Do the Marks Survive the
Pipeline?" (FSE 2027). Written to drop into the paper largely as-is — methods,
metrics, and a results table — not as an internal lab notebook. For the full
narrative, per-run detail, and honest hedging, see `RESULTS.md`; this file is the
condensed, citable version.

## 1. Method

### 1.1 Schemes under test

Four green-list watermarking schemes, drawn from one open-source implementation
family (`github.com/inistory/STONE-watermarking`, commit `bb5d809`, Apache-2.0,
vendored unmodified — see `vendor/VENDORED.md`) so that scheme identity is the
only varying factor and no reimplementation risk is introduced:

| Scheme | Token selection rule | Detection needs the model? |
|---|---|---|
| **STONE** (Kim, Park & Han, Findings of EACL 2026) | Syntax-aware: biases only non-syntax tokens | No |
| **KGW** (Kirchenbauer et al., ICML 2023) | None: biases every generated token | No |
| **SWEET** (Lee et al.) | Entropy-gated: biases only tokens above a fixed entropy cutoff | Yes (recomputes entropy) |
| **EWD** | Entropy-weighted: biases every token like KGW, but weights each token's contribution to the detection statistic by its entropy | Yes (recomputes entropy) |

Two schemes originally selected for the wider study (SrcMarker, CodeIP — see
`docs/06-scheme-selection.md`) were evaluated for inclusion here and excluded on
concrete grounds, not convenience:
- **SrcMarker**: no released pretrained checkpoint (requires training a
  BiGRU encoder/decoder from scratch); official tree-sitter parser support
  covers Java, C++, and JavaScript only — no Python grammar, incompatible with
  this benchmark's host language.
- **CodeIP**: uses a fundamentally different detection paradigm (multi-bit
  message encoding with a two-tokenizer remapping and hash-chained message
  seeds, decoded via bit-accuracy) rather than the green-list z-score interface
  the other four schemes share. Integrating it would mean writing a new adapter
  layer, not configuring an existing one — deferred rather than rushed.

### 1.2 Configuration

All four schemes ran with `gamma=0.5, delta=4.0, hash_key=15485863,
prefix_length=1, z_threshold=4.0` (SWEET additionally: `entropy_threshold=0.9`).
`delta=4.0` is above STONE's paper-typical range (0.5–2.0); raised to keep the
generation model's watermark reliably detectable given its size (see §1.3). The
same value was used for every scheme, so it does not bias the *comparison*
between them, but no rate in §3 should be read as that scheme's robustness at
its own paper-recommended defaults.

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

16 operations across three layers, chosen to cover every class in this study's
mined operation catalogue (`scripts/mining/detectors.py`) that is mechanically
applicable to a single Python file — `transpile` and `bundle` are confirmed
not applicable to a pure-Python codebase (no standard tooling) and excluded on
that basis, not omitted by oversight.

- **History** (real git operations against a temp repo, not simulated diffs):
  squash (plain, and with a reformat pass in the squashed commit), rebase,
  cherry-pick, fork-sync.
- **Source**: `ruff format`, `ruff check --fix`, AST-based variable renaming,
  dead-code insertion, `python-minifier` (mild and aggressive settings),
  AST round-trip (`ast.parse` → `ast.unparse`), and a stacked combination of
  four of the above.
- **Packaging**: bytecode-only compilation (`py_compile`, no source shipped),
  source-preserving zip repackage, and a real wheel build via the PyPA `build`
  frontend (`republish`).

### 1.6 Metric: retention rate under repeated generation

For each (scheme, operation) pair: `detect_watermark()` is run on the mutated
text and classified retained / silently-lost / destroyed-structurally, per this
study's outcome taxonomy (`docs/01-outcome-definitions.md`). This is repeated
across independent generations (STONE: 10, KGW: 10, SWEET: 8, EWD: 8) because
detection is a statistical test, not a deterministic property — a single run's
result is not reported as a rate. A run whose *baseline* (pre-mutation) text
does not itself clear the detection threshold is excluded from that scheme's
denominator and logged separately (§3.2), per the taxonomy's "never emitted"
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

## 3. Threats to validity

1. **Single host repository, single generated function per run.** External
   validity to other repositories/languages/code shapes is untested.
2. **Unequal usable sample sizes** (STONE 10, KGW 7, SWEET 1, EWD 0) — §2.1's
   comparison is not a matched-N test; §2.3's schemes have no comparison table
   at all because there is no sample to compare.
3. **`delta=4.0`** is shared across all schemes (fair for comparison) but above
   at least STONE's published default (not fair as a general robustness claim).
4. **One generation model** (164M parameters) — Finding 5 may be specific to
   models this small/low-entropy; untested against a larger model.
5. **Host memory constraints during this run.** Two earlier attempts at running
   all four schemes as one long-lived process segfaulted, traced to host memory
   exhaustion (confirmed via direct memory inspection and reproduced on an
   isolated, mutation-free generation call). Restructured to run each scheme as
   its own process, merging results into one file — the data reported here is
   from that restructured, successfully-completed run, not the crashed one.

## 4. Reproducing this benchmark

```
python experiments/stone_pilot/run_full_battery.py \
  --repo <path to a lutris/lutris checkout> \
  --runs 10 --schemes stone,kgw,sweet,ewd \
  --out experiments/stone_pilot/multischeme_results.json
```

Add `--fresh` to overwrite rather than merge into an existing results file. Each
scheme can also be run as a separate invocation (default merge mode) — the
approach actually used to produce this benchmark, for memory-constrained hosts.
Raw data: `multischeme_results.json`. Vendored scheme code and provenance:
`vendor/VENDORED.md`.
