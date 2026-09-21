"""Scheme registry for the mutation-survival battery.

Four schemes, same vendored repo family (github.com/inistory/STONE-watermarking,
commit bb5d809), same API shape (generate_watermarked_text / detect_watermark),
same base model — so the only thing that varies is how each scheme picks which
tokens to bias, or how it weighs them at detection time:

- **STONE**: syntax-aware — biases only non-syntax tokens (its actual contribution).
- **KGW** (Kirchenbauer et al. 2023, vendored as the library's baseline): biases
  every token, no code-awareness at all — the non-code-aware ancestor STONE and
  the literature sheet's "base paper" both build on.
- **SWEET**: entropy-*gated* — biases only tokens where the model's own next-token
  distribution is high-entropy (a hard on/off cutoff). Needs the model at
  *detection* time too (recomputes entropy), unlike STONE/KGW.
- **EWD**: KGW's full-token bias, but at detection time each token's contribution
  to the z-score is *weighted* by its entropy rather than gated on/off — a soft
  version of SWEET's idea. Also needs the model at detection time. Tests whether
  SWEET's near-total embedding failure on this small model (docs/RESULTS.md) is a
  property of entropy-based selection in general, or specifically of SWEET's hard
  gate.

Comparing all four under the identical mutation battery tests whether STONE's
selection rule matters for robustness, or whether any selective/full green-list
scheme behaves the same under mutation — that's the point of including them.
"""

import sys
from pathlib import Path

VENDOR_ROOT = Path(__file__).parent / "vendor" / "stone_watermarking"
sys.path.insert(0, str(VENDOR_ROOT))

from utils.transformers_config import TransformersConfig  # noqa: E402
from watermark.stone.stone import STONE  # noqa: E402
from watermark.kgw.kgw import KGW  # noqa: E402
from watermark.sweet.sweet import SWEET  # noqa: E402
from watermark.ewd.ewd import EWD  # noqa: E402

MODEL_NAME = "bigcode/tiny_starcoder_py"

SCHEME_KWARGS = {
    "stone": dict(
        gamma=0.5,
        delta=4.0,
        hash_key=15485863,
        prefix_length=1,
        z_threshold=4.0,
        language="python",
        skipping_rule="all_pl",
        watermark_on_pl="False",
    ),
    "kgw": dict(
        gamma=0.5,
        delta=4.0,
        hash_key=15485863,
        prefix_length=1,
        z_threshold=4.0,
        f_scheme="time",
        window_scheme="left",
    ),
    "sweet": dict(
        gamma=0.5,
        delta=4.0,
        hash_key=15485863,
        prefix_length=1,
        z_threshold=4.0,
        entropy_threshold=0.9,
    ),
    "ewd": dict(
        gamma=0.5,
        delta=4.0,
        hash_key=15485863,
        prefix_length=1,
        z_threshold=4.0,
    ),
}

SCHEME_CLASSES = {"stone": STONE, "kgw": KGW, "sweet": SWEET, "ewd": EWD}


def build_transformers_config(model, tokenizer):
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
    transformers_config = build_transformers_config(model, tokenizer)
    return SCHEME_CLASSES[name](transformers_config, **SCHEME_KWARGS[name])
