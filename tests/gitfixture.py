"""Minimal git repo builder for recovery-check fixtures.

Builds fixtures with known before/after states (docs/03-before-state.md), used to
confirm the recovery checks classify every case correctly.
"""

import subprocess
import tempfile
from pathlib import Path


def run(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


class GitFixture:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        run(self.path.parent, "init", str(self.path))
        run(self.path, "config", "user.email", "fixture@example.test")
        run(self.path, "config", "user.name", "Fixture")
        run(self.path, "config", "commit.gpgsign", "false")

    def commit(self, message: str, filename: str = "file.txt", content: str = "x") -> str:
        (self.path / filename).write_text(content)
        run(self.path, "add", filename)
        run(self.path, "commit", "-m", message)
        return run(self.path, "rev-parse", "HEAD").stdout.strip()

    def cleanup(self):
        self._tmp.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cleanup()
