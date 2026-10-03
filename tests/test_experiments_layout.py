"""Guards the replication package layout: the files the experiment scripts read
by default exist where the scripts look for them, and every model that produced
a committed result has a pinned revision. Cheap (no torch/model load)."""

import json
import sys
import unittest
from pathlib import Path

EXPERIMENTS = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXPERIMENTS))

import schemes  # noqa: E402

RESULTS = EXPERIMENTS / "results"
DATA = EXPERIMENTS / "data"

# Files read by default (not just written) by scripts under experiments/.
DEFAULT_INPUTS = [
    RESULTS / "full_battery_results.json",   # verify_patch_ops, unparse_control, lifecycle_draw_variance
    RESULTS / "lifecycle_results.json",      # analyze_lifecycle
    RESULTS / "lifecycle_v2_results.json",   # offline_matrix, format_recovery_check
    DATA / "human_corpus.json",              # human_mutations, more_operations
]


class TestExperimentsLayout(unittest.TestCase):
    def test_default_inputs_exist(self):
        for path in DEFAULT_INPUTS:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"missing {path}")

    def test_corpora_have_expected_keys(self):
        keys = {"source", "identifiers", "comments", "except_types",
                "docstring_openers", "param_annotations", "return_annotations"}
        for path in DATA.glob("human_corpus*.json"):
            with self.subTest(path=path.name):
                self.assertTrue(keys <= set(json.loads(path.read_text(encoding="utf-8"))))

    def test_every_result_model_is_pinned(self):
        models = set()
        for path in RESULTS.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "model" in data:
                models.add(data["model"])
        self.assertTrue(models)
        self.assertEqual(models - set(schemes.MODEL_REVISIONS), set())

    def test_no_result_files_left_beside_code(self):
        self.assertEqual(sorted(p.name for p in EXPERIMENTS.glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
