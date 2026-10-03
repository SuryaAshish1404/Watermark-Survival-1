# Do the Marks Survive the Pipeline?

**Replication package for an empirical study of whether provenance marks embedded in AI-generated code survive the transformations that code undergoes between generation and release.**

AI-generated code rarely reaches production unchanged. It may be edited by developers, reformatted, linted, minified, rewritten through Git history, or repackaged before release.

This repository evaluates how well code provenance marks survive those real-world transformations.

The study covers:

- **9 published code-watermarking schemes**
- **2 code-generation models**
- **22 real-world code transformations**
- A **9-step cumulative release pipeline**
- Human-style edits derived from real open-source repositories
- Reproducible raw results committed to `experiments/results/`

The repository also includes tooling for mining the transformation operations applied by a repository's CI pipeline.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [CI Mining](#ci-mining)
- [Watermark-Survival Benchmark](#watermark-survival-benchmark)
- [Setup](#setup)
- [Replicating the Results](#replicating-the-results)
  - [Verify the Installation](#1-verify-the-installation)
  - [Single-Operation Battery](#2-single-operation-battery)
  - [Release-Chain Experiments](#3-release-chain-experiments)
  - [Larger Model](#4-larger-model)
  - [Mining Inputs and Repository Operations](#5-mining-inputs-and-repository-operations)
- [Reproducibility](#reproducibility)
- [Watermark Schemes](#watermark-schemes)

---

## Overview

The repository contains two closely related components.

### 1. CI Mining

Located in:

```text
scripts/
tests/
```

The tooling answers questions such as:

- Which code transformations does a repository's CI pipeline perform?
- In what order are those transformations applied?

### 2. Watermark-Survival Benchmark

Located in:

```text
experiments/
```

The benchmark evaluates whether provenance marks embedded in AI-generated code remain detectable after common transformations.

It includes:

- 9 watermarking schemes
- Two generation models
- Individual transformation experiments
- Human-style code mutations
- A cumulative 9-step release pipeline
- Control experiments
- Multiple human-edit corpora
- Raw results for independent analysis

---

# Repository Structure

```text
.
├── README.md
├── requirements.txt
│
├── scripts/
│   └── mining/
│       ├── detectors.py
│       ├── scan.py
│       ├── workflow_order.py
│       ├── catalogue.py
│       └── cli.py
│
├── tests/
│
└── experiments/
    ├── schemes.py
    ├── run_pilot.py
    ├── run_full_battery.py
    ├── run_lifecycle.py
    ├── human_mutations.py
    ├── more_operations.py
    │
    ├── scripts/
    ├── data/
    ├── results/
    └── vendor/
```

---

# CI Mining

| Module | Purpose |
|---|---|
| `mining/detectors.py` | Maps configuration-file signals to operation classes such as formatting, linting, minification, and repackaging |
| `mining/scan.py` | Scans a repository for transformation signals |
| `mining/workflow_order.py` | Extracts operation ordering from GitHub Actions workflows |
| `mining/catalogue.py` | Aggregates repository scans into an operation catalogue |
| `mining/cli.py` | Command-line interface for repository mining |

---

# Watermark-Survival Benchmark

The benchmark lives under `experiments/`.

## Core Experiment Scripts

| Script | Purpose |
|---|---|
| `schemes.py` | Scheme registry, model selection, and pinned model revisions |
| `run_pilot.py` | Single-scheme smoke test and shared mutation helpers |
| `run_full_battery.py` | Applies individual transformations independently |
| `run_lifecycle.py` | Runs the cumulative 9-step release chain |
| `human_mutations.py` | Human-style edits sourced from real repositories |
| `more_operations.py` | Additional operations including type hints, docstrings, and patches |

## Analysis and Control Scripts

| Script | Purpose |
|---|---|
| `baseline_embed_check.py` | Checks whether each scheme produces a detectable mark for each model |
| `quick_scheme_check.py` | Runs one scheme per process to isolate CUDA failures |
| `unparse_control.py` | Separates the effect of type annotations from whole-file `ast.unparse` reserialization |
| `offline_matrix.py` | Factorial experiment over first-step variant, CI order, and random draw |
| `lifecycle_draw_variance.py` | Measures outcome variance caused by random corpus selection |
| `format_recovery_check.py` | Tests whether `ruff format` reverses reserialization damage |
| `verify_patch_ops.py` | Verifies that text-patch operations produce the same program as their AST equivalents |
| `analyze_lifecycle.py` | Computes summary statistics for lifecycle results |
| `mine_human_corpus.py` | Extracts identifiers, comments, and docstrings from repositories for use as human-edit corpora |
| `mine_ci_order.py` | Mines the lint/format order from the GitHub Actions workflows of 20 Python repositories at pinned commits |
| `paper_numbers.py` | Recomputes every number reported in the paper from the committed result files |

---

## Human-Edit Corpora

The benchmark includes human-written material used to make the transformations more representative of actual developer edits.

| File | Description |
|---|---|
| `experiments/data/human_corpus.json` | Identifiers, comments, exception names, docstring openers, and type annotations mined from `lutris/lutris` contributors |
| `experiments/data/human_corpus_flask.json` | Equivalent corpus mined from `pallets/flask`, used as a corpus-robustness check |
| `experiments/data/ci_order_repos.json` | The 20 Python repositories, with pinned commits, whose CI workflows were mined for the lint/format order |

The corpus can be selected with:

```bash
export WM_CORPUS=experiments/data/human_corpus.json
```

---

# Results

Raw experimental results are committed under:

```text
experiments/results/
```

| File | Produced by | Contents |
|---|---|---|
| `results.json` | `run_pilot.py` | Initial STONE smoke test |
| `full_battery_results.json` | `run_full_battery.py` | STONE-only battery |
| `multischeme_results.json` | `run_full_battery.py` | Multi-scheme operation battery |
| `human_ops_results.json` | `run_full_battery.py` | 22-operation battery including human-sourced edits |
| `lifecycle_results.json` | `run_lifecycle.py` | 9-step release chain across all 9 schemes |
| `lifecycle_v2_results.json` | `run_lifecycle.py` | Repeated lifecycle experiment across multiple prompts and mutation variants |
| `control_texts_{stone,kgw}.json` | Lifecycle experiments | Fixed detected baselines used as controls |
| `unparse_control_*.json` | `unparse_control.py` | Annotation vs. reserialization controls |
| `offline_matrix_{stone,kgw}.json` | `offline_matrix.py` | Factorial experiments using the Lutris corpus |
| `offline_matrix_flask_{stone,kgw}.json` | `offline_matrix.py` | Equivalent experiments using the Flask corpus |
| `draw_variance_results.json` | `lifecycle_draw_variance.py` | Variance across random corpus draws |
| `ci_order_results.json` | `mine_ci_order.py` | Observed lint/format order: 281 job sequences from 20 repositories |
| `baseline_embed_*.json` | `baseline_embed_check.py` | Model-specific embedding checks |
| `gpu_battery_results.json` | `run_full_battery.py` | GPU-based 22-operation battery |
---

# Watermark Schemes

Two upstream watermark implementations are vendored into the repository.

| Directory | Schemes | Source |
|---|---|---|
| `experiments/vendor/stone_watermarking/` | STONE, KGW, SWEET, EWD | `inistory/STONE-watermarking` |
| `experiments/vendor/markllm/` | Unigram, Unbiased, DIP, SynthID, PF | `THU-BPM/MarkLLM` |

The vendored files are retained byte-for-byte. `VENDORED.md` records the source revision and license for each file.

The two upstream projects expose packages with overlapping names, so they are intentionally never loaded in the same Python process. This isolation is enforced by `experiments/schemes.py`.

---

# Setup

## Requirements

- Python **3.13**  
  Results were produced with Python **3.13.5**.
- `git` available on `PATH`
- Sufficient CPU resources for unit tests and the default model
- NVIDIA GPU with **CUDA 12.4** for the larger-model experiments
- Approximately **0.6 GB** for the default model
- Approximately **3 GB** for the larger model

Models are downloaded from Hugging Face on first use.

## Installation

Create a virtual environment and install the pinned dependencies:

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
```

For GPU experiments:

```bash
pip install torch==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124
```

---

## Host Repository

The benchmark generates code inside a real repository and applies that repository's own formatting and linting configuration.

The default host repository is `lutris/lutris`. Its formatting and linting configuration (`ruff.toml`) changes over time, so check out the commit used for the result you are reproducing:

```bash
git clone https://github.com/lutris/lutris
git -C lutris checkout <commit>
```

| Commit | Used for |
|---|---|
| `8d882da59c68c8ff7f8eff43b2772c493ddcc088` | `results.json`, `full_battery_results.json`, `multischeme_results.json`, `human_ops_results.json`, `lifecycle_results.json`, `draw_variance_results.json` |
| `01687c6e73e284f634ff33e9edf2f38b6e76bda3` | `lifecycle_v2_results.json`, `offline_matrix_*.json`, `gpu_battery_results.json` |

Commands that accept:

```text
--repo <lutris>
```

expect the path to this checkout.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `WM_MODEL` | `bigcode/tiny_starcoder_py` | Generation model |
| `WM_MODEL_REVISION` | Pinned in `schemes.py` | Optional Hugging Face revision override |
| `WM_DEVICE` | `cpu` | Set to `cuda` for GPU experiments |
| `WM_CORPUS` | `experiments/data/human_corpus.json` | Human-edit corpus |

---

# Replicating the Results

All commands below should be run from the repository root.

## 1. Verify the Installation

These checks require no model download.

```bash
python -m unittest discover -s tests -t .

python experiments/scripts/verify_patch_ops.py

python experiments/scripts/analyze_lifecycle.py

python experiments/scripts/paper_numbers.py
```

Expected behavior:

- All unit tests pass.
- `verify_patch_ops.py` reports `75/75 identical programs` for each of its four operations.
- `analyze_lifecycle.py` reports per-scheme statistics for the 9-step lifecycle.
- `paper_numbers.py` prints every number reported in the paper, section by section, including the bootstrap confidence intervals.

These analysis scripts operate on the committed result files, so they do not regenerate the experiments.

---

## 2. Single-Operation Battery

Each transformation is applied independently so its effect can be measured in isolation.

Run the STONE-family schemes:

```bash
python experiments/run_full_battery.py \
  --repo <lutris> \
  --runs 10 \
  --schemes stone,kgw,sweet,ewd \
  --out experiments/results/multischeme_results.json
```

Run the MarkLLM schemes:

```bash
python experiments/run_full_battery.py \
  --repo <lutris> \
  --runs 10 \
  --schemes unigram,unbiased,dip,synthid,pf \
  --out experiments/results/multischeme_results.json
```

Add `--fresh` to replace the existing output instead of merging into it.

For machines with limited memory, run one scheme per invocation. Results can still be merged into the same output file.

---

## 3. Release-Chain Experiments

### 9-Step Cumulative Release Chain

```bash
python experiments/run_lifecycle.py \
  --repo <lutris> \
  --runs 5 \
  --schemes stone \
  --out experiments/results/lifecycle_results.json
```

### Repeated Lifecycle Experiment

The following runs 25 experiments across 5 prompts and includes both reserialization and in-place edit variants:

```bash
python experiments/run_lifecycle.py \
  --repo <lutris> \
  --schemes stone \
  --runs 25 \
  --hints both \
  --multi-prompt \
  --out experiments/results/lifecycle_v2_results.json
```

### Controls

Verify patch equivalence:

```bash
python experiments/scripts/verify_patch_ops.py
```

Run the `ast.unparse` control:

```bash
python experiments/scripts/unparse_control.py \
  --repo <lutris> \
  --scheme kgw \
  --texts experiments/results/control_texts_kgw.json
```

Run the offline factorial matrix:

```bash
python experiments/scripts/offline_matrix.py \
  --repo <lutris> \
  --scheme kgw \
  --draws 20
```

Measure lifecycle draw variance:

```bash
python experiments/scripts/lifecycle_draw_variance.py \
  --repo <lutris>
```

Check formatting recovery:

```bash
python experiments/scripts/format_recovery_check.py <lutris>
```

### Flask Corpus Robustness Check

```bash
WM_CORPUS=experiments/data/human_corpus_flask.json \
  python experiments/scripts/offline_matrix.py \
  --repo <lutris> \
  --scheme kgw \
  --draws 20 \
  --out experiments/results/offline_matrix_flask_kgw.json
```

---

## 4. Larger Model

### DeepSeek Coder 1.3B

Set the model and CUDA device:

```bash
export WM_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct
export WM_DEVICE=cuda
```

Run the embedding checks:

```bash
python experiments/scripts/baseline_embed_check.py \
  --schemes stone,kgw,sweet,ewd \
  --n 15

python experiments/scripts/baseline_embed_check.py \
  --schemes unigram,unbiased,dip,synthid,pf \
  --n 15
```

Run the 22-operation battery:

```bash
python experiments/run_full_battery.py \
  --repo <lutris> \
  --runs 15 \
  --schemes stone,kgw,sweet,ewd \
  --out experiments/results/gpu_battery_results.json \
  --fresh

python experiments/run_full_battery.py \
  --repo <lutris> \
  --runs 15 \
  --schemes unbiased,synthid,pf \
  --out experiments/results/gpu_battery_results.json
```

---

## 5. Mining Inputs and Repository Operations

### Build a Human-Edit Corpus

Given a repository checkout:

```bash
python experiments/scripts/mine_human_corpus.py \
  <repo> \
  --out <corpus.json>
```

The resulting corpus can then be selected with `WM_CORPUS`.

### Mine a Repository's CI Operation Catalogue

```bash
python -m scripts.mining.cli \
  <repo> [<repo> ...] \
  --out <catalogue.json>
```

This identifies transformation signals in repository configuration and extracts operation ordering from GitHub Actions workflows.

### Reproduce the Observed Lint/Format Order

```bash
python experiments/scripts/mine_ci_order.py
```

This fetches only `.github/workflows` from the 20 repositories in `experiments/data/ci_order_repos.json`, each at its pinned commit, and reproduces the reported counts: 281 job sequences, with lint autofix preceding formatting 29 times and the reverse 15 times. Network access to GitHub is required.

---

# Reproducibility

The repository is designed so that the reported experiments can be independently inspected and regenerated.

### Python dependencies

Exact package versions are pinned in:

```text
requirements.txt
```

This includes dependencies such as `ruff` and `python-minifier`, whose behavior directly affects the transformation and detection pipeline.

### Models

Model weights and tokenizers are loaded from fixed Hugging Face revisions specified in:

```text
experiments/schemes.py
```

### Watermark implementations

The upstream watermark implementations are vendored byte-for-byte under:

```text
experiments/vendor/
```

See `experiments/vendor/VENDORED.md` for source revisions and licensing information.

### Deterministic mutations

Mutations are seeded per input text. The same input therefore receives the same mutation sequence.

### Human-edit corpora

The exact corpora used for the reported experiments are committed under:

```text
experiments/data/human_corpus*.json
```

### Generation

Watermarked code is generated with sampling enabled (`do_sample=True`). Consequently, regenerated experiments reproduce the reported rates statistically rather than necessarily producing identical samples.

Every generated text used in the reported experiments is retained in the result files, allowing the mutation and detection stages to be independently re-evaluated.

---

# Research Artifacts

The repository intentionally commits both **inputs and raw outputs** rather than only aggregated statistics.

This makes it possible to:

1. Inspect the exact generated samples.
2. Re-run mutation and detection stages.
3. Reproduce analysis from committed result files.
4. Test alternative analyses without regenerating model outputs.
5. Compare results across watermarking schemes, models, transformation types, and human-edit corpora.

The combination of pinned dependencies, fixed model revisions, vendored watermark implementations, seeded mutations, committed corpora, and committed raw results is intended to make the study independently auditable and reproducible.
