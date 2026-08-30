"""
calm.adapters.base — Abstract interface definitions for Telemetry, Memory, Lifecycle, and Storage providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from calm.models.app_state import LifecycleState


class TelemetryProvider(ABC):
    """Abstract interface for collecting system and process/item telemetry."""

    @abstractmethod
    def get_process_stats(self, item_id: str) -> Dict[str, Any]:
        """Returns runtime stats (access count, cpu, memory) for an item."""
        pass

    @abstractmethod
    def get_system_ram_mb(self) -> Tuple[int, int]:
        """Returns (used_mb, total_limit_mb)."""
        pass


class MemoryProvider(ABC):
    """Abstract interface for querying and allocating memory reservations."""

    @abstractmethod
    def get_resident_memory(self, item_id: str) -> int:
        pass

    @abstractmethod
    def get_total_budget_mb(self) -> int:
        pass


class LifecycleAdapter(ABC):
    """Abstract interface for executing state transitions on the underlying platform."""

    @abstractmethod
    def transition_state(self, item_id: str, target_state: LifecycleState) -> bool:
        pass


class StorageAdapter(ABC):
    """Abstract interface for compressing and archiving memory payloads."""

    @abstractmethod
    def compress(self, item_id: str, content: Any) -> bytes:
        pass

    @abstractmethod
    def decompress(self, item_id: str, compressed_bytes: bytes) -> Any:
        pass

    @abstractmethod
    def write_archive(self, item_id: str, payload: bytes) -> bool:
        pass

    @abstractmethod
    def read_archive(self, item_id: str) -> Optional[bytes]:
        pass
