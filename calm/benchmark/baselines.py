"""
calm.benchmark.baselines — Standardized baseline lifecycle managers for fair comparative evaluation.
All strategies share identical initial states, memory budgets, and pre-transition observation points.
"""

from abc import ABC, abstractmethod
import random
from typing import Dict, List, Optional, Any, Set
from collections import deque

from calm.models.app_state import LifecycleState, StateTransition
from calm.models.prediction import PredictionResult
from calm.lifecycle.manager import LifecycleManager
from calm.utils.config import CALMConfig


STRATEGY_NAMES = [
    "Random",
    "LRU",
    "LFU",
    "Reactive",
    "Predictive-Only",
    "Pressure-Only",
    "CALM",
]


class BaseStrategy(ABC):
    """Abstract base class ensuring fair, standardized benchmark execution."""

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        self.config = config
        self.all_items = list(all_items)
        self.seed = seed
        self.rng = random.Random(seed)
        self.states: Dict[str, LifecycleState] = {
            item: LifecycleState.ARCHIVED for item in self.all_items
        }
        self.tick: int = 0
        self.reclaimed_memory_history: List[float] = []

    def get_effective_ram(self, item_id: str, state: Optional[LifecycleState] = None) -> int:
        st = state if state is not None else self.states[item_id]
        return self.config.effective_ram(item_id, st.value)

    def total_ram(self) -> int:
        return sum(self.get_effective_ram(item) for item in self.all_items)

    @abstractmethod
    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        """Executes a single benchmark step and returns standardized telemetry dict."""
        pass


class RandomStrategy(BaseStrategy):
    """Random eviction under RAM pressure."""

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        self.tick += 1
        pre_launch_state = self.states[requested_item]
        is_cache_hit = pre_launch_state in (
            LifecycleState.ACTIVE,
            LifecycleState.CACHED,
            LifecycleState.COMPRESSED,
        )
        launch_latency = self.config.launch_times.get(pre_launch_state.value, 2.40)

        # Promote requested item to ACTIVE
        self.states[requested_item] = LifecycleState.ACTIVE

        # Demote other ACTIVE items to CACHED
        for item in self.all_items:
            if item != requested_item and self.states[item] == LifecycleState.ACTIVE:
                self.states[item] = LifecycleState.CACHED

        # Enforce RAM limit randomly
        reclaimed_mb = 0.0
        ram_before = self.total_ram()
        while self.total_ram() > self.config.ram_limit_mb:
            candidates = [
                i for i in self.all_items
                if i != requested_item and self.states[i] != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break
            victim = self.rng.choice(candidates)
            self.states[victim] = LifecycleState.ARCHIVED

        reclaimed_mb = max(0.0, float(ram_before - self.total_ram()))
        self.reclaimed_memory_history.append(reclaimed_mb)

        return {
            "tick": self.tick,
            "requested_item": requested_item,
            "pre_launch_state": pre_launch_state,
            "is_cache_hit": is_cache_hit,
            "launch_latency": launch_latency,
            "post_states": dict(self.states),
            "total_ram": self.total_ram(),
            "reclaimed_mb": reclaimed_mb,
        }


class LRUStrategy(BaseStrategy):
    """Least Recently Used (LRU) cache policy."""

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.last_access: Dict[str, int] = {item: -999 for item in self.all_items}

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        self.tick += 1
        self.last_access[requested_item] = self.tick

        pre_launch_state = self.states[requested_item]
        is_cache_hit = pre_launch_state in (
            LifecycleState.ACTIVE,
            LifecycleState.CACHED,
            LifecycleState.COMPRESSED,
        )
        launch_latency = self.config.launch_times.get(pre_launch_state.value, 2.40)

        # Promote requested item to ACTIVE
        self.states[requested_item] = LifecycleState.ACTIVE

        # Demote previous ACTIVE to CACHED
        for item in self.all_items:
            if item != requested_item and self.states[item] == LifecycleState.ACTIVE:
                self.states[item] = LifecycleState.CACHED

        # Evict least recently accessed items under RAM pressure
        ram_before = self.total_ram()
        while self.total_ram() > self.config.ram_limit_mb:
            candidates = [
                i for i in self.all_items
                if i != requested_item and self.states[i] != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break
            candidates.sort(key=lambda a: self.last_access.get(a, -999))
            victim = candidates[0]
            self.states[victim] = LifecycleState.ARCHIVED

        reclaimed_mb = max(0.0, float(ram_before - self.total_ram()))
        self.reclaimed_memory_history.append(reclaimed_mb)

        return {
            "tick": self.tick,
            "requested_item": requested_item,
            "pre_launch_state": pre_launch_state,
            "is_cache_hit": is_cache_hit,
            "launch_latency": launch_latency,
            "post_states": dict(self.states),
            "total_ram": self.total_ram(),
            "reclaimed_mb": reclaimed_mb,
        }


class LFUStrategy(BaseStrategy):
    """Least Frequently Used (LFU) cache policy."""

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.access_counts: Dict[str, int] = {item: 0 for item in self.all_items}

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        self.tick += 1
        self.access_counts[requested_item] += 1

        pre_launch_state = self.states[requested_item]
        is_cache_hit = pre_launch_state in (
            LifecycleState.ACTIVE,
            LifecycleState.CACHED,
            LifecycleState.COMPRESSED,
        )
        launch_latency = self.config.launch_times.get(pre_launch_state.value, 2.40)

        # Promote requested item to ACTIVE
        self.states[requested_item] = LifecycleState.ACTIVE

        # Demote previous ACTIVE to CACHED
        for item in self.all_items:
            if item != requested_item and self.states[item] == LifecycleState.ACTIVE:
                self.states[item] = LifecycleState.CACHED

        # Evict least frequently accessed items under RAM pressure
        ram_before = self.total_ram()
        while self.total_ram() > self.config.ram_limit_mb:
            candidates = [
                i for i in self.all_items
                if i != requested_item and self.states[i] != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break
            candidates.sort(key=lambda a: self.access_counts.get(a, 0))
            victim = candidates[0]
            self.states[victim] = LifecycleState.ARCHIVED

        reclaimed_mb = max(0.0, float(ram_before - self.total_ram()))
        self.reclaimed_memory_history.append(reclaimed_mb)

        return {
            "tick": self.tick,
            "requested_item": requested_item,
            "pre_launch_state": pre_launch_state,
            "is_cache_hit": is_cache_hit,
            "launch_latency": launch_latency,
            "post_states": dict(self.states),
            "total_ram": self.total_ram(),
            "reclaimed_mb": reclaimed_mb,
        }


class ReactivePressureStrategy(BaseStrategy):
    """
    Reactive Pressure-based Lifecycle Strategy:
    Uses multi-tier states (ACTIVE -> CACHED -> COMPRESSED -> ARCHIVED),
    but reacts only when the hard limit is violated, without prediction, burst, or hysteresis.
    """

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.last_access: Dict[str, int] = {item: -999 for item in self.all_items}

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        self.tick += 1
        self.last_access[requested_item] = self.tick

        pre_launch_state = self.states[requested_item]
        is_cache_hit = pre_launch_state in (
            LifecycleState.ACTIVE,
            LifecycleState.CACHED,
            LifecycleState.COMPRESSED,
        )
        launch_latency = self.config.launch_times.get(pre_launch_state.value, 2.40)

        # Promote requested item to ACTIVE
        self.states[requested_item] = LifecycleState.ACTIVE

        # Demote other ACTIVE to CACHED
        for item in self.all_items:
            if item != requested_item and self.states[item] == LifecycleState.ACTIVE:
                self.states[item] = LifecycleState.CACHED

        # Reactive step-wise demotion (CACHED -> COMPRESSED -> ARCHIVED) based on recency
        ram_before = self.total_ram()
        while self.total_ram() > self.config.ram_limit_mb:
            candidates = [
                i for i in self.all_items
                if i != requested_item and self.states[i] != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break
            # Sort by LRU
            candidates.sort(key=lambda a: self.last_access.get(a, -999))
            victim = candidates[0]
            if self.states[victim] == LifecycleState.CACHED:
                self.states[victim] = LifecycleState.COMPRESSED
            else:
                self.states[victim] = LifecycleState.ARCHIVED

        reclaimed_mb = max(0.0, float(ram_before - self.total_ram()))
        self.reclaimed_memory_history.append(reclaimed_mb)

        return {
            "tick": self.tick,
            "requested_item": requested_item,
            "pre_launch_state": pre_launch_state,
            "is_cache_hit": is_cache_hit,
            "launch_latency": launch_latency,
            "post_states": dict(self.states),
            "total_ram": self.total_ram(),
            "reclaimed_mb": reclaimed_mb,
        }


class PredictiveOnlyStrategy(BaseStrategy):
    """
    Predictive-Only Strategy:
    Uses predictive prewarming, but ignores pressure trends, burst detection, and hysteresis.
    """

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.manager = LifecycleManager(config, all_items)

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        return self.manager.step(
            requested_item=requested_item,
            prediction_result=prediction_result,
            enable_prediction=True,
            enable_burst=False,
            enable_hysteresis=False,
            enable_pressure_trend=False,
            enable_compression=True,
            enable_context=False,
        )


class PressureOnlyStrategy(BaseStrategy):
    """
    Pressure-Only Strategy:
    Uses pressure levels & trend-based demotion, but no predictive prewarming.
    """

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.manager = LifecycleManager(config, all_items)

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        return self.manager.step(
            requested_item=requested_item,
            prediction_result=None,
            enable_prediction=False,
            enable_burst=False,
            enable_hysteresis=True,
            enable_pressure_trend=True,
            enable_compression=True,
            enable_context=False,
        )


class CALMStrategy(BaseStrategy):
    """
    Full CALM V2 Strategy:
    Full integration of Prediction, Confidence, Multi-Tier Lifecycle,
    Pressure Trends, Hysteresis, and Burst Protection.
    """

    def __init__(self, config: CALMConfig, all_items: List[str], seed: int = 42):
        super().__init__(config, all_items, seed)
        self.manager = LifecycleManager(config, all_items)

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
    ) -> Dict[str, Any]:
        return self.manager.step(
            requested_item=requested_item,
            prediction_result=prediction_result,
            enable_prediction=True,
            enable_burst=True,
            enable_hysteresis=True,
            enable_pressure_trend=True,
            enable_compression=True,
            enable_context=True,
        )


def create_strategy(
    strategy_name: str,
    config: CALMConfig,
    all_items: List[str],
    seed: int = 42,
) -> BaseStrategy:
    """Factory helper to instantiate any benchmark strategy by name."""
    mapping = {
        "Random": RandomStrategy,
        "LRU": LRUStrategy,
        "LFU": LFUStrategy,
        "Reactive": ReactivePressureStrategy,
        "Predictive-Only": PredictiveOnlyStrategy,
        "Pressure-Only": PressureOnlyStrategy,
        "CALM": CALMStrategy,
    }
    cls = mapping.get(strategy_name, CALMStrategy)
    return cls(config=config, all_items=all_items, seed=seed)
