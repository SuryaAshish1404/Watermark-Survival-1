# Do the Marks Survive the Pipeline?

Replication package for an empirical study of code-watermark persistence under software-engineering transformations. The package contains the benchmark harness, the vendored watermark implementations, the input corpora, every raw result file reported in the paper, and the analysis scripts that recompute the reported numbers.

**Scope.** 9 watermarking schemes (STONE, KGW, SWEET, EWD, Unigram, Unbiased, DIP, SynthID, PF); 2 generation models (`bigcode/tiny_starcoder_py`, 164M; `deepseek-ai/deepseek-coder-1.3b-instruct`, 1.3B); 30 single operations grouped by source-rewriting mechanism; a 9-step cumulative lifecycle; a controlled comparison of targeted text patches against whole-file AST reserialization.

---

## Table of Contents

- [Repository Layout](#repository-layout)
- [Experimental Configuration](#experimental-configuration)
- [Operations](#operations)
- [Lifecycle and Controlled Comparison](#lifecycle-and-controlled-comparison)
- [Result Files](#result-files)
- [Setup](#setup)
- [Replicating the Results](#replicating-the-results)
- [CI Mining](#ci-mining)
- [Determinism and Reproducibility](#determinism-and-reproducibility)

---

## Repository Layout

```text
.
├── requirements.txt              pinned dependencies (Python 3.13.5)
├── scripts/mining/               CI configuration and workflow-order mining
├── tests/                        unit tests (mining, package layout)
└── experiments/
    ├── schemes.py                scheme registry, scheme parameters, pinned model revisions
    ├── run_pilot.py              single-scheme pilot; formatting, lint, rename, minify, AST round-trip operations
    ├── run_full_battery.py       single-operation battery (each operation applied to the unmodified baseline)
    ├── run_lifecycle.py          9-step cumulative lifecycle
    ├── human_mutations.py        human-sourced operations (vocabulary from a mined corpus)
    ├── more_operations.py        additional operations and their text-patch equivalents
    ├── scripts/                  controls, analyses, corpus and CI-order mining
    ├── data/                     human-edit corpora, CI-order repository list
    ├── results/                  raw result files (JSON)
    └── vendor/                   upstream watermark code (see vendor/VENDORED.md)
```

---

## Experimental Configuration

**Generation.** Sampling with `top_k=50`, `temperature=0.7`, `max_new_tokens=160`, `num_beams=1`. Output is trimmed to its longest syntactically valid prefix before any operation (`run_pilot._largest_parseable_prefix`). Model weights and tokenizers load from fixed Hugging Face revisions (`MODEL_REVISIONS` in `schemes.py`): `tiny_starcoder_py@8547527`, `deepseek-coder-1.3b-instruct@e063262`.

**Schemes.** Two vendored implementation families. They define packages with identical top-level names (`watermark`, `utils`, `exceptions`, `visualize`), so each process loads exactly one family; `schemes.assert_single_family` raises otherwise.

| Family | Schemes | Source | Parameters |
|---|---|---|---|
| 1 | STONE, KGW, SWEET, EWD | `inistory/STONE-watermarking@bb5d809` | $\gamma=0.5$, $\delta=4.0$, hash key 15485863, prefix length 1, $z$ threshold 4.0; STONE `language=python`, `skipping_rule=all_pl`; KGW `f_scheme=time`, `window_scheme=left`; SWEET entropy threshold 0.9 |
| 2 | Unigram, Unbiased, DIP, SynthID, PF | `THU-BPM/MarkLLM` | upstream default configs (`vendor/markllm/config/*.json`); Unigram overridden to $\delta=4.0$, $z$ threshold 4.0 |

Family 1 detectors return a $z$-score. Family 2 detectors return scheme-specific statistics (Unbiased a $p$-value; SynthID a mean score against threshold 0.52; PF its own statistic), so retention is comparable within a scheme, not across families.

**Baseline usability.** A generation is a usable baseline if the detector reports it as watermarked before any operation. Unusable generations are recorded with `"excluded": "baseline_never_emitted"` and are not scored.

**Detection outcomes** (`run_full_battery.classify`): `retained`, `silently_lost` (source available, detector negative), `destroyed_no_source` (bytecode-only artifact, no source to detect), `build_failure` (output no longer parses), `tool_error`.

**Execution settings.** Experiments on the 164M model ran on CPU in fp32; DeepSeek experiments ran on GPU (CUDA 12.4) in fp16 (`schemes.DEVICE`, set via `WM_DEVICE`). Baseline usability depends on the execution setting, so results are compared only within one setting.

---

## Operations

Each operation is a mutation `f(source, repo) -> source` applied to the unmodified baseline. The current battery (`run_full_battery.py`) applies 30 operations, grouped by how they rewrite the source:

| Mechanism | Operation ids | Implementation |
|---|---|---|
| Text-level edits (4) | `crlf_line_endings`, `tabs_to_spaces`, `human_add_comment`, `file_rename_only` | string edits; no reparse |
| Tool-based rewriting (4) | `format`, `lint_autofix`, `minify`, `aggressive_minify` | `ruff format` / `ruff check --fix` with the host repository's `ruff.toml`; `python-minifier` |
| AST reserialization (13) | `ast_roundtrip`, `rename`, `dead_code_insert`, `stacked_adversarial`, `human_rename`, `human_add_error_handling`, `human_extract_variable`, `human_guard_clause`, `human_reorder_statements`, `add_real_docstring`, `add_type_hints`, `extract_helper_function`, `targeted_patch` | `ast.parse` → `NodeTransformer` → `ast.unparse` of the whole file |
| Model regeneration (1) | `agent_rewrite` | keeps signature and docstring; the generation model regenerates the body without the watermark |
| History (5) | `squash_plain`, `squash_with_reformat`, `rebase_plain`, `cherry_pick_plain`, `fork_sync` | literal git operations in a scratch repository with `core.autocrlf=false`; `squash_plain` squashes a branch that appends two review comments, `squash_with_reformat` a branch that applies `ruff format`; `fork_sync` clones the scratch repository, and the clone inherits the host's global `core.autocrlf` |
| Packaging (3) | `repackage_zip_with_source`, `republish_wheel`, `rebuild_bytecode_only` | zip with source; wheel via `python -m build`; zip with `py_compile` bytecode only |

`targeted_patch` flips the first comparison operator and is implemented through AST reserialization; it is distinct from the targeted text patches of the controlled comparison.

Human-sourced operations insert vocabulary (identifiers, comments, exception names, docstrings, annotations) drawn from a corpus mined from the host repository (`data/human_corpus.json`); the corpus is selected with `WM_CORPUS`.

---

## Lifecycle and Controlled Comparison

**Lifecycle** (`run_lifecycle.py`). Steps applied cumulatively, with detection after each step:

1. `agent_add_type_hints` 2. `agent_add_docstring` 3. `review_targeted_patch` 4. `review_rename` 5. `review_add_comment` 6. `ci_format` 7. `ci_lint_autofix` 8. `merge_squash_with_reformat` 9. `release_build_wheel`

`--hints patch` replaces step 1 with `agent_add_type_hints_patch` (text patch); `--hints both` runs both first-step variants from the same baseline (`chain`, `chain_patch`). `--multi-prompt` cycles runs over 5 prompts.

**Controlled comparison** (`experiments/scripts/offline_matrix.py`). Replays the distinct detected baselines of `lifecycle_v2_results.json` through three chains crossed with two CI orders, 20 draws per baseline:

| Chain | Edits |
|---|---|
| `unparse_chain` | type hints, docstring, comparison flip, rename via `ast.unparse`; comment insertion |
| `patch_chain` | the same edits and draws as text patches at AST-reported positions |
| `roundtrip_only` | one `ast.unparse`, no edits |

| Order | CI steps |
|---|---|
| `format_then_lint` | `ruff format`, then `ruff check --fix` |
| `lint_then_format` | `ruff check --fix`, then `ruff format` |

Squash and wheel build are omitted from the replay. Detection uses the tokenizer only (STONE, KGW). Per baseline, continuous retention (`never_broke`) is the fraction of draws whose score never falls below threshold, and final retention (`end_retained`) the fraction detectable after the last step. Baselines are the unit of analysis: draws are averaged within a baseline, then baselines are bootstrapped (2000 resamples, `random.Random(0)`, percentile 95% CI).

**Program equivalence.** Each text-patch operation is checked against its AST sibling with the same draw: `ast.dump(ast.parse(patch)) == ast.dump(ast.parse(unparse))` (`experiments/scripts/verify_patch_ops.py`; `experiments/scripts/unparse_control.py` records `all_same_program` per baseline).

---

## Result Files

All files are in `experiments/results/`; script paths are relative to `experiments/`. "lutris" is the host-repository commit the run used.

| File | Script | Model / device | Design | lutris |
|---|---|---|---|---|
| `results.json` | `run_pilot.py` | 164M / CPU | STONE, 1 run, 6 operations | `8d882da` |
| `full_battery_results.json` | `run_full_battery.py` | 164M / CPU | STONE, 5 runs, 16 operations | `8d882da` |
| `multischeme_results.json` | `run_full_battery.py` | 164M / CPU | STONE, KGW 10 runs; SWEET, EWD 8 runs; 16 operations | `8d882da` |
| `human_ops_results.json` | `run_full_battery.py` | 164M / CPU | STONE, KGW, Unigram 5 runs; 22 operations | `8d882da` |
| `lifecycle_results.json` | `run_lifecycle.py` | 164M / CPU | STONE, KGW 25 runs; other 7 schemes 5 runs; 9 steps | `8d882da` |
| `draw_variance_results.json` | `scripts/lifecycle_draw_variance.py` | 164M tokenizer / CPU | 5 texts × 60 draws | `8d882da` |
| `lifecycle_v2_results.json` | `run_lifecycle.py --hints both --multi-prompt` | 164M / CPU | STONE, KGW 25 runs, 5 prompts | `01687c6` |
| `control_texts_{stone,kgw}.json` | from `lifecycle_v2_results.json` | – | distinct detected baselines (13 STONE, 17 KGW) | – |
| `unparse_control_{stone,kgw}.json` | `scripts/unparse_control.py` | 164M tokenizer / CPU | 13 / 17 baselines × 30 draws | – |
| `unparse_control_results.json` | `scripts/unparse_control.py` | 164M tokenizer / CPU | STONE, 5 texts × 40 draws | – |
| `offline_matrix_{stone,kgw}.json` | `scripts/offline_matrix.py` | 164M tokenizer / CPU | 3 chains × 2 orders × 20 draws; lutris corpus | `01687c6` |
| `offline_matrix_flask_{stone,kgw}.json` | `scripts/offline_matrix.py` | 164M tokenizer / CPU | as above; Flask corpus | `01687c6` |
| `baseline_embed_stone_kgw_sweet_ewd.json`, `baseline_embed_unigram_unbiased_dip_synthid_pf.json` | `scripts/baseline_embed_check.py` | 1.3B / GPU fp16 | 15 generations per scheme, 5 prompts | – |
| `gpu_battery_results.json` | `run_full_battery.py` | 1.3B / GPU fp16 | 7 schemes, 15 runs, 30 operations | `01687c6` |
| `ci_order_results.json` | `scripts/mine_ci_order.py` | – | 20 repositories, 281 job sequences | – |

`multischeme_results.json` and `human_ops_results.json` were produced when the battery contained 16 and 22 operations; those operation sets are subsets of the current 30.

**Schemas.**

- Battery files: `{model, prompt, schemes: {<scheme>: {runs: [{run_index, generated_code?, generated_chars, baseline: {score, is_watermarked}, operations: [{mutation, layer, outcome, score}], excluded?}], summary: {n_runs, n_excluded_baseline_never_emitted, n_scored_runs, per_operation}}}}`
- Lifecycle files: `{model, steps, schemes: {<scheme>: {runs: [{run_index, prompt_id?, chain: [{step, score, is_watermarked, outcome?, chars?, code?}], chain_patch?, excluded?}]}}}`; `chain[0]` is the baseline.
- Offline matrix: `{scheme, n_baselines, draws, summary: {"<chain>|<order>": {n_baselines, never_broke, never_broke_ci, end_retained, end_retained_ci, end_z}}, cells: {"<chain>|<order>": [{baseline_index, chars, baseline_z, never_broke, end_retained, first_breaks, end_z, step_z}]}}`

---

## Setup

Requirements: Python 3.13 (results produced with 3.13.5), `git` on `PATH`, network access to Hugging Face on first model load. GPU runs used an NVIDIA GPU with CUDA 12.4. Disk: about 0.6 GB for the 164M model and 3 GB for the 1.3B model.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# GPU runs only:
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
```

**Host repository.** Operations run inside a checkout of `lutris/lutris` and use its `ruff.toml`. Check out the commit listed for the result being reproduced (both commits have the same `ruff.toml`):

```bash
git clone https://github.com/lutris/lutris
git -C lutris checkout 01687c6e73e284f634ff33e9edf2f38b6e76bda3   # or 8d882da59c68c8ff7f8eff43b2772c493ddcc088
```

**Environment variables.**

| Variable | Default | Effect |
|---|---|---|
| `WM_MODEL` | `bigcode/tiny_starcoder_py` | generation model |
| `WM_MODEL_REVISION` | `MODEL_REVISIONS[WM_MODEL]` | Hugging Face revision override |
| `WM_DEVICE` | `cpu` | `cuda` for GPU runs (fp16) |
| `WM_CORPUS` | `experiments/data/human_corpus.json` | human-edit corpus |

---

## Replicating the Results

Commands run from the repository root; `<lutris>` is the path of the host-repository checkout.

### Recompute reported numbers from committed results (no model, no network)

```bash
python -m unittest discover -s tests -t .
python experiments/scripts/paper_numbers.py
python experiments/scripts/verify_patch_ops.py
python experiments/scripts/analyze_lifecycle.py
```

`paper_numbers.py` prints every reported number per paper section, including per-condition and paired-difference bootstrap confidence intervals. `verify_patch_ops.py` prints `75/75 identical programs` for each of its four operations and exits non-zero on any mismatch.

### Single-operation battery (164M, CPU)

One invocation per family; outputs merge into the same file unless `--fresh` is given.

```bash
python experiments/run_full_battery.py --repo <lutris> --runs 10 --schemes stone,kgw,sweet,ewd \
  --out experiments/results/multischeme_results.json
python experiments/run_full_battery.py --repo <lutris> --runs 10 --schemes unigram,unbiased,dip,synthid,pf \
  --out experiments/results/multischeme_results.json
```

### Lifecycle (164M, CPU)

```bash
python experiments/run_lifecycle.py --repo <lutris> --schemes stone,kgw --runs 25 \
  --out experiments/results/lifecycle_results.json
python experiments/run_lifecycle.py --repo <lutris> --schemes sweet,ewd --runs 5 \
  --out experiments/results/lifecycle_results.json
python experiments/run_lifecycle.py --repo <lutris> --schemes unigram,unbiased,dip,synthid,pf --runs 5 \
  --out experiments/results/lifecycle_results.json

python experiments/run_lifecycle.py --repo <lutris> --schemes stone,kgw --runs 25 --hints both --multi-prompt \
  --out experiments/results/lifecycle_v2_results.json
```

### Controlled comparison and controls (tokenizer only)

```bash
python experiments/scripts/offline_matrix.py --repo <lutris> --scheme stone --draws 20
python experiments/scripts/offline_matrix.py --repo <lutris> --scheme kgw --draws 20
WM_CORPUS=experiments/data/human_corpus_flask.json \
  python experiments/scripts/offline_matrix.py --repo <lutris> --scheme stone --draws 20 \
  --out experiments/results/offline_matrix_flask_stone.json
WM_CORPUS=experiments/data/human_corpus_flask.json \
  python experiments/scripts/offline_matrix.py --repo <lutris> --scheme kgw --draws 20 \
  --out experiments/results/offline_matrix_flask_kgw.json

python experiments/scripts/unparse_control.py --repo <lutris> --scheme stone --draws 30 \
  --texts experiments/results/control_texts_stone.json --out experiments/results/unparse_control_stone.json
python experiments/scripts/unparse_control.py --repo <lutris> --scheme kgw --draws 30 \
  --texts experiments/results/control_texts_kgw.json --out experiments/results/unparse_control_kgw.json

python experiments/scripts/lifecycle_draw_variance.py --repo <lutris> --draws 60
python experiments/scripts/format_recovery_check.py <lutris>
```

### DeepSeek Coder 1.3B (GPU)

```bash
export WM_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct WM_DEVICE=cuda
python experiments/scripts/baseline_embed_check.py --schemes stone,kgw,sweet,ewd --n 15
python experiments/scripts/baseline_embed_check.py --schemes unigram,unbiased,dip,synthid,pf --n 15
python experiments/run_full_battery.py --repo <lutris> --runs 15 --schemes stone,kgw,sweet,ewd \
  --out experiments/results/gpu_battery_results.json --fresh
python experiments/run_full_battery.py --repo <lutris> --runs 15 --schemes unbiased,synthid,pf \
  --out experiments/results/gpu_battery_results.json
```

### Corpora

```bash
python experiments/scripts/mine_human_corpus.py <repo> --out <corpus.json>
```

---

## CI Mining

`scripts/mining/` derives operation classes from repository configuration and operation order from GitHub Actions workflows.

| Module | Function |
|---|---|
| `detectors.py` | operation-class signals: existence globs (dedicated config files) and content globs with regex patterns (generic files such as workflow YAML, `pyproject.toml`); per-class step keywords |
| `scan.py` | scans one repository; records the file that produced each match |
| `workflow_order.py` | parses `.github/workflows/*.yml`; classifies each job step by step keywords; emits one operation sequence per job |
| `catalogue.py` | aggregates scans into per-class repository prevalence with evidence files |
| `cli.py` | `python -m scripts.mining.cli <repo> [<repo> ...] --out <catalogue.json>` |

The lint/format order used in the lifecycle is reproduced with:

```bash
python experiments/scripts/mine_ci_order.py
```

It fetches only `.github/workflows` (sparse, blob-filtered, depth 1) from the 20 repositories in `experiments/data/ci_order_repos.json` at their pinned commits, extracts 281 job sequences, and counts ordered pairs of distinct operations within each job: `lint_autofix` precedes `format` 29 times and follows it 15 times.

---

## Determinism and Reproducibility

| Component | Mechanism |
|---|---|
| Python packages | exact versions in `requirements.txt`, including `ruff==0.16.8` and `python-minifier==3.3.0`, whose output feeds the detectors |
| Models | Hugging Face revisions pinned in `schemes.MODEL_REVISIONS` |
| Watermark code | vendored from recorded upstream sources (`vendor/VENDORED.md`) |
| Host repository | lutris commits listed per result file |
| Mutation draws | `random.Random(sha256(source) + SEED_SALT)`; `SEED_SALT=0` except in draw-variance and factorial runs, which vary it per draw |
| Corpora | committed in `experiments/data/` |
| CI-order mining | repositories pinned in `experiments/data/ci_order_repos.json` |
| Generation | sampled (`do_sample=True`) without a global seed; regenerated runs reproduce rates statistically. Every generated text used downstream is stored in the result files, so mutation and detection can be re-evaluated exactly. |
