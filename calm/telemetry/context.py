"""
calm.telemetry.context — Context feature extraction for CALM priority scoring.
"""

from typing import Dict, List, Optional
from calm.models.memory_item import MemoryItem
from calm.telemetry.collector import TelemetryCollector


def normalize_value(value: float, max_value: float) -> float:
    """Safely normalizes value to [0.0, 1.0]."""
    if max_value <= 0.0:
        return 0.0
    return min(max(value / max_value, 0.0), 1.0)


class ContextExtractor:
    """
    Computes real-time context signals for priority scoring:
    recency, frequency, burst score, foreground flag, context importance, and memory cost factor.
    """

    def __init__(self, all_items: List[str]):
        self.all_items = all_items

    def compute_recency_scores(
        self,
        telemetry_collector: TelemetryCollector,
        current_tick: int,
    ) -> Dict[str, float]:
        """
        Calculates harmonic recency score: 1.0 / (gap + 1).
        If item has never been accessed, score is 0.0.
        """
        recency: Dict[str, float] = {}
        for item_id in self.all_items:
            t = telemetry_collector.get_or_create(item_id)
            if t.last_access_tick < 0:
                recency[item_id] = 0.0
            else:
                gap = max(0, current_tick - t.last_access_tick)
                recency[item_id] = 1.0 / (gap + 1.0)
        return recency

    def compute_frequency_scores(
        self,
        telemetry_collector: TelemetryCollector,
    ) -> Dict[str, float]:
        """
        Calculates normalized frequency scores against maximum observed accesses.
        """
        counts = {
            item_id: telemetry_collector.get_or_create(item_id).access_count
            for item_id in self.all_items
        }
        max_count = max(counts.values()) if counts and max(counts.values()) > 0 else 1
        return {item_id: normalize_value(count, max_count) for item_id, count in counts.items()}

    def compute_burst_scores(
        self,
        telemetry_collector: TelemetryCollector,
    ) -> Dict[str, float]:
        """Extracts burst access scores from telemetry."""
        return {
            item_id: telemetry_collector.get_or_create(item_id).burst_score
            for item_id in self.all_items
        }

    def compute_foreground_scores(
        self,
        current_foreground: str,
    ) -> Dict[str, float]:
        """1.0 for the active foreground item, 0.0 for others."""
        return {item_id: (1.0 if item_id == current_foreground else 0.0) for item_id in self.all_items}
