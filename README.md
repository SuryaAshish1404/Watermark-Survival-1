# Do the Marks Survive the Pipeline?

Replication package for an empirical study of whether provenance marks on
AI-generated code survive the steps that code goes through between generation
and release: human edits, formatting, linting, minification, git history
rewrites, and packaging.

The package has two parts:

- **Provenance tooling** (`scripts/`, `tests/`, `docs/`): checks for commit
  trailers, signatures and build attestations, and mining of the operations a
  repository's CI actually applies.
- **Watermark-survival benchmark** (`experiments/`): nine published
  code-watermarking schemes, three generation models, a battery of 22
  real-world operations, and a 9-step end-to-end release chain. Every raw result
  is committed in `experiments/results/`.

---

## 1. What is where

```
.
├── README.md                  this file
├── requirements.txt           pinned Python dependencies
├── docs/                      specifications the provenance tooling implements
├── scripts/                   provenance tooling (importable package)
│   ├── recovery/              is a provenance mark present / valid?
│   └── mining/                which operations does a repo's CI apply?
├── tests/                     unit tests (run these first)
└── experiments/               watermark-survival benchmark
    ├── schemes.py             scheme registry, model choice, pinned model revisions
    ├── run_pilot.py           single-scheme smoke test + shared mutation helpers
    ├── run_full_battery.py    single-operation battery (each operation applied alone)
    ├── run_lifecycle.py       9-step cumulative release chain
    ├── human_mutations.py     human-style edits sourced from a real corpus
    ├── more_operations.py     second wave of operations (type hints, docstrings, patches)
    ├── scripts/               controls and analyses (§1.3)
    ├── data/                  human edit corpora (inputs, §1.4)
    ├── results/               raw results (outputs, §1.5)
    └── vendor/                upstream watermark code, unmodified (§1.6)
```

### 1.1 Specifications (`docs/`)

| File | What it defines | Implemented in |
|---|---|---|
| `01-outcome-definitions.md` | outcomes: retained / silently lost / spuriously gained, per carrier | `scripts/recovery/outcomes.py` |
| `02-substantially-human-rule.md` | when a module counts as substantially human (spurious-gain check) | `outcomes.classify_spurious_only` |
| `03-before-state.md` | how "emitted, then destroyed" is established for each carrier | `scripts/recovery/`, `tests/gitfixture.py` |

### 1.2 Provenance tooling (`scripts/`)

| Module | Purpose |
|---|---|
| `recovery/trailer.py` | agent / co-authorship commit trailer presence |
| `recovery/signature.py` | commit signature presence and verification |
| `recovery/attestation.py` | build attestation / SBOM presence |
| `recovery/outcomes.py` | classifies each carrier's outcome per `docs/01` |
| `mining/detectors.py` | config-file signals → operation class (format, lint, minify, repackage, …) |
| `mining/scan.py` | scans one repository for those signals |
| `mining/workflow_order.py` | operation order from GitHub Actions step sequences |
| `mining/catalogue.py` | aggregates scans into a ranked operation catalogue |
| `mining/cli.py` | command-line entry point (§3.5) |

### 1.3 Benchmark scripts (`experiments/scripts/`)

| Script | Purpose | Loads model |
|---|---|---|
| `baseline_embed_check.py` | does each scheme embed a detectable mark at all, per model | yes |
| `quick_scheme_check.py` | same, one scheme per process (isolates CUDA crashes) | yes |
| `unparse_control.py` | separates the effect of type annotations from whole-file `ast.unparse` reserialization | tokenizer only |
| `offline_matrix.py` | factorial over saved baselines: first-step variant × CI order × random draw | tokenizer only |
| `lifecycle_draw_variance.py` | how much of the chain outcome comes from the random corpus draw | tokenizer only |
| `format_recovery_check.py` | whether `ruff format` undoes reserialization damage | no |
| `verify_patch_ops.py` | each text-patch operation yields the same program as its AST twin | no |
| `analyze_lifecycle.py` | summary statistics for a lifecycle results file | no |
| `mine_human_corpus.py` | mines identifiers/comments/docstrings from a repo into an edit corpus | no |

### 1.4 Inputs (`experiments/data/`)

| File | Contents |
|---|---|
| `human_corpus.json` | identifiers, comments, exception names, docstring openers and type annotations written by lutris/lutris contributors; default source for human-style edits |
| `human_corpus_flask.json` | the same, mined from pallets/flask; corpus robustness check (select with `WM_CORPUS`) |

### 1.5 Outputs (`experiments/results/`)

Script paths in this table are relative to `experiments/`.

| File | Produced by | Contents |
|---|---|---|
| `results.json` | `run_pilot.py` | first STONE smoke test, 6 operations |
| `full_battery_results.json` | `run_full_battery.py` | STONE-only battery, 5 runs |
| `multischeme_results.json` | `run_full_battery.py` | 16-operation battery: STONE, KGW, SWEET, EWD |
| `human_ops_results.json` | `run_full_battery.py` | 22-operation battery incl. human-sourced edits: STONE, KGW, Unigram |
| `lifecycle_results.json` | `run_lifecycle.py` | 9-step release chain, all 9 schemes |
| `lifecycle_v2_results.json` | `run_lifecycle.py --hints both --multi-prompt` | chain rerun, 25 runs over 5 prompts, reserialized and in-place edit variants: STONE, KGW |
| `control_texts_{stone,kgw}.json` | saved from the runs above | detected baselines used as fixed control inputs |
| `unparse_control_*.json` | `scripts/unparse_control.py` | annotation vs. reserialization control |
| `offline_matrix_{stone,kgw}.json` | `scripts/offline_matrix.py` | factorial matrix, lutris corpus |
| `offline_matrix_flask_{stone,kgw}.json` | same, with the Flask corpus | factorial matrix, Flask corpus |
| `draw_variance_results.json` | `scripts/lifecycle_draw_variance.py` | outcome variance across random draws |
| `baseline_embed_stone_kgw_sweet_ewd.json`, `baseline_embed_unigram_unbiased_dip_synthid_pf.json` | `scripts/baseline_embed_check.py` | embedding check, deepseek-coder-1.3b |
| `gpu_battery_results.json` | `run_full_battery.py` | 22-operation battery, deepseek-coder-1.3b |
| `baseline_embed_qwen_f{1,2}.json` | `scripts/baseline_embed_check.py` | embedding check, Qwen2.5-Coder-1.5B |

### 1.6 Vendored schemes (`experiments/vendor/`)

| Folder | Schemes | Upstream |
|---|---|---|
| `stone_watermarking/` | STONE, KGW, SWEET, EWD | github.com/inistory/STONE-watermarking @ `bb5d809` |
| `markllm/` | Unigram, Unbiased, DIP, SynthID, PF | github.com/THU-BPM/MarkLLM, fetched 2026-09-21 |

Files are byte-for-byte copies; `VENDORED.md` lists every file, its source and
its license (Apache 2.0). The two families define packages with the same names,
so they never run in the same Python process (enforced in `schemes.py`).

---

## 2. Setup

**Requirements**

- Python 3.13 (results produced with 3.13.5)
- `git` on `PATH`
- CPU: enough for the tests, the offline checks and the default model
  (`bigcode/tiny_starcoder_py`)
- GPU: an NVIDIA GPU with CUDA 12.4 for the deepseek-coder-1.3b and
  Qwen2.5-Coder-1.5B runs
- Disk: ~0.6 GB for the default model, ~3 GB for each larger model
  (downloaded from Hugging Face on first use)

**Install**

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# GPU runs only:
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
```

**Host repository.** Generated code is written into a real project and
formatted/linted with that project's own `ruff.toml`:

```
git clone https://github.com/lutris/lutris
```

Every command below that takes `--repo <lutris>` expects the path to this
checkout.

**Environment variables**

| Variable | Default | Purpose |
|---|---|---|
| `WM_MODEL` | `bigcode/tiny_starcoder_py` | generation model |
| `WM_MODEL_REVISION` | pinned per model in `schemes.py` | Hugging Face commit override |
| `WM_DEVICE` | `cpu` | set to `cuda` for GPU runs |
| `WM_CORPUS` | `experiments/data/human_corpus.json` | human edit corpus |

---

## 3. Replicating the results

All commands run from the repository root.

### 3.1 Verify the installation (≈2 min, no model)

```
python -m unittest discover -s tests -t .
python experiments/scripts/verify_patch_ops.py
python experiments/scripts/analyze_lifecycle.py
```

Expected: all tests pass (the GPG signature test is skipped if `gpg` is not
installed); `verify_patch_ops.py` prints `75/75 identical programs` for each of
its four operations; `analyze_lifecycle.py` prints the per-scheme chain
statistics for the 9-step chain. Both scripts read the committed results, so
they re-derive reported numbers without regenerating anything.

### 3.2 Single-operation battery (CPU)

Each scheme family runs in its own process; both merge into the same output.

```
python experiments/run_full_battery.py --repo <lutris> --runs 10 \
  --schemes stone,kgw,sweet,ewd --out experiments/results/multischeme_results.json
python experiments/run_full_battery.py --repo <lutris> --runs 10 \
  --schemes unigram,unbiased,dip,synthid,pf --out experiments/results/multischeme_results.json
```

Add `--fresh` to overwrite instead of merging. On memory-constrained machines,
run one scheme per invocation; results merge the same way.

### 3.3 Release-chain survival and controls (CPU)

```
# 9-step cumulative chain
python experiments/run_lifecycle.py --repo <lutris> --runs 5 --schemes stone \
  --out experiments/results/lifecycle_results.json

# Repeated chain: 25 runs over 5 prompts, reserialized and in-place edit variants
python experiments/run_lifecycle.py --repo <lutris> --schemes stone \
  --runs 25 --hints both --multi-prompt --out experiments/results/lifecycle_v2_results.json

# Controls
python experiments/scripts/verify_patch_ops.py
python experiments/scripts/unparse_control.py --repo <lutris> --scheme kgw \
  --texts experiments/results/control_texts_kgw.json
python experiments/scripts/offline_matrix.py --repo <lutris> --scheme kgw --draws 20
python experiments/scripts/lifecycle_draw_variance.py --repo <lutris>
python experiments/scripts/format_recovery_check.py <lutris>

# Flask corpus robustness check
WM_CORPUS=experiments/data/human_corpus_flask.json \
  python experiments/scripts/offline_matrix.py --repo <lutris> --scheme kgw --draws 20 \
  --out experiments/results/offline_matrix_flask_kgw.json
```

### 3.4 Larger models (GPU)

```
# deepseek-coder-1.3b: embedding check and 22-operation battery
export WM_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct WM_DEVICE=cuda
python experiments/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15
python experiments/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15
python experiments/run_full_battery.py --repo <lutris> --runs 15 \
  --schemes stone,kgw,sweet,ewd --out experiments/results/gpu_battery_results.json --fresh
python experiments/run_full_battery.py --repo <lutris> --runs 15 \
  --schemes unbiased,synthid,pf --out experiments/results/gpu_battery_results.json

# Qwen2.5-Coder-1.5B: embedding check
export WM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct WM_DEVICE=cuda
python experiments/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15 \
  --out experiments/results/baseline_embed_qwen_f1.json
python experiments/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15 \
  --out experiments/results/baseline_embed_qwen_f2.json
```

### 3.5 Inputs and provenance tooling

```
# Rebuild an edit corpus from a repository checkout
python experiments/scripts/mine_human_corpus.py <repo> --out <corpus.json>

# Mine the operation catalogue from one or more repository checkouts
python -m scripts.mining.cli <repo> [<repo> ...] --out <catalogue.json>
```

---

## 4. Reproducibility

- **Python packages:** exact versions in `requirements.txt`, including `ruff`
  and `python-minifier`, whose output feeds the detectors directly.
- **Models:** weights and tokenizers load from fixed Hugging Face commits
  (`MODEL_REVISIONS` in `experiments/schemes.py`).
- **Watermark schemes:** upstream code vendored byte-for-byte
  (`experiments/vendor/VENDORED.md`).
- **Mutations:** seeded per input text, so the same code always receives the
  same edits.
- **Edit corpora:** `experiments/data/human_corpus*.json` are the inputs used
  for every reported result.
- **Generation:** watermarked code is sampled (`do_sample=True`), so a rerun
  reproduces the reported rates statistically. Every generated text is kept in
  the result files, so mutation and detection can be re-checked exactly against
  them.
