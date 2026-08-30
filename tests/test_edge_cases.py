"""
Unit tests for edge cases and malformed inputs in CALM V2.
"""

import unittest
from calm.prediction.markov import MarkovPredictor
from calm.prediction.evaluation import PredictionEvaluator
from calm.lifecycle.manager import LifecycleManager
from calm.utils.config import CALMConfig, DEFAULT_APPS
from calm.models.app_state import LifecycleState
from calm.models.prediction import PredictionResult


class TestEdgeCases(unittest.TestCase):

    def test_empty_workload_prediction(self):
        predictor = MarkovPredictor()
        predictor.fit([], all_items=DEFAULT_APPS)
        probs = predictor.get_transition_probabilities("Chrome")
        self.assertEqual(len(probs), len(DEFAULT_APPS))
        self.assertAlmostEqual(sum(probs.values()), 1.0)

    def test_single_item_workload(self):
        predictor = MarkovPredictor()
        predictor.fit(["Chrome", "Chrome", "Chrome"], all_items=DEFAULT_APPS)
        pred = predictor.predict("Chrome")
        self.assertEqual(pred.top_1, "Chrome")
        self.assertGreater(pred.confidence, 0.0)

    def test_unknown_app_request(self):
        config = CALMConfig(ram_limit_mb=2500)
        manager = LifecycleManager(config, DEFAULT_APPS)
        # Should gracefully manage registered apps even if unknown app is queried in predictor
        pred = manager.policy_engine.priority_engine.compute_scores(
            all_items=DEFAULT_APPS,
            foreground_item="UnknownApp",
            prediction_result=None,
            recency_scores={a: 0.0 for a in DEFAULT_APPS},
            frequency_scores={a: 0.0 for a in DEFAULT_APPS},
            burst_scores={a: 0.0 for a in DEFAULT_APPS},
        )
        self.assertEqual(len(pred), len(DEFAULT_APPS))

    def test_zero_memory_budget(self):
        config = CALMConfig(ram_limit_mb=0)
        manager = LifecycleManager(config, DEFAULT_APPS)
        res = manager.step("Chrome")
        self.assertIsNotNone(res)

    def test_very_large_memory_budget(self):
        config = CALMConfig(ram_limit_mb=100000)
        manager = LifecycleManager(config, DEFAULT_APPS)
        for app in DEFAULT_APPS:
            manager.step(app)
        self.assertLessEqual(manager.total_ram(), 100000)

    def test_low_confidence_fallback(self):
        config = CALMConfig(ram_limit_mb=2500)
        manager = LifecycleManager(config, DEFAULT_APPS)
        pred_low = PredictionResult(
            source_item="Chrome",
            top_1="YouTube",
            confidence=0.05,
            entropy=2.3,
            probability_distribution={a: 0.20 for a in DEFAULT_APPS},
        )
        # With low confidence, YouTube should NOT be aggressively promoted
        manager.step("Chrome", prediction_result=pred_low)
        self.assertEqual(manager.states["YouTube"], LifecycleState.ARCHIVED)


if __name__ == "__main__":
    unittest.main()
