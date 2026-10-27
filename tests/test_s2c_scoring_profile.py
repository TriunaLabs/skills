"""Scoring profiles must remain reproducible and cannot silently change shape."""

import copy
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_reader_views  # noqa: E402
import s2c_scoring_profile  # noqa: E402


class ScoringProfileTests(unittest.TestCase):
    def test_rejects_invalid_weights_and_nonfinite_parameters(self):
        baseline = s2c_scoring_profile.default_profile()
        invalid = copy.deepcopy(baseline)
        invalid["browser_weights"][next(iter(invalid["browser_weights"]))] += 1
        with self.assertRaises(ValueError):
            s2c_scoring_profile.validate(invalid)
        invalid = copy.deepcopy(baseline)
        invalid["retrieval"]["k1"] = float("nan")
        with self.assertRaises(ValueError):
            s2c_scoring_profile.validate(invalid)
        invalid = copy.deepcopy(baseline)
        invalid["crawler_weights"]["unknown"] = 1
        with self.assertRaises(ValueError):
            s2c_scoring_profile.validate(invalid)

    def test_tuned_bm25_is_traceable_and_changes_saved_passage_score(self):
        frame = {"nodes": [
            {"id": "h", "tag": "h1", "text": "Plans", "visible": True, "aria_hidden": False,
             "a11y_index": 1, "dom_index": 1, "landmark": "main"},
            {"id": "a", "tag": "p", "text": "Cost cost cost for a monthly plan.", "visible": True,
             "aria_hidden": False, "a11y_index": 2, "dom_index": 2, "landmark": "main"},
            {"id": "h2", "tag": "h2", "text": "Getting started", "visible": True,
             "aria_hidden": False, "a11y_index": 3, "dom_index": 3, "landmark": "main"},
            {"id": "b", "tag": "p", "text": "Create an account and review options.", "visible": True,
             "aria_hidden": False, "a11y_index": 4, "dom_index": 4, "landmark": "main"},
        ]}
        baseline = s2c_scoring_profile.default_profile()
        tuned = copy.deepcopy(baseline)
        tuned["retrieval"]["k1"] = 2.5
        original = s2c_reader_views.retrieval(frame, "What is the cost?", baseline["retrieval"])
        revised = s2c_reader_views.retrieval(frame, "What is the cost?", tuned["retrieval"])
        self.assertEqual(original["mode"], "bm25")
        self.assertNotEqual(original["chunks"][0]["score"], revised["chunks"][0]["score"])
        self.assertEqual(original["chunks"][1]["score"], 0)
        self.assertNotEqual(s2c_scoring_profile.fingerprint(baseline), s2c_scoring_profile.fingerprint(tuned))


if __name__ == "__main__":
    unittest.main()
