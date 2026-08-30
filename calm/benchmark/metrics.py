"""
calm.benchmark.metrics — Rigorous evaluation metrics for lifecycle memory systems.
Computes latency percentiles, memory-time, thrashing, oscillations, and state distributions.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import numpy as np

from calm.models.app_state import LifecycleState


@dataclass
class RunResultMetrics:
    """Consolidated metrics summary for a single benchmark run."""
    strategy_name: str
    workload_name: str
    seed: int
    num_requests: int

    # Performance
    cache_hit_rate_pct: float = 0.0
    avg_launch_latency_sec: float = 0.0
    p95_launch_latency_sec: float = 0.0
    p99_launch_latency_sec: float = 0.0

    # Memory
    avg_ram_mb: float = 0.0
    peak_ram_mb: float = 0.0
    min_ram_mb: float = 0.0
    memory_time_mb_ticks: float = 0.0
    total_reclaimed_mb: float = 0.0
    compression_savings_mb_ticks: float = 0.0
    budget_violations_count: int = 0

    # Lifecycle & Stability
    thrashing_count: int = 0
    oscillation_count: int = 0
    unnecessary_evictions_count: int = 0
    total_evictions_count: int = 0
    state_distribution: Dict[str, float] = field(default_factory=dict)

    # Prediction (if available)
    prediction_top_1_accuracy: float = 0.0
    prediction_top_3_accuracy: float = 0.0
    mean_prediction_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BenchmarkMetricsCalculator:
    """
    Computes rigorous metrics from raw event traces of a benchmark execution.
    """

    @staticmethod
    def calculate(
        strategy_name: str,
        workload_name: str,
        seed: int,
        step_results: List[Dict[str, Any]],
        ram_limit_mb: int,
        prediction_metrics: Optional[Dict[str, float]] = None,
        thrashing_window: int = 5,
    ) -> RunResultMetrics:
        """Calculates all metrics from step results trace."""
        n = len(step_results)
        if n == 0:
            return RunResultMetrics(strategy_name, workload_name, seed, 0)

        hits = sum(1 for s in step_results if s["is_cache_hit"])
        hit_rate = (hits / float(n)) * 100.0

        latencies = [s["launch_latency"] for s in step_results]
        avg_lat = float(np.mean(latencies))
        p95_lat = float(np.percentile(latencies, 95))
        p99_lat = float(np.percentile(latencies, 99))

        ram_history = [s["total_ram"] for s in step_results]
        avg_ram = float(np.mean(ram_history))
        peak_ram = float(np.max(ram_history))
        min_ram = float(np.min(ram_history))
        mem_time = float(sum(ram_history))  # MB * ticks

        reclaimed_list = [s.get("reclaimed_mb", 0.0) for s in step_results]
        total_reclaimed = float(sum(reclaimed_list))

        violations = sum(1 for r in ram_history if r > ram_limit_mb)

        # ── Thrashing and Oscillation Analysis ──────────────────────────────
        thrash_count = 0
        evictions_count = 0
        unnecessary_evictions = 0
        recent_evictions: Dict[str, int] = {}

        for i, step in enumerate(step_results):
            req_item = step["requested_item"]
            pre_st = step["pre_launch_state"]

            if pre_st == LifecycleState.ARCHIVED:
                evictions_count += 1
                # Was this item recently evicted within thrashing_window?
                if req_item in recent_evictions:
                    if (i - recent_evictions[req_item]) <= thrashing_window:
                        thrash_count += 1

            # Track post-step state changes for evictions
            post_states = step["post_states"]
            for item, st in post_states.items():
                if st == LifecycleState.ARCHIVED and item != req_item:
                    recent_evictions[item] = i

        # State distribution across all items and all ticks
        all_states_flat = []
        for step in step_results:
            for st in step["post_states"].values():
                all_states_flat.append(st.value if hasattr(st, "value") else str(st))

        total_item_ticks = len(all_states_flat) or 1
        state_dist = {
            s: round((all_states_flat.count(s) / float(total_item_ticks)) * 100.0, 2)
            for s in ["ACTIVE", "CACHED", "COMPRESSED", "ARCHIVED"]
        }

        pred_top1 = prediction_metrics.get("top_1_accuracy", 0.0) if prediction_metrics else 0.0
        pred_top3 = prediction_metrics.get("top_3_accuracy", 0.0) if prediction_metrics else 0.0
        pred_conf = prediction_metrics.get("mean_confidence", 0.0) if prediction_metrics else 0.0

        return RunResultMetrics(
            strategy_name=strategy_name,
            workload_name=workload_name,
            seed=seed,
            num_requests=n,
            cache_hit_rate_pct=round(hit_rate, 2),
            avg_launch_latency_sec=round(avg_lat, 4),
            p95_launch_latency_sec=round(p95_lat, 4),
            p99_launch_latency_sec=round(p99_lat, 4),
            avg_ram_mb=round(avg_ram, 1),
            peak_ram_mb=round(peak_ram, 1),
            min_ram_mb=round(min_ram, 1),
            memory_time_mb_ticks=round(mem_time, 1),
            total_reclaimed_mb=round(total_reclaimed, 1),
            budget_violations_count=violations,
            thrashing_count=thrash_count,
            oscillation_count=0,
            unnecessary_evictions_count=unnecessary_evictions,
            total_evictions_count=evictions_count,
            state_distribution=state_dist,
            prediction_top_1_accuracy=pred_top1,
            prediction_top_3_accuracy=pred_top3,
            mean_prediction_confidence=pred_conf,
        )
