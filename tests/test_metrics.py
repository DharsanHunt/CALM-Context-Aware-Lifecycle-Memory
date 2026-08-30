"""
Unit tests for CALM V2 Benchmark Metrics Calculator.
"""

import unittest
from calm.benchmark.metrics import BenchmarkMetricsCalculator
from calm.models.app_state import LifecycleState


class TestBenchmarkMetrics(unittest.TestCase):

    def test_metrics_calculation(self):
        step_results = [
            {
                "requested_item": "Chrome",
                "pre_launch_state": LifecycleState.ARCHIVED,
                "is_cache_hit": False,
                "launch_latency": 2.40,
                "total_ram": 1200,
                "post_states": {"Chrome": LifecycleState.ACTIVE, "YouTube": LifecycleState.ARCHIVED},
                "reclaimed_mb": 0.0,
            },
            {
                "requested_item": "Chrome",
                "pre_launch_state": LifecycleState.ACTIVE,
                "is_cache_hit": True,
                "launch_latency": 0.05,
                "total_ram": 1200,
                "post_states": {"Chrome": LifecycleState.ACTIVE, "YouTube": LifecycleState.ARCHIVED},
                "reclaimed_mb": 0.0,
            },
        ]

        metrics = BenchmarkMetricsCalculator.calculate(
            strategy_name="CALM",
            workload_name="test_workload",
            seed=42,
            step_results=step_results,
            ram_limit_mb=2500,
        )

        self.assertEqual(metrics.cache_hit_rate_pct, 50.0)
        self.assertAlmostEqual(metrics.avg_launch_latency_sec, 1.225, places=2)
        self.assertEqual(metrics.peak_ram_mb, 1200.0)
        self.assertEqual(metrics.budget_violations_count, 0)


if __name__ == "__main__":
    unittest.main()
