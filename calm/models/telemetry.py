"""
calm.models.telemetry — Item-level and system-wide telemetry structures.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Any, List


@dataclass
class ItemTelemetry:
    """Telemetry tracking for an individual memory item or application."""
    item_id: str
    access_count: int = 0
    last_access_tick: int = -999
    ticks_in_state: int = 0
    access_intervals: Deque[int] = field(default_factory=lambda: deque(maxlen=20))
    _prev_access_tick: int = -999

    def record_access(self, tick: int) -> None:
        if self.last_access_tick > -999:
            gap = max(1, tick - self.last_access_tick)
            self.access_intervals.append(gap)
        self._prev_access_tick = self.last_access_tick
        self.last_access_tick = tick
        self.access_count += 1

    def tick(self) -> None:
        self.ticks_in_state += 1

    def reset_state_timer(self) -> None:
        self.ticks_in_state = 0

    @property
    def avg_interval(self) -> float:
        if not self.access_intervals:
            return 999.0
        return sum(self.access_intervals) / len(self.access_intervals)

    @property
    def burst_score(self) -> float:
        """
        Calculates burst access score in [0.0, 1.0].
        Scores higher when recent access intervals are very small.
        """
        if len(self.access_intervals) < 2:
            return 0.0
        recent = list(self.access_intervals)
        last_two = sum(recent[-2:]) / 2.0
        overall = sum(recent) / len(recent)
        
        # Immediate rapid succession gives high burst
        if last_two <= 2.0:
            return max(0.40, min(1.0, 1.0 / (last_two + 0.2)))
        
        ratio = overall / (last_two + 0.1)
        return max(0.0, min(1.0, ratio / 2.5))


@dataclass
class SystemTelemetrySnapshot:
    """Snapshot of overall system state at a specific simulation tick."""
    tick: int
    total_ram_used_mb: int
    ram_limit_mb: int
    pressure_ratio: float
    pressure_level: str
    pressure_trend: str
    active_count: int
    cached_count: int
    compressed_count: int
    archived_count: int
    requested_item: str
    hit: bool
    launch_latency: float
    reclaimed_memory_mb: float = 0.0
