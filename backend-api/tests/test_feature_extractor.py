import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Historical regression only. The serving process never imports this extractor.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "archive/legacy-backend"))

from feature_extractor import FEATURE_NAMES, extract_features


class FeatureExtractorTests(unittest.TestCase):
    def test_exact_paper_feature_inventory(self):
        self.assertEqual(len(FEATURE_NAMES), 7)
        self.assertEqual(FEATURE_NAMES[0], "code_switching_ratio")
        self.assertEqual(FEATURE_NAMES[-1], "urgency_cue_frequency")

    def test_empty_denominators_return_zero(self):
        np.testing.assert_array_equal(extract_features(""), np.zeros(7))

    def test_surface_signals_are_measured_as_ratios(self):
        values = extract_features("TAKOT!!! share agad na this soooo")
        self.assertEqual(values.shape, (7,))
        self.assertTrue(np.all(values >= 0))
        self.assertGreater(values[0], 0)  # Filipino and English both occur.
        self.assertGreater(values[1], 0)
        self.assertGreater(values[2], 0)
        self.assertGreater(values[3], 0)
        self.assertGreater(values[4], 0)
        self.assertGreater(values[5], 0)
        self.assertGreater(values[6], 0)


if __name__ == "__main__":
    unittest.main()
