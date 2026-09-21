# Vendored: STONE watermarking (subset)

Source: https://github.com/inistory/STONE-watermarking
Commit: `bb5d809c0c494a219411e861f2313cca2b9fd7b4` (2026-03-27)
License: Apache License 2.0 (per each file's header, retained unmodified)

Only the files needed to instantiate `STONE` and call
`generate_watermarked_text` / `detect_watermark` directly are vendored —
not the full repo (which includes a bigcode-evaluation-harness submodule,
training scripts, and CodeIP, none of which this pilot uses). Files are
byte-for-byte copies, not reimplementations, so the scheme under test is
STONE as released, per docs/06-scheme-selection.md's reproducibility
requirement — no reimplementation risk.

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
