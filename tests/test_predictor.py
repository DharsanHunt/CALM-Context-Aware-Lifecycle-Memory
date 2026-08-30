"""
Unit tests for CALM V2 Prediction Engine (Markov predictor, confidence, entropy, multi-step).
"""

import unittest
from calm.prediction.markov import MarkovPredictor
from calm.prediction.confidence import ConfidenceScorer
from calm.prediction.evaluation import PredictionEvaluator


class TestMarkovPredictor(unittest.TestCase):

    def setUp(self):
        self.apps = ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"]
        # Sequence with known transition structure: A -> B -> C -> A ...
        self.train_sequence = ["Chrome", "YouTube", "Spotify", "Chrome", "YouTube", "Spotify"] * 10
        self.predictor = MarkovPredictor(smoothing_alpha=0.01)
        self.predictor.fit(self.train_sequence, all_items=self.apps)

    def test_predictor_trained_flag(self):
        self.assertTrue(self.predictor.is_trained)

    def test_transition_probability_learned(self):
        probs_chrome = self.predictor.get_transition_probabilities("Chrome")
        # YouTube should be highest after Chrome
        self.assertGreater(probs_chrome["YouTube"], probs_chrome["Spotify"])
        self.assertGreater(probs_chrome["YouTube"], 0.70)

    def test_top_k_prediction(self):
        pred = self.predictor.predict("Chrome", top_k=3)
        self.assertEqual(pred.top_1, "YouTube")
        self.assertEqual(len(pred.top_k), 3)
        self.assertEqual(pred.top_k[0].item_id, "YouTube")
        self.assertGreater(pred.confidence, 0.50)

    def test_confidence_and_entropy(self):
        pred = self.predictor.predict("Chrome", top_k=3)
        self.assertGreaterEqual(pred.confidence, 0.0)
        self.assertLessEqual(pred.confidence, 1.0)
        self.assertGreaterEqual(pred.entropy, 0.0)

    def test_multi_step_prediction(self):
        paths = self.predictor.predict_multi_step("Chrome", steps=2, top_k_per_step=1)
        self.assertEqual(len(paths), 1)
        # Should project Chrome -> YouTube -> Spotify
        path = paths[0]
        self.assertEqual(path[0][0], "YouTube")
        self.assertEqual(path[1][0], "Spotify")

    def test_unseen_item_handling(self):
        # Predictor should gracefully return uniform distribution for an unknown item without crashing
        probs = self.predictor.get_transition_probabilities("UnknownApp")
        self.assertEqual(len(probs), len(self.apps))
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=3)

    def test_prediction_evaluator(self):
        test_seq = ["Chrome", "YouTube", "Spotify", "Chrome", "YouTube"]
        metrics = PredictionEvaluator.evaluate(self.predictor, test_seq, top_k=3)
        self.assertIn("top_1_accuracy", metrics)
        self.assertIn("top_3_accuracy", metrics)
        self.assertIn("brier_score", metrics)
        self.assertEqual(metrics["top_1_accuracy"], 100.0)


if __name__ == "__main__":
    unittest.main()
