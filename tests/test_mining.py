import json
import tempfile
import unittest
from pathlib import Path

from scripts.mining.catalogue import build_catalogue
from scripts.mining.scan import scan_repo
from scripts.mining.workflow_order import extract_orders

RELEASE_WORKFLOW = """
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: npx eslint . --fix
      - name: Build
        run: npm run build
      - name: Bundle
        run: npx webpack --mode production
      - name: Publish to npm
        run: npm publish
"""


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestScanRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_detects_formatter_and_bundler_and_release(self):
        _write(self.root, ".prettierrc", '{"semi": true}')
        _write(self.root, "webpack.config.js", "module.exports = { mode: 'production' }")
        _write(self.root, ".github/workflows/release.yml", RELEASE_WORKFLOW)

        result = scan_repo(self.root)
        present = result.operations_present()

        self.assertIn("format", present)
        self.assertIn("bundle", present)
        self.assertIn("minify", present)  # mode: production matches MINIFY pattern
        self.assertIn("republish", present)  # npm publish
        self.assertIn("rebuild", present)  # "npm run build"
        self.assertIn("lint_autofix", present)  # eslint --fix

    def test_every_hit_cites_a_file(self):
        _write(self.root, ".prettierrc", '{"semi": true}')
        result = scan_repo(self.root)
        for ev in result.evidence:
            self.assertTrue((self.root / ev.file_path).is_file())

    def test_no_config_no_evidence(self):
        _write(self.root, "README.md", "just docs")
        result = scan_repo(self.root)
        self.assertEqual(result.operations_present(), set())


class TestWorkflowOrder(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_extracts_step_order(self):
        _write(self.root, ".github/workflows/release.yml", RELEASE_WORKFLOW)
        orders = extract_orders(self.root)
        self.assertEqual(len(orders), 1)
        order = orders[0]
        self.assertEqual(order.job_name, "release")
        # lint -> build -> bundle -> publish, in that order, as configured
        self.assertEqual(
            order.operation_sequence,
            ("lint_autofix", "rebuild", "bundle", "republish"),
        )


class TestCatalogue(unittest.TestCase):
    def test_prevalence_across_two_repos(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            a_path, b_path = Path(a), Path(b)
            _write(a_path, ".prettierrc", "{}")
            _write(a_path, ".github/workflows/release.yml", RELEASE_WORKFLOW)
            _write(b_path, ".github/workflows/release.yml", RELEASE_WORKFLOW)
            # repo b has no formatter config

            catalogue = build_catalogue([a_path, b_path])
            self.assertEqual(catalogue.total_repos_scanned, 2)

            by_id = {e.operation_id: e for e in catalogue.entries}
            self.assertEqual(by_id["format"].repo_count, 1)
            self.assertAlmostEqual(by_id["format"].repo_prevalence, 0.5)
            self.assertEqual(by_id["republish"].repo_count, 2)
            self.assertAlmostEqual(by_id["republish"].repo_prevalence, 1.0)

            # sorted descending by prevalence
            prevalences = [e.repo_prevalence for e in catalogue.entries]
            self.assertEqual(prevalences, sorted(prevalences, reverse=True))

            # every non-zero entry cites at least one file
            for entry in catalogue.entries:
                if entry.repo_count > 0:
                    self.assertTrue(entry.evidence_files)

            # JSON-serializable
            json.dumps(catalogue.to_dict())


if __name__ == "__main__":
    unittest.main()
