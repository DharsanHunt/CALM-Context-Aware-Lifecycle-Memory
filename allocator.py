"""
allocator.py — Priority scoring and pressure-aware dynamic memory allocation.
"""

import pandas as pd

from utils import (
    APPS,
    WEIGHT_FOREGROUND, WEIGHT_PREDICTION, WEIGHT_FREQUENCY, WEIGHT_RECENCY,
    HIGH_PRIORITY_THRESH, MED_PRIORITY_THRESH,
    normalize,
)
from config import SystemConfig
from predictor import MarkovPredictor


# ── Priority Scoring ─────────────────────────────────────────────────────────

def compute_frequency(logs: pd.DataFrame) -> dict[str, float]:
    counts = logs["app"].value_counts()
    max_count = counts.max()
    return {app: normalize(counts.get(app, 0), max_count) for app in APPS}


def compute_recency(logs: pd.DataFrame, current_idx: int) -> dict[str, float]:
    recency: dict[str, float] = {}
    for app in APPS:
        mask = (logs["app"] == app) & (logs.index <= current_idx)
        occurrences = logs.index[mask]
        if len(occurrences) == 0:
            recency[app] = 0.0
        else:
            last_idx = occurrences[-1]
            gap = current_idx - last_idx
            recency[app] = normalize(1.0 / (gap + 1), 1.0)
    return recency


def compute_priority_scores(
    logs: pd.DataFrame,
    current_idx: int,
    predictor: MarkovPredictor,
) -> dict[str, float]:
    """
    Priority =
        0.4 × Foreground
      + 0.3 × PredictionScore
      + 0.2 × Frequency
      + 0.1 × Recency
    """
    current_app = logs.loc[current_idx, "app"]
    foreground = {app: (1.0 if app == current_app else 0.0) for app in APPS}
    prediction = predictor.get_transition_probabilities(current_app)
    frequency = compute_frequency(logs)
    recency = compute_recency(logs, current_idx)

    return {
        app: (
            WEIGHT_FOREGROUND * foreground[app]
            + WEIGHT_PREDICTION * prediction.get(app, 0.0)
            + WEIGHT_FREQUENCY  * frequency[app]
            + WEIGHT_RECENCY    * recency[app]
        )
        for app in APPS
    }


# ── Memory Allocation ────────────────────────────────────────────────────────

def allocate_memory(priority_scores: dict[str, float], config: SystemConfig) -> dict[str, dict]:
    """
    Allocate memory tier and MB reservation based on priority.
    Tier thresholds come from config-derived values.

    Returns:
        dict mapping app → {"tier": str, "allocated_mb": int}
    """
    # Derive tier allocations from per-app config limits
    # HIGH = 75% of app's configured limit, MEDIUM = 50%, LOW = 25%
    allocation: dict[str, dict] = {}
    for app, score in priority_scores.items():
        app_limit = config.app_ram.get(app, 500)
        if score >= HIGH_PRIORITY_THRESH:
            tier = "HIGH"
            mb = int(app_limit * 0.75)
        elif score >= MED_PRIORITY_THRESH:
            tier = "MEDIUM"
            mb = int(app_limit * 0.50)
        else:
            tier = "LOW"
            mb = int(app_limit * 0.25)
        allocation[app] = {"tier": tier, "allocated_mb": max(100, mb)}
    return allocation


def allocate_memory_pressure_aware(
    priority_scores: dict[str, float],
    pressure_level: str,
    config: SystemConfig,
) -> dict[str, dict]:
    """
    Pressure-aware allocation: under high pressure, shrink low-priority
    allocations to free headroom.
    """
    scale = {
        "LOW":      1.0,
        "MEDIUM":   0.85,
        "HIGH":     0.65,
        "CRITICAL": 0.45,
    }.get(pressure_level, 1.0)

    allocation: dict[str, dict] = {}
    for app, score in priority_scores.items():
        app_limit = config.app_ram.get(app, 500)
        if score >= HIGH_PRIORITY_THRESH:
            tier = "HIGH"
            mb = int(app_limit * 0.75)
        elif score >= MED_PRIORITY_THRESH:
            tier = "MEDIUM"
            mb = int(app_limit * 0.50 * scale)
        else:
            tier = "LOW"
            mb = int(app_limit * 0.25 * scale)
        allocation[app] = {"tier": tier, "allocated_mb": max(100, mb)}
    return allocation
