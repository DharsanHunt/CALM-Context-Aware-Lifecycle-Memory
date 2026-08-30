"""
calm.policy.pressure — Memory pressure tracking with multi-level thresholds and trend analysis.
"""

from collections import deque
from enum import Enum
from typing import Deque, List, Optional
import numpy as np

from calm.utils.config import PressureThresholds


class PressureLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PressureTrend(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"


class PressureEngine:
    """
    Tracks memory utilization ratio and computes rolling trends.
    Enables early preemptive lifecycle decisions when pressure is rapidly rising.
    """

    def __init__(self, thresholds: Optional[PressureThresholds] = None):
        self.thresholds = thresholds or PressureThresholds()
        self.history: Deque[float] = deque(maxlen=self.thresholds.rolling_window)
        self.current_ratio: float = 0.0
        self.slope: float = 0.0

    def update(self, used_ram_mb: int, ram_limit_mb: int) -> None:
        """Updates current pressure ratio and trend slope."""
        if ram_limit_mb > 0:
            self.current_ratio = used_ram_mb / float(ram_limit_mb)
        else:
            self.current_ratio = 1.0

        self.history.append(self.current_ratio)

        # Compute trend slope using split-half comparison
        if len(self.history) >= 4:
            arr = list(self.history)
            half = len(arr) // 2
            first_half_avg = sum(arr[:half]) / half
            second_half_avg = sum(arr[half:]) / (len(arr) - half)
            self.slope = second_half_avg - first_half_avg
        else:
            self.slope = 0.0

    @property
    def level(self) -> PressureLevel:
        """Calculates current categorical pressure level."""
        if self.current_ratio < self.thresholds.low:
            return PressureLevel.LOW
        elif self.current_ratio < self.thresholds.moderate:
            return PressureLevel.MODERATE
        elif self.current_ratio < self.thresholds.critical:
            return PressureLevel.HIGH
        return PressureLevel.CRITICAL

    @property
    def trend(self) -> PressureTrend:
        """Calculates direction of memory pressure trajectory."""
        if self.slope >= self.thresholds.rising_slope_threshold:
            return PressureTrend.RISING
        elif self.slope <= self.thresholds.falling_slope_threshold:
            return PressureTrend.FALLING
        return PressureTrend.STABLE

    @property
    def is_urgent(self) -> bool:
        """Returns True if system is either in CRITICAL or HIGH + RISING state."""
        return self.level == PressureLevel.CRITICAL or (
            self.level == PressureLevel.HIGH and self.trend == PressureTrend.RISING
        )
