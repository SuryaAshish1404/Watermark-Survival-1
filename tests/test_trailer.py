import unittest

from scripts.recovery.trailer import check_presence, find_trailer_commits
from tests.gitfixture import GitFixture


class TestTrailerPresence(unittest.TestCase):
    def test_no_trailer_anywhere(self):
        with GitFixture() as repo:
            repo.commit("plain commit, no trailer")
            result = check_presence(repo.path, "HEAD")
            self.assertFalse(result.present)
            self.assertIsNone(result.origin)

    def test_trailer_present(self):
        with GitFixture() as repo:
            repo.commit("fix bug\n\nCo-Authored-By: agent-x <agent-x@example.test>")
            result = check_presence(repo.path, "HEAD")
            self.assertTrue(result.present)
            self.assertIn("agent-x", result.origin)

    def test_trailer_reachable_from_earlier_commit_still_found(self):
        with GitFixture() as repo:
            repo.commit("first, has trailer\n\nAssisted-By: model-y", filename="a.txt")
            repo.commit("second, no trailer", filename="b.txt")
            hits = find_trailer_commits(repo.path, "HEAD")
            self.assertEqual(len(hits), 1)
            self.assertIn("model-y", hits[0][1])

    def test_case_insensitive_key(self):
        with GitFixture() as repo:
            repo.commit("lowercase key\n\nco-authored-by: agent-z <a@example.test>")
            result = check_presence(repo.path, "HEAD")
            self.assertTrue(result.present)


if __name__ == "__main__":
    unittest.main()
