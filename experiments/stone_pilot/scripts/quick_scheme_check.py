"""One-shot baseline-embedding check for a single scheme, meant to be invoked as a
fresh subprocess per scheme so a CUDA-context-corrupting crash in one scheme can't
poison the next. Usage: python scripts/quick_scheme_check.py <scheme_name>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from schemes import DEVICE, MODEL_NAME, build_scheme

PROMPT = (
    '"""Utilities for locating a game\'s installed executable and save-data '
    'directory on disk."""\n'
    "import os\n\n\n"
    "def get_game_executable_path(game_id):\n"
    '    """Return the absolute path to the executable for the given game id, '
    'or None if not installed."""\n'
)

name = sys.argv[1]
dtype = torch.float16 if DEVICE.startswith("cuda") else torch.float32
tok = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(DEVICE)
model.eval()

try:
    sch = build_scheme(name, model, tok)
    gen = sch.generate_watermarked_text(PROMPT)
    det = sch.detect_watermark(gen)
    print(f"RESULT {name:10s} chars={len(gen):4d} detected={det.get('is_watermarked')} score={det.get('score')}")
except Exception as e:  # noqa: BLE001
    print(f"RESULT {name:10s} ERROR: {repr(e)[:300]}")
