"""
Unit tests for standard baseline strategies ensuring benchmark fairness.
"""

import unittest
from calm.benchmark.baselines import (
    create_strategy,
    STRATEGY_NAMES,
    RandomStrategy,
    LRUStrategy,
    LFUStrategy,
    ReactivePressureStrategy,
    PredictiveOnlyStrategy,
    PressureOnlyStrategy,
    CALMStrategy,
)
from calm.utils.config import CALMConfig, DEFAULT_APPS
from calm.models.app_state import LifecycleState


class TestBaselinesFairness(unittest.TestCase):

    def setUp(self):
        self.config = CALMConfig(ram_limit_mb=2500)
        self.apps = DEFAULT_APPS

    def test_all_strategies_instantiable(self):
        for name in STRATEGY_NAMES:
            strat = create_strategy(name, self.config, self.apps, seed=42)
            self.assertIsNotNone(strat)
            # Initial states must all be ARCHIVED
            for app in self.apps:
                self.assertEqual(strat.states[app], LifecycleState.ARCHIVED)

    def test_pre_launch_state_fairness(self):
        # On first access, all strategies must report pre_launch_state as ARCHIVED and is_cache_hit as False
        for name in STRATEGY_NAMES:
            strat = create_strategy(name, self.config, self.apps, seed=42)
            res = strat.step("Chrome")
            self.assertEqual(res["pre_launch_state"], LifecycleState.ARCHIVED, f"Strategy {name} violated initial state check")
            self.assertFalse(res["is_cache_hit"], f"Strategy {name} falsely reported hit on cold launch")

    def test_ram_budget_respect(self):
        # Under multiple heavy accesses, all strategies must keep RAM <= budget
        sequence = ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"] * 3
        for name in STRATEGY_NAMES:
            strat = create_strategy(name, self.config, self.apps, seed=42)
            for app in sequence:
                strat.step(app)
            self.assertLessEqual(strat.total_ram(), self.config.ram_limit_mb, f"Strategy {name} violated RAM budget")


if __name__ == "__main__":
    unittest.main()
