"""Scheme registry for the mutation-survival battery.

Nine schemes across two vendored repo families. Both families expose the same
runtime API (`generate_watermarked_text` / `detect_watermark`), but their
*internal* package layout collides — both define top-level `watermark`,
`utils`, `exceptions`, `visualize` packages — so importing both families in one
Python process causes a `sys.modules` collision (the second family's `watermark`
package silently resolves to the first family's cached one). Since every
invocation of this battery already runs one scheme per process (a memory-safety
fix from an earlier session — see PROGRESS.md), this module enforces
single-family-per-process at import time instead of trying to support mixing,
which would be a real correctness bug hiding behind an import that "succeeds."

## Family 1 — `vendor/stone_watermarking/` (github.com/inistory/STONE-watermarking,
commit bb5d809). Plain-kwargs config, no external config file needed.

- **STONE**: syntax-aware — biases only non-syntax tokens (its actual contribution).
- **KGW** (Kirchenbauer et al. 2023): biases every token, no code-awareness.
- **SWEET**: entropy-*gated* — biases only high-entropy tokens (hard cutoff).
  Needs the model at detection time (recomputes entropy).
- **EWD**: KGW's full-token bias, but detection *weights* each token's
  contribution by entropy — SWEET's idea, made soft instead of hard. Also
  needs the model at detection time.

## Family 2 — `vendor/markllm/` (github.com/THU-BPM/MarkLLM, the upstream
library Family 1 forked its structure from — same API, many more schemes).
JSON-config-file based (`BaseConfig(algorithm_config_path, transformers_config,
**kwargs)`), kwargs override the file's defaults.

- **Unigram** (Zhao et al. 2023): a *static* green list — the same list at
  every position, not re-derived from the previous token. Tests whether a
  fixed vs. hash-chained green list changes mutation sensitivity.
- **Unbiased** (Hu et al.): distortion-free — reweights the sampling
  distribution via a randomized strategy rather than an additive logit bias,
  so it doesn't skew the model's output distribution at all. Detection is a
  p-value (lower = more watermarked), not a z-score.
- **DIP**: another distortion-free family member, permutation-based, with
  its own history-context handling.
- **SynthID** (Google DeepMind's Gumbel-sampling-based scheme, as published):
  uses the same `MeanDetector` path as the public description of SynthID
  Text's "mean" scoring mode — no trained Bayesian detector involved (that
  variant needs a dataset dependency this project doesn't vendor; see
  `vendor/VENDORED.md`).
- **PF** (Permute-and-Flip sampler): another distortion-free construction,
  different sampling procedure again, hash-table-seeded rather than
  logit-biased.

**Not included, investigated and rejected on concrete grounds** (see
`BENCHMARK.md` §1.1 for the full writeup):
- **SrcMarker**: no released checkpoint (needs training from scratch); no
  Python grammar support (Java/C++/JS only).
- **CodeIP**: a fundamentally different multi-bit message-encoding detection
  paradigm, not the green-list interface every other scheme here shares.
- **EXPGumbel**: its reference implementation builds a
  `(vocab_size * prefix_length) x vocab_size` lookup table at initialization —
  for `tiny_starcoder_py`'s ~49k-token vocabulary this is a ~19 GB allocation,
  confirmed by a direct `RuntimeError` on this host. A real scalability
  property of this implementation for large-vocabulary code models, not a
  vendoring bug — would need a different model or a smarter (non-table-based)
  implementation of the same algorithm to include fairly.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent / "vendor"
STONE_FAMILY_ROOT = _ROOT / "stone_watermarking"
MARKLLM_FAMILY_ROOT = _ROOT / "markllm"

MODEL_NAME = "bigcode/tiny_starcoder_py"

STONE_FAMILY = {"stone", "kgw", "sweet", "ewd"}
MARKLLM_FAMILY = {"unigram", "unbiased", "dip", "synthid", "pf"}

SCHEME_KWARGS = {
    # --- Family 1: plain kwargs, no config file ---
    "stone": dict(
        gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0,
        language="python", skipping_rule="all_pl", watermark_on_pl="False",
    ),
    "kgw": dict(
        gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0,
        f_scheme="time", window_scheme="left",
    ),
    "sweet": dict(
        gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0,
        entropy_threshold=0.9,
    ),
    "ewd": dict(
        gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0,
    ),
    # --- Family 2: kwargs override each scheme's own published default config
    # (config/<Name>.json, vendored unmodified) rather than being forced onto
    # Family 1's gamma/delta/z_threshold convention, which doesn't apply to
    # these distortion-free constructions (Unbiased/DIP/PF use p-values or
    # scheme-specific statistics, not a shared z-score scale).
    "unigram": dict(delta=4.0, z_threshold=4.0),  # override toward Family 1's delta for the one scheme that shares the mechanism
    "unbiased": dict(),
    "dip": dict(),
    "synthid": dict(),
    "pf": dict(),
}

MARKLLM_CONFIG_FILES = {
    "unigram": "Unigram.json",
    "unbiased": "Unbiased.json",
    "dip": "DIP.json",
    "synthid": "SynthID.json",
    "pf": "PF.json",
}

MARKLLM_CLASS_NAMES = {
    "unigram": ("watermark.unigram.unigram", "Unigram"),
    "unbiased": ("watermark.unbiased.unbiased", "UnbiasedWatermark"),
    "dip": ("watermark.dip.dip", "DIP"),
    "synthid": ("watermark.synthid.synthid", "SynthID"),
    "pf": ("watermark.pf.pf", "PF"),
}


def _family_of(name: str) -> str:
    if name in STONE_FAMILY:
        return "stone_family"
    if name in MARKLLM_FAMILY:
        return "markllm_family"
    raise ValueError(f"Unknown scheme: {name}")


def assert_single_family(scheme_names: list[str]) -> str:
    """Raises if the requested schemes span both vendor families — see module
    docstring for why mixing them in one process is unsafe, not just slow."""
    families = {_family_of(n) for n in scheme_names}
    if len(families) > 1:
        raise ValueError(
            f"Cannot run schemes from both vendor families in one process: {scheme_names} "
            f"span {families}. Run each family as a separate invocation "
            f"(they can still merge into the same --out file — see run_full_battery.py --fresh)."
        )
    return families.pop()


def build_transformers_config(TransformersConfig, model, tokenizer):
    return TransformersConfig(
        model=model,
        tokenizer=tokenizer,
        vocab_size=len(tokenizer),
        device="cpu",
        max_new_tokens=160,
        do_sample=True,
        top_k=50,
        temperature=0.7,
        num_beams=1,
    )


def build_scheme(name: str, model, tokenizer):
    family = _family_of(name)

    if family == "stone_family":
        root = str(STONE_FAMILY_ROOT)
        if root not in sys.path:
            sys.path.insert(0, root)
        from utils.transformers_config import TransformersConfig  # noqa: E402

        classes = {
            "stone": lambda: __import__("watermark.stone.stone", fromlist=["STONE"]).STONE,
            "kgw": lambda: __import__("watermark.kgw.kgw", fromlist=["KGW"]).KGW,
            "sweet": lambda: __import__("watermark.sweet.sweet", fromlist=["SWEET"]).SWEET,
            "ewd": lambda: __import__("watermark.ewd.ewd", fromlist=["EWD"]).EWD,
        }
        cls = classes[name]()
        tc = build_transformers_config(TransformersConfig, model, tokenizer)
        return cls(tc, **SCHEME_KWARGS[name])

    # markllm_family
    root = str(MARKLLM_FAMILY_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    from utils.transformers_config import TransformersConfig  # noqa: E402

    module_name, class_name = MARKLLM_CLASS_NAMES[name]
    module = __import__(module_name, fromlist=[class_name])
    cls = getattr(module, class_name)
    tc = build_transformers_config(TransformersConfig, model, tokenizer)
    config_path = str(MARKLLM_FAMILY_ROOT / "config" / MARKLLM_CONFIG_FILES[name])
    return cls(config_path, tc, **SCHEME_KWARGS[name])
