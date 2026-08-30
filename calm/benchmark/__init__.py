"""
calm.benchmark — Comprehensive benchmarking suite, 7 baselines, rigorous metrics, and statistical runners.
"""

from calm.benchmark.baselines import (
    BaseStrategy,
    RandomStrategy,
    LRUStrategy,
    LFUStrategy,
    ReactivePressureStrategy,
    PredictiveOnlyStrategy,
    PressureOnlyStrategy,
    CALMStrategy,
    create_strategy,
    STRATEGY_NAMES,
)
from calm.benchmark.metrics import BenchmarkMetricsCalculator, RunResultMetrics
from calm.benchmark.runner import BenchmarkRunner
from calm.benchmark.report import BenchmarkReporter

__all__ = [
    "BaseStrategy",
    "RandomStrategy",
    "LRUStrategy",
    "LFUStrategy",
    "ReactivePressureStrategy",
    "PredictiveOnlyStrategy",
    "PressureOnlyStrategy",
    "CALMStrategy",
    "create_strategy",
    "STRATEGY_NAMES",
    "BenchmarkMetricsCalculator",
    "RunResultMetrics",
    "BenchmarkRunner",
    "BenchmarkReporter",
]
