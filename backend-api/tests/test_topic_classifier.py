import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config
from topic_classifier import suggest_topic


class TopicClassifierTests(unittest.TestCase):
    def test_routes_taglish_health_content(self):
        result = suggest_topic("Ayon sa doktor, kailangan ang bakuna para sa sakit na ito.")
        self.assertEqual(result.topic, "Health and Medicine")
        self.assertGreater(result.confidence, 0.5)

    def test_routes_politics_content(self):
        result = suggest_topic("COMELEC election update para sa mga kandidato at senador.")
        self.assertEqual(result.topic, "Politics, Governance, and Elections")

    def test_unknown_content_uses_other(self):
        result = suggest_topic("Isang pangkalahatang kuwento na walang tiyak na larangan.")
        self.assertEqual(result.topic, "Other and General")
        self.assertEqual(result.confidence, 0.35)

    def test_every_suggestion_uses_paper_taxonomy(self):
        for text in ("bagyo at baha", "student at teacher", "artista at pelikula", "inflation at sahod"):
            self.assertIn(suggest_topic(text).topic, config.TOPIC_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
