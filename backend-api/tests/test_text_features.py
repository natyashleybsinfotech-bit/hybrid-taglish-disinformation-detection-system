import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import text_features as features

class TextFeatureTests(unittest.TestCase):
    def test_seven_measurements_have_real_known_character_ratios_without_classifier(self):
        with patch.object(features.HybridPipeline,'__init__',side_effect=AssertionError('Classifier must remain unloaded')):
            rows=features.measure_text_features('AAA!!!')
        values={r['name']:r['value'] for r in rows}
        self.assertEqual(list(values),list(features.FEATURE_NAMES));self.assertEqual(len(values),7)
        self.assertEqual(values['capitalization_ratio'],1)
        self.assertEqual(values['repeated_character_ratio'],1)
        self.assertEqual(values['punctuation_intensity'],.5)
        self.assertEqual(values['filipino_particle_frequency'],0)
        self.assertTrue(all(0<=v<=1 for v in values.values()))

    def test_saved_particle_tokenization_and_prepared_text_denominators(self):
        values={r['name']:r['value'] for r in features.measure_text_features('na ba?')}
        self.assertAlmostEqual(values['filipino_particle_frequency'],2/3,places=6)
        self.assertAlmostEqual(values['punctuation_intensity'],1/6,places=6)
        self.assertEqual(features.measure_text_features('  na   ba? '),features.measure_text_features('na ba?'))
