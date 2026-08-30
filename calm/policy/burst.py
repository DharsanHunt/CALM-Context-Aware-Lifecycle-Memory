"""
calm.policy.burst — Burst access detection and protective priority scaling.
"""

from typing import Dict, List, Optional
from calm.models.telemetry import ItemTelemetry


class BurstDetector:
    """
    Detects high-frequency access bursts and generates protection scores.
    Items experiencing a burst receive protective priority boosts to prevent eviction during multi-turn interactions.
    """

    def __init__(self, burst_threshold: float = 0.35, protection_boost: float = 0.20):
        self.burst_threshold = burst_threshold
        self.protection_boost = protection_boost

    def evaluate_burst(self, telemetry: ItemTelemetry) -> float:
        """Calculates burst score from telemetry access intervals."""
        return telemetry.burst_score

    def is_bursting(self, telemetry: ItemTelemetry) -> bool:
        """Checks if item is currently in an active access burst."""
        return telemetry.burst_score >= self.burst_threshold

    def get_protection_boost(self, telemetry: ItemTelemetry) -> float:
        """Returns additional priority protection weight for bursting items."""
        if self.is_bursting(telemetry):
            return self.protection_boost * telemetry.burst_score
        return 0.0
