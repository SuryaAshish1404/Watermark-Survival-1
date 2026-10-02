# Watermark Survival Across Three Generation Models — GPU Results

**Status:** preliminary, 2026-09-29 through 2026-10-02. Covers three generation
models, all run on a 6 GB VRAM GPU: the original `bigcode/tiny_starcoder_py`
(164M parameters, CPU, used for every result before this file existed),
`deepseek-ai/deepseek-coder-1.3b-instruct` (1.3B, fp16), and
`Qwen/Qwen2.5-Coder-1.5B-Instruct` (1.5B, fp16 — deliberately chosen to be in
the *same size class* as the deepseek model, not bigger, to separate "model
scale" from "which specific model" as an explanation). This file does not
repeat the full small-model benchmark methodology (see `BENCHMARK.md` §1-2.8
for that). The content here is also folded into `BENCHMARK.md` as §2.9, §2.10,
and §2.11.

## Why this run exists

Five of nine watermarking schemes never produced a single detectable watermark
across 25 combined attempts on the old 164M model (SWEET, Unigram, Unbiased,
SynthID, PF). That made it impossible to say anything about their robustness —
there was nothing to test. The working hypothesis was that the model was too
small/low-entropy to give these schemes room to embed a signal. A 6 GB VRAM
GPU became available partway through the project, which let us check that
hypothesis directly.

## Setup

- Model: `deepseek-ai/deepseek-coder-1.3b-instruct`, fp16, ~2.7 GB VRAM used
  (comfortable headroom on a 6 GB card).
- Same watermarking config as every earlier result: `delta=4.0`, `z_threshold=4.0`
  where applicable; each Family-2 scheme otherwise uses its own published default.
- Generation now configurable via `WM_MODEL` / `WM_DEVICE` environment variables
  (`schemes.py`); defaults are unchanged (`tiny_starcoder_py` on CPU) unless set.

**One real bug found and fixed along the way:** `Unigram`'s green-list mask was
sized off `len(tokenizer)` (32,022), but this model's actual output embedding is
padded to 32,256 for tensor-core efficiency. The mismatch caused an out-of-bounds
CUDA write that corrupted the process's CUDA context, which then produced an
unrelated-looking crash in whatever scheme ran next in the same process. Fixed
by sizing the green-list mask off the model's real output width
(`model.config.vocab_size`) instead of the tokenizer's logical vocabulary.
`tiny_starcoder_py` never hit this because its tokenizer length and embedding
size happen to match exactly.

## Part 1 — Can each scheme embed a detectable watermark at all?

15 generate-then-detect attempts per scheme, no mutations applied, cycled
across 5 different prompts. Run on all three models.

| Scheme | 164M (`tiny_starcoder`) | 1.3B (`deepseek-coder`) | 1.5B (`Qwen2.5-Coder`) |
|---|---|---|---|
| STONE | 25/25 | 14/15 | **15/15** |
| KGW | 18/25 | 4/15 | **13/15** |
| SWEET | 0/25 — never | 0/15 (2/10 on a same-prompt repeat) | **4/15** |
| EWD | 1/5 | 4/15 (4/10 on a same-prompt repeat) | **12/15** |
| Unigram | 0/25 — never | 0/15 | 0/15 — never on any model |
| Unbiased | 0/25 — never | **3/15** | 1/15 |
| DIP | 1/5 | 0/15 | **3/15** |
| SynthID | 0/25 — never | **1/15** | 3/15 |
| PF | 0/25 — never | 3/15 | **9/15** |

**Three schemes that never once embedded a detectable watermark on the small
model now do on a bigger one: Unbiased, SynthID, PF.** Real, if low-rate,
progress — these are testable for the first time in this project.

**Qwen2.5-Coder beats deepseek-coder on every Family-1 scheme (STONE, KGW,
SWEET, EWD), despite being essentially the same size (1.5B vs 1.3B).** This is
the key result of adding a third model: it separates "a bigger model gives more
room for the watermark" from "this particular model's training matters." KGW
and EWD roughly triple their embedding rate between the two similarly-sized
models — so parameter count alone doesn't explain the earlier jump; the
specific model (likely its code-focused instruction tuning) does real,
independent work too.

**Unigram is 0/15 or 0/25 on all three models, including two different models
at the "bigger" size class.** That rules out "needs a bigger model" as the
explanation for Unigram specifically — a static, non-hash-chained green list
looks weak on short generated functions as a property of its own design.

**Correlation between models' per-scheme embedding rates** (Pearson r, 9
schemes, each estimated from 5-25 runs — directional, not precise):

| | 164M vs 1.3B | 164M vs 1.5B | 1.3B vs 1.5B |
|---|---|---|---|
| r | 0.84 | 0.79 | 0.76 |

All three pairs correlate strongly — a scheme's rough ranking holds up across
models, so scheme design is still the single biggest factor. But no pair
reaches r > 0.9, and the two closest-in-size models (1.3B vs 1.5B) are the
*weakest*-correlated pair of the three, reinforcing that which specific model
you use moves results by a real amount, not just how big it is.

**SWEET and EWD go from "effectively untestable" to "sometimes works."**
Confirmed as a real (if uncommon) rate, not a single lucky draw, by an
independent repeat on one fixed prompt (SWEET 2/10, EWD 4/10).

**Unigram still never embeds, even on the bigger model.** This weakens the
"model was too small" explanation for Unigram specifically — a fixed,
non-hash-chained green list looks like it has a weak signal on short generated
functions more or less regardless of model size, which is itself a finding
about that design, not about our test setup.

**KGW looks less reliable relative to STONE on this model** (4/15 vs. 14/15)
than it did on the old one — consistent with, though not proof of, the
reserialization-sensitivity gap found earlier in this project (see
`BENCHMARK.md` §2.8, Finding 13: KGW loses far more signal than STONE when code
is reserialized rather than edited in place).

**Caveat on PF:** its test statistic (mean 227.75 in one run) is on its own
gamma-distribution scale, not a z-score, and is far larger in absolute terms
than anything else in this document. Its threshold calibration should be
checked independently before trusting any robustness claim for it.

## Part 2 — Does the watermark survive individual operations?

The full 22-operation battery (one mutation at a time, from a fresh baseline),
15 attempts per scheme, **one fixed prompt** (`run_full_battery.py` does not
yet cycle prompts the way the lifecycle runner does). Unigram and DIP were
skipped — both showed 0/15 baseline embedding above, not worth the GPU time.

| Scheme | Usable baselines | Baseline z (mean, range) |
|---|---|---|
| STONE | 15/15 | 13.3 (6.0 – 21.7) |
| KGW | **0/15** | — |
| SWEET | 2/15 | 4.78 (4.74 – 4.82) |
| EWD | 3/15 | 5.19 (4.10 – 5.86) |
| Unbiased | 6/15 | own scale (p-value-adjacent, not z-score) |
| SynthID | 2/15 | own scale |
| PF | **0/15** | — |

**KGW and PF got zero usable baselines in this run**, despite both embedding
successfully in Part 1's 5-prompt check (KGW 4/15, PF 3/15). This is not a
contradiction — it's direct evidence that for these two schemes, whether the
watermark embeds at all depends heavily on the *specific prompt* used, not
just on the scheme or model. Neither has any mutation-survival data on this
model yet; that needs a multi-prompt version of `run_full_battery.py`
(`run_lifecycle.py` already has `--multi-prompt`; `run_full_battery.py` does
not yet).

**The operation-class pattern from every earlier stage of this project
replicates here — including on a scheme with a completely different detection
mechanism.** Across STONE, SWEET, EWD, *and* Unbiased:

- Version-control operations (squash merge, rebase, cherry-pick, fork-sync),
  packaging that keeps the source, `format`, and `lint_autofix` **retained the
  watermark in every single usable run.**
- Operations that rewrite identifiers or structure (`rename`, `minify`,
  `dead_code_insert`, `extract_helper_function`, `add_type_hints`, all six
  `human_*` operations, `targeted_patch`) **lost the watermark in effectively
  every usable run** for the low-headroom schemes (SWEET, EWD, SynthID,
  Unbiased). For STONE's much stronger baselines, only the two deliberately
  adversarial mutations (`stacked_adversarial`, `aggressive_minify`)
  meaningfully dented its 15/15.

**Unbiased reproducing this exact split is the most interesting result here.**
It's a distortion-free scheme with a p-value detector, sharing no green-list
mechanism with STONE/SWEET/EWD. The same operation-class split showing up
there is evidence the pattern is about *what a mutation does to the token
stream*, not an artifact of one detection family.

## What this does and doesn't tell us yet

**Established:**
- A larger model changes *which schemes can be tested at all* (3 schemes went
  from zero to nonzero on deepseek-coder).
- A third, similarly-sized-but-different model (Qwen2.5-Coder) shows this isn't
  just about scale: it outperforms deepseek-coder on every Family-1 scheme at
  essentially the same parameter count.
- The "VCS/packaging/format/lint survive, content-rewriting destroys" pattern
  (from §2.10, deepseek-coder only so far) generalizes across model size and
  across a structurally different scheme (Unbiased).
- Unigram's failure to embed looks like a property of the scheme, not the
  model — it is 0/15 or 0/25 on all three models tried, including two in the
  "bigger" size class.
- Per-scheme embedding rates correlate strongly but not perfectly across all
  three model pairs (r = 0.76-0.84) — scheme design dominates, but which
  specific model is used still moves individual schemes meaningfully.

**Not yet established on any model but the small one:**
- Any real survival *rate* for KGW or PF on deepseek-coder (0 usable baselines
  on `run_full_battery.py`'s single prompt).
- Whether the reserialization-vs-text-patch finding (§2.8's central result)
  holds on either larger model — not yet re-run as a control on either.
- Anything about the 9-step cumulative lifecycle chain on either larger model —
  not yet run at all.
- The full 22-operation battery on Qwen2.5-Coder — only the baseline-embedding
  check (Part 1) has been run on it so far.
- Real numbers for Unigram, DIP (never/rarely embed) or a confident number for
  several other schemes (sample sizes of 2-4 usable baselines in places).

## Reproducing this

```bash
export WM_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct WM_DEVICE=cuda

# Part 1 — baseline embedding only, 5-prompt cycle
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15

# Part 2 — full 22-operation battery, single prompt
python experiments/stone_pilot/run_full_battery.py --repo <lutris checkout> --runs 15 \
  --schemes stone,kgw,sweet,ewd --out experiments/stone_pilot/gpu_battery_results.json --fresh
python experiments/stone_pilot/run_full_battery.py --repo <lutris checkout> --runs 15 \
  --schemes unbiased,synthid,pf --out experiments/stone_pilot/gpu_battery_results.json

# Third model (Part 1 only so far) — same size class as deepseek-coder, different architecture
export WM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct WM_DEVICE=cuda
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15 \
  --out experiments/stone_pilot/baseline_embed_qwen_f1.json
python experiments/stone_pilot/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15 \
  --out experiments/stone_pilot/baseline_embed_qwen_f2.json
```

Raw data: `baseline_embed_stone_kgw_sweet_ewd.json`,
`baseline_embed_unigram_unbiased_dip_synthid_pf.json`, `gpu_battery_results.json`,
`baseline_embed_qwen_f1.json`, `baseline_embed_qwen_f2.json`.

## Suggested next steps

1. Add prompt-cycling to `run_full_battery.py` so KGW and PF can actually be
   assessed on deepseek-coder (same fix `run_lifecycle.py` already has).
2. Re-run the §2.8 reserialization-vs-text-patch control on both larger models.
3. Run the full 22-operation battery and the 9-step lifecycle chain on
   Qwen2.5-Coder, at minimum for STONE/KGW (its strongest two schemes here).
4. Independently verify PF's threshold calibration before trusting any of its
   numbers.
5. A fourth model outside the ~1.3-1.5B size class (meaningfully bigger or a
   non-code-specialized model of similar size) would help separate "code-tuned
   training helps" from "Qwen2.5-Coder specifically is just a stronger model."
