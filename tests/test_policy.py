"""
Unit tests for CALM V2 Policy Engine (priority scoring, pressure levels & trends, hysteresis, burst).
"""

import unittest
from calm.policy.priority import PriorityEngine
from calm.policy.pressure import PressureEngine, PressureLevel, PressureTrend
from calm.policy.hysteresis import HysteresisController
from calm.policy.burst import BurstDetector
from calm.models.app_state import LifecycleState
from calm.models.telemetry import ItemTelemetry
from calm.models.prediction import PredictionResult, PredictionCandidate
from calm.utils.config import CALMConfig, PriorityWeights, PressureThresholds, HysteresisConfig


class TestPolicyComponents(unittest.TestCase):

    def setUp(self):
        self.apps = ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"]

    def test_priority_engine_foreground_dominant(self):
        engine = PriorityEngine(PriorityWeights())
        scores = engine.compute_scores(
            all_items=self.apps,
            foreground_item="Chrome",
            prediction_result=None,
            recency_scores={a: 0.1 for a in self.apps},
            frequency_scores={a: 0.1 for a in self.apps},
            burst_scores={a: 0.0 for a in self.apps},
        )
        self.assertGreater(scores["Chrome"], scores["YouTube"])
        self.assertGreater(scores["Chrome"], 0.25)

    def test_priority_engine_confidence_scaling(self):
        engine = PriorityEngine(PriorityWeights())
        # High confidence prediction
        pred_high = PredictionResult(
            source_item="Chrome",
            top_1="YouTube",
            top_k=[PredictionCandidate("YouTube", 0.9, 1)],
            confidence=0.95,
            entropy=0.1,
            probability_distribution={"YouTube": 0.9, "Spotify": 0.05, "Chrome": 0.05},
        )
        scores_high = engine.compute_scores(
            all_items=self.apps,
            foreground_item="Chrome",
            prediction_result=pred_high,
            recency_scores={a: 0.0 for a in self.apps},
            frequency_scores={a: 0.0 for a in self.apps},
            burst_scores={a: 0.0 for a in self.apps},
        )

        # Low confidence prediction
        pred_low = PredictionResult(
            source_item="Chrome",
            top_1="YouTube",
            top_k=[PredictionCandidate("YouTube", 0.3, 1)],
            confidence=0.10,
            entropy=2.0,
            probability_distribution={"YouTube": 0.3, "Spotify": 0.3, "Chrome": 0.4},
        )
        scores_low = engine.compute_scores(
            all_items=self.apps,
            foreground_item="Chrome",
            prediction_result=pred_low,
            recency_scores={a: 0.0 for a in self.apps},
            frequency_scores={a: 0.0 for a in self.apps},
            burst_scores={a: 0.0 for a in self.apps},
        )

        self.assertGreater(scores_high["YouTube"], scores_low["YouTube"])

    def test_pressure_engine_levels_and_trend(self):
        engine = PressureEngine(PressureThresholds(low=0.55, moderate=0.75, high=0.88, critical=0.95))
        
        # Test low pressure
        engine.update(used_ram_mb=1000, ram_limit_mb=3000)
        self.assertEqual(engine.level, PressureLevel.LOW)

        # Feed rising pressure
        engine.update(used_ram_mb=1500, ram_limit_mb=3000)
        engine.update(used_ram_mb=2000, ram_limit_mb=3000)
        engine.update(used_ram_mb=2700, ram_limit_mb=3000)
        
        self.assertEqual(engine.level, PressureLevel.HIGH)
        self.assertEqual(engine.trend, PressureTrend.RISING)
        self.assertTrue(engine.is_urgent)

    def test_hysteresis_controller(self):
        controller = HysteresisController(HysteresisConfig(min_state_ticks=3, demote_threshold=0.40))
        
        # Should NOT allow demotion if residency < min_state_ticks
        can_demote_early = controller.can_demote(
            item_id="YouTube",
            current_state=LifecycleState.CACHED,
            ticks_in_state=1,
            priority_score=0.20,
        )
        self.assertFalse(can_demote_early)

        # Should allow demotion if residency >= min_state_ticks and priority <= demote_threshold
        can_demote_ready = controller.can_demote(
            item_id="YouTube",
            current_state=LifecycleState.CACHED,
            ticks_in_state=4,
            priority_score=0.20,
        )
        self.assertTrue(can_demote_ready)

    def test_burst_detector(self):
        detector = BurstDetector(burst_threshold=0.35)
        t = ItemTelemetry("Spotify")
        t.record_access(10)
        t.record_access(12)  # fast gap
        t.record_access(13)  # fast gap
        
        burst_score = detector.evaluate_burst(t)
        self.assertGreaterEqual(burst_score, 0.35)
        self.assertTrue(detector.is_bursting(t))
        self.assertGreater(detector.get_protection_boost(t), 0.0)


if __name__ == "__main__":
    unittest.main()
