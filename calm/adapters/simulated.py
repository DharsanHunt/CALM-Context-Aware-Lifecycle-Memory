"""
calm.adapters.simulated — Simulated providers for mobile memory benchmarking.
"""

from typing import Dict, Any, Tuple
from calm.models.app_state import LifecycleState
from calm.adapters.base import TelemetryProvider, MemoryProvider, LifecycleAdapter
from calm.utils.config import CALMConfig


class SimulatedTelemetryProvider(TelemetryProvider):
    """Simulated telemetry provider reading from virtual application models."""

    def __init__(self, config: CALMConfig):
        self.config = config
        self.used_ram: int = 0

    def get_process_stats(self, item_id: str) -> Dict[str, Any]:
        return {
            "item_id": item_id,
            "base_ram_mb": self.config.app_ram.get(item_id, 500),
        }

    def get_system_ram_mb(self) -> Tuple[int, int]:
        return self.used_ram, self.config.ram_limit_mb


class SimulatedMemoryProvider(MemoryProvider):
    """Simulated memory budget provider."""

    def __init__(self, config: CALMConfig):
        self.config = config

    def get_resident_memory(self, item_id: str) -> int:
        return self.config.app_ram.get(item_id, 500)

    def get_total_budget_mb(self) -> int:
        return self.config.ram_limit_mb


class SimulatedLifecycleAdapter(LifecycleAdapter):
    """Simulated OS lifecycle adapter logging state transitions."""

    def __init__(self):
        self.current_states: Dict[str, LifecycleState] = {}

    def transition_state(self, item_id: str, target_state: LifecycleState) -> bool:
        self.current_states[item_id] = target_state
        return True
