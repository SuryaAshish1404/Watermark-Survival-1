# Vendored Watermark Code

Upstream watermark implementations used by *An Empirical Study of Code Watermark Persistence Under Software Engineering Transformations*. The two trees define packages with identical top-level names (`watermark`, `utils`, `exceptions`, `visualize`) and are never imported in the same process; `schemes.assert_single_family` enforces this.

| Directory | Schemes | Source | Revision | License |
|---|---|---|---|---|
| `stone_watermarking/` | STONE, KGW, SWEET, EWD | https://github.com/inistory/STONE-watermarking | `bb5d809c0c494a219411e861f2313cca2b9fd7b4` (2026-03-27) | Apache-2.0 (file headers retained) |
| `markllm/` | Unigram, Unbiased, DIP, SynthID, PF | https://github.com/THU-BPM/MarkLLM | default branch, fetched 2026-09-21 via the GitHub Contents API | Apache-2.0 (file headers retained) |

---

## `stone_watermarking/`

Byte-for-byte copies of the files required to construct each scheme and call `generate_watermarked_text` / `detect_watermark`:

- `watermark/base.py`
- `watermark/{stone,kgw,sweet,ewd}/` (scheme module and `__init__.py`)
- `utils/transformers_config.py`, `utils/utils.py`
- `exceptions/exceptions.py`
- `visualize/data_for_visualization.py`

Not vendored: the evaluation-harness submodule, training scripts, CodeIP, and the upstream `run.py` driver.

**Additions.** Empty `__init__.py` files in `watermark/`, `utils/`, `exceptions/`, `visualize/`. Upstream relies on implicit namespace packages and a `run.py` that prepends its source directory to `sys.path`; the added files give the same import structure without the driver.

---

## `markllm/`

Byte-for-byte copies of:

- `watermark/base.py`
- `watermark/{unigram,unbiased,dip,synthid,pf}/`
- `utils/transformers_config.py`, `utils/utils.py`
- `exceptions/exceptions.py`
- `visualize/data_for_visualization.py`
- `config/{Unigram,Unbiased,DIP,SynthID,PF}.json`

MarkLLM's `BaseConfig` reads scheme parameters from a JSON file. `schemes.py` passes the vendored default config path and applies only the overrides listed in its `SCHEME_KWARGS`.

**Modification.** In `watermark/synthid/detector.py`, the module-level `from evaluation.dataset import C4Dataset` is moved into `get_data_for_training`, the only method that uses it. That method belongs to the `BayesianDetector` training path; this package uses `detector_type: "mean"` (`MeanDetector`), which does not call it. The change site carries an inline comment. No other vendored line is modified.

**Present but not selectable.** `watermark/exp_gumbel/` and `config/EXPGumbel.json` are vendored but excluded from `SCHEME_KWARGS` and `MARKLLM_CLASS_NAMES` in `schemes.py`. `EXPGumbelUtils.__init__` allocates a `(vocab_size × prefix_length) × vocab_size` table, which exceeds available memory for the generation models' vocabularies; see the `schemes.py` module docstring.
