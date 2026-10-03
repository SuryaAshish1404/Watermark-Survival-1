# Vendored watermarking code

Two separate vendor trees, from two related but distinct upstream repos. They
are never imported in the same Python process (see `schemes.py`'s module
docstring) because both define top-level `watermark`/`utils`/`exceptions`/
`visualize` packages that would collide in `sys.modules`.

---

## `stone_watermarking/` — STONE, KGW, SWEET, EWD

Source: https://github.com/inistory/STONE-watermarking
Commit: `bb5d809c0c494a219411e861f2313cca2b9fd7b4` (2026-03-27)
License: Apache License 2.0 (per each file's header, retained unmodified)

Only the files needed to instantiate `STONE` and call
`generate_watermarked_text` / `detect_watermark` directly are vendored —
not the full repo (which includes a bigcode-evaluation-harness submodule,
training scripts, and CodeIP, none of which this benchmark uses). Files are
byte-for-byte copies, not reimplementations, so the scheme under test is
STONE as released — no reimplementation risk.

Files:
- `watermark/stone/stone.py`, `watermark/stone/__init__.py`
- `watermark/base.py`
- `utils/transformers_config.py`, `utils/utils.py`
- `exceptions/exceptions.py`
- `visualize/data_for_visualization.py`

`__init__.py` files for `watermark/`, `utils/`, `exceptions/`, `visualize/`
were added (empty) by us to make these proper packages for import — STONE's
own repo relies on implicit namespace packages plus a `run.py` that adds
`stone_implementation/` to `sys.path`; we reproduce the same import
structure standalone instead of vendoring their run.py driver.

Also includes `watermark/kgw/kgw.py`, `watermark/sweet/sweet.py`,
`watermark/ewd/ewd.py` (each with their `__init__.py`) — same repo, same
commit, same license, used as additional schemes.

---

## `markllm/` — Unigram, UnbiasedWatermark, DIP, SynthID, PF

Source: https://github.com/THU-BPM/MarkLLM (the upstream library the STONE
repo above forked its structure from — same author lineage, same API shape,
many more schemes). Commit: HEAD at fetch time, 2026-09-21 (MarkLLM does not
pin a specific commit hash in its releases the way STONE does; fetched via
the GitHub Contents API, file-by-file, byte-for-byte).
License: Apache License 2.0 (per each file's header, retained unmodified).

Files: `watermark/base.py`, `utils/{transformers_config.py,utils.py}`,
`exceptions/exceptions.py`, `visualize/data_for_visualization.py`, and five
scheme directories (`watermark/{unigram,unbiased,dip,synthid,pf}/`), plus
their default config JSON files (`config/*.json`) — MarkLLM's newer
`BaseConfig` loads scheme parameters from a JSON file path rather than plain
kwargs (STONE's fork simplified this away); we pass the vendored default
config path and override only what's documented in `schemes.py`.

**One disclosed, narrow modification** (not a byte-for-byte copy):
`watermark/synthid/detector.py`'s module-level
`from evaluation.dataset import C4Dataset` was moved to a lazy import inside
the one method that uses it (`get_data_for_training`, part of the
`BayesianDetector` training path this project never calls — we use
`detector_type: "mean"`, i.e. `MeanDetector`, which never touches that code).
Vendoring the full `evaluation` package to satisfy an otherwise-unused
top-level import wasn't worth the added surface. No other line in that file,
or any other vendored file, is modified. See the inline comment at the
change site for the same explanation.

**Also vendored but not used**: `watermark/exp_gumbel/exp_gumbel.py` and its
`config/EXPGumbel.json`. Kept in the tree rather than deleted, as
documentation of a real finding: `EXPGumbelUtils.__init__` allocates a
`(vocab_size * prefix_length) x vocab_size` lookup table, which for
`tiny_starcoder_py`'s ~49k-token vocabulary requires ~19 GB — it fails with a
`RuntimeError`, not a configuration mistake. See
`schemes.py`'s module docstring for the full reasoning. Excluded from `SCHEME_KWARGS`/`MARKLLM_CLASS_NAMES` in `schemes.py`
so it can't be accidentally selected.
