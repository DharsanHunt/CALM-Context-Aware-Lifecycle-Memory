"""
calm.policy.hysteresis — Residency duration enforcement and dual-threshold stability controller.
"""

from typing import Dict, Optional
from calm.models.app_state import LifecycleState
from calm.utils.config import HysteresisConfig


class HysteresisController:
    """
    Prevents thrashing and rapid state oscillation across consecutive ticks.
    Enforces minimum state residency duration and asymmetric promotion/demotion thresholds.
    """

    def __init__(self, config: Optional[HysteresisConfig] = None):
        self.config = config or HysteresisConfig()
        self.last_transition_tick: Dict[str, int] = {}

    def can_demote(
        self,
        item_id: str,
        current_state: LifecycleState,
        ticks_in_state: int,
        priority_score: float,
        is_force_eviction: bool = False,
    ) -> bool:
        """
        Determines whether an item is eligible for demotion.
        Under hard limit violation (is_force_eviction=True), residency constraint may be overridden,
        but under normal adaptive demotion, requires ticks_in_state >= min_state_ticks and priority < demote_threshold.
        """
        if is_force_eviction:
            return True

        if ticks_in_state < self.config.min_state_ticks:
            return False

        return priority_score <= self.config.demote_threshold

    def can_promote(
        self,
        item_id: str,
        current_state: LifecycleState,
        priority_score: float,
        is_foreground: bool = False,
    ) -> bool:
        """
        Determines whether an item is eligible for proactive promotion/prewarming.
        Foreground items are always allowed to promote to ACTIVE.
        Background prewarming requires priority > promote_threshold.
        """
        if is_foreground:
            return True
        return priority_score >= self.config.promote_threshold

    def record_transition(self, item_id: str, tick: int) -> None:
        self.last_transition_tick[item_id] = tick
