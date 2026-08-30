"""
Unit tests for CALM V2 Lifecycle Engine (state transitions, budget enforcement, latency costs).
"""

import unittest
from calm.lifecycle.manager import LifecycleManager
from calm.models.app_state import LifecycleState
from calm.models.prediction import PredictionResult, PredictionCandidate
from calm.utils.config import CALMConfig, DEFAULT_APPS


class TestLifecycleManager(unittest.TestCase):

    def setUp(self):
        self.config = CALMConfig(ram_limit_mb=2500)
        self.manager = LifecycleManager(self.config, DEFAULT_APPS)

    def test_initial_state_is_archived(self):
        for app in DEFAULT_APPS:
            self.assertEqual(self.manager.states[app], LifecycleState.ARCHIVED)
        self.assertEqual(self.manager.total_ram(), 0)

    def test_step_foreground_activation(self):
        res = self.manager.step(requested_item="Chrome")
        self.assertEqual(res["requested_item"], "Chrome")
        self.assertEqual(res["pre_launch_state"], LifecycleState.ARCHIVED)
        self.assertFalse(res["is_cache_hit"])  # Cold launch initially
        self.assertEqual(self.manager.states["Chrome"], LifecycleState.ACTIVE)
        self.assertGreater(self.manager.total_ram(), 0)

    def test_hit_rate_on_subsequent_access(self):
        # First access: cold launch
        res1 = self.manager.step("Chrome")
        self.assertFalse(res1["is_cache_hit"])

        # Next access: Chrome should be ACTIVE or CACHED -> hit!
        res2 = self.manager.step("Chrome")
        self.assertTrue(res2["is_cache_hit"])
        self.assertLess(res2["launch_latency"], res1["launch_latency"])

    def test_predictive_prewarming(self):
        # Request Chrome with strong prediction for YouTube
        pred_res = PredictionResult(
            source_item="Chrome",
            top_1="YouTube",
            top_k=[PredictionCandidate("YouTube", 0.85, 1)],
            confidence=0.88,
            entropy=0.3,
            probability_distribution={"YouTube": 0.85, "Spotify": 0.05, "Chrome": 0.10},
        )
        self.manager.step("Chrome", prediction_result=pred_res)
        # YouTube should be prewarmed to CACHED or COMPRESSED
        self.assertIn(self.manager.states["YouTube"], (LifecycleState.CACHED, LifecycleState.COMPRESSED))

    def test_ram_budget_enforcement(self):
        # Launch multiple heavy apps
        for app in ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"]:
            self.manager.step(app)

        # Total RAM must strictly respect budget limit
        self.assertLessEqual(self.manager.total_ram(), self.config.ram_limit_mb)


if __name__ == "__main__":
    unittest.main()
