import unittest

from scripts.recovery.outcomes import Outcome, PresenceResult, classify, classify_spurious_only


class TestClassify(unittest.TestCase):
    def test_never_emitted(self):
        before = PresenceResult(present=False, origin=None)
        after = PresenceResult(present=False, origin=None)
        self.assertEqual(classify(before, after), Outcome.NEVER_EMITTED)

    def test_retained(self):
        before = PresenceResult(present=True, origin="agent-a")
        after = PresenceResult(present=True, origin="agent-a")
        self.assertEqual(classify(before, after), Outcome.RETAINED)

    def test_silently_lost(self):
        before = PresenceResult(present=True, origin="agent-a")
        after = PresenceResult(present=False, origin=None)
        self.assertEqual(classify(before, after), Outcome.SILENTLY_LOST)

    def test_lost_surfaced(self):
        before = PresenceResult(present=True, origin="agent-a")
        after = PresenceResult(present=False, origin=None, surfaced_failure=True)
        self.assertEqual(classify(before, after), Outcome.LOST_SURFACED)

    def test_spuriously_gained_against_ground_truth(self):
        before = PresenceResult(present=True, origin="human")
        after = PresenceResult(present=True, origin="model-x")
        self.assertEqual(
            classify(before, after, ground_truth_origin="human"), Outcome.SPURIOUSLY_GAINED
        )

    def test_origin_changed_without_ground_truth_is_lost(self):
        before = PresenceResult(present=True, origin="agent-a")
        after = PresenceResult(present=True, origin="agent-b")
        self.assertEqual(classify(before, after), Outcome.SILENTLY_LOST)


class TestClassifySpuriousOnly(unittest.TestCase):
    def test_module_never_had_carrier_gains_one(self):
        before = PresenceResult(present=False, origin=None)
        after = PresenceResult(present=True, origin="model-x")
        self.assertEqual(
            classify_spurious_only(before, after, actual_origin_is_human=True),
            Outcome.SPURIOUSLY_GAINED,
        )

    def test_out_of_scope_if_carrier_already_present_before(self):
        before = PresenceResult(present=True, origin="model-x")
        after = PresenceResult(present=True, origin="model-x")
        self.assertIsNone(
            classify_spurious_only(before, after, actual_origin_is_human=True)
        )

    def test_no_gain_no_result(self):
        before = PresenceResult(present=False, origin=None)
        after = PresenceResult(present=False, origin=None)
        self.assertIsNone(
            classify_spurious_only(before, after, actual_origin_is_human=True)
        )


if __name__ == "__main__":
    unittest.main()
