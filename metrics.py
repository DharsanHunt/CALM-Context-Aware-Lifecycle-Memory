"""
metrics.py — Performance metrics for baseline vs adaptive comparison.
"""

from utils import APPS, LAUNCH_TIME


def compute_metrics(
    events: list[dict],
    baseline_states: list[str],
    adaptive_states: list[str],
    baseline_cache_hits: list[bool],
    adaptive_cache_hits: list[bool],
    baseline_thrash_flags: list[bool],
    adaptive_thrash_flags: list[bool],
) -> dict:
    """Aggregate simulation metrics."""
    n = len(events)

    baseline_hit_rate = sum(baseline_cache_hits) / n if n else 0
    adaptive_hit_rate = sum(adaptive_cache_hits) / n if n else 0

    baseline_launch = sum(LAUNCH_TIME[s] for s in baseline_states) / n if n else 0
    adaptive_launch = sum(LAUNCH_TIME[s] for s in adaptive_states) / n if n else 0

    launch_reduction = 0.0
    if baseline_launch > 0:
        launch_reduction = (baseline_launch - adaptive_launch) / baseline_launch * 100

    baseline_thrash = sum(baseline_thrash_flags)
    adaptive_thrash = sum(adaptive_thrash_flags)
    thrash_reduction = 0.0
    if baseline_thrash > 0:
        thrash_reduction = (baseline_thrash - adaptive_thrash) / baseline_thrash * 100

    return {
        "cache_hit_rate_baseline": round(baseline_hit_rate * 100, 1),
        "cache_hit_rate_adaptive": round(adaptive_hit_rate * 100, 1),
        "avg_launch_time_baseline": round(baseline_launch, 3),
        "avg_launch_time_adaptive": round(adaptive_launch, 3),
        "launch_time_reduction_pct": round(launch_reduction, 1),
        "thrashing_baseline": baseline_thrash,
        "thrashing_adaptive": adaptive_thrash,
        "thrashing_reduction_pct": round(thrash_reduction, 1),
    }


def compute_lifecycle_metrics(lifecycle_engine) -> dict:
    """
    Extract lifecycle-specific metrics from a LifecycleEngine instance.

    Returns:
        dict with total transitions, pressure stats, per-app telemetry.
    """
    transitions = lifecycle_engine.transition_log
    total_transitions = len(transitions)

    # Count transitions by type
    transition_types = {}
    for t in transitions:
        key = f"{t['from']}→{t['to']}"
        transition_types[key] = transition_types.get(key, 0) + 1

    # Pressure history
    pressure_history = list(lifecycle_engine.pressure.history)

    # Per-app telemetry snapshot
    app_telemetry = {}
    for app in APPS:
        tel = lifecycle_engine.telemetry[app]
        app_telemetry[app] = {
            "access_count": tel.access_count,
            "avg_interval": round(tel.avg_interval, 1),
            "burst_score": round(tel.burst_score, 2),
            "ticks_in_state": tel.ticks_in_state,
        }

    return {
        "total_transitions": total_transitions,
        "transition_types": transition_types,
        "pressure_history": pressure_history,
        "app_telemetry": app_telemetry,
        "final_pressure": round(lifecycle_engine.pressure.current, 3),
        "final_pressure_level": lifecycle_engine.pressure.level,
    }


def compute_cache_efficiency(states: list[str]) -> dict[str, int]:
    """Count occurrences of each cache state."""
    counts = {s: 0 for s in LAUNCH_TIME}
    for s in states:
        counts[s] = counts.get(s, 0) + 1
    return counts


def build_comparison_df(metrics: dict):
    """Return a pandas DataFrame summarising before vs after."""
    import pandas as pd

    rows = [
        {
            "Metric": "Cache Hit Rate (%)",
            "Baseline": metrics["cache_hit_rate_baseline"],
            "Adaptive": metrics["cache_hit_rate_adaptive"],
        },
        {
            "Metric": "Avg Launch Time (s)",
            "Baseline": metrics["avg_launch_time_baseline"],
            "Adaptive": metrics["avg_launch_time_adaptive"],
        },
        {
            "Metric": "Launch Time Reduction (%)",
            "Baseline": "—",
            "Adaptive": metrics["launch_time_reduction_pct"],
        },
        {
            "Metric": "Thrashing Events",
            "Baseline": metrics["thrashing_baseline"],
            "Adaptive": metrics["thrashing_adaptive"],
        },
        {
            "Metric": "Thrashing Reduction (%)",
            "Baseline": "—",
            "Adaptive": metrics["thrashing_reduction_pct"],
        },
    ]
    return pd.DataFrame(rows)
