import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.recovery.signature import check_presence
from tests.gitfixture import GitFixture, run

GPG_BATCH_KEY = """
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: Fixture Signer
Name-Email: fixture-signer@example.test
Expire-Date: 0
%commit
"""


def _gpg_available() -> bool:
    return shutil.which("gpg") is not None


def _make_gnupg_home() -> Path | None:
    """Generate a throwaway signing key in an isolated GNUPGHOME. Returns None if
    key generation isn't feasible in this environment (no gpg, generation times out,
    or — as observed on Windows/Git-Bash — gpg mis-resolves the mixed MSYS/native
    temp path and can't reach its own agent) so the test can skip cleanly rather
    than hang CI. Known-good on Linux; re-verify there before trusting this check
    against real sampled repos."""
    if not _gpg_available():
        return None
    home = Path(tempfile.mkdtemp())
    home.chmod(0o700)
    env = os.environ.copy()
    env["GNUPGHOME"] = str(home)
    try:
        subprocess.run(
            ["gpg", "--batch", "--gen-key"],
            input=GPG_BATCH_KEY,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None
    return home


@unittest.skipUnless(_gpg_available(), "gpg not installed")
class TestSignaturePresence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gnupg_home = _make_gnupg_home()
        if cls.gnupg_home is None:
            raise unittest.SkipTest("could not generate a throwaway GPG key in this environment")
        env = os.environ.copy()
        env["GNUPGHOME"] = str(cls.gnupg_home)
        env_list = subprocess.run(
            ["gpg", "--list-secret-keys", "--with-colons"],
            capture_output=True,
            text=True,
            env=env,
        ).stdout
        cls.key_id = next(
            line.split(":")[4] for line in env_list.splitlines() if line.startswith("sec")
        )

    @classmethod
    def tearDownClass(cls):
        if cls.gnupg_home:
            shutil.rmtree(cls.gnupg_home, ignore_errors=True)

    def setUp(self):
        self._old_gnupghome = os.environ.get("GNUPGHOME")
        os.environ["GNUPGHOME"] = str(self.gnupg_home)

    def tearDown(self):
        if self._old_gnupghome is None:
            os.environ.pop("GNUPGHOME", None)
        else:
            os.environ["GNUPGHOME"] = self._old_gnupghome

    def test_unsigned_commit_not_present(self):
        with GitFixture() as repo:
            repo.commit("unsigned")
            result = check_presence(repo.path, "HEAD")
            self.assertFalse(result.present)

    def test_signed_commit_present(self):
        with GitFixture() as repo:
            run(repo.path, "config", "user.signingkey", self.key_id)
            run(repo.path, "config", "commit.gpgsign", "true")
            (repo.path / "file.txt").write_text("x")
            run(repo.path, "add", "file.txt")
            run(repo.path, "commit", "-m", "signed commit")
            result = check_presence(repo.path, "HEAD")
            self.assertTrue(result.present)


if __name__ == "__main__":
    unittest.main()
