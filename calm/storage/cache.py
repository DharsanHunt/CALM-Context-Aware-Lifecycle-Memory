"""
calm.storage.cache — In-memory cache tier tracking resident active and cached memory items.
"""

from typing import Dict, List, Optional
from calm.models.memory_item import MemoryItem
from calm.models.app_state import LifecycleState


class MemoryCachePool:
    """
    Tracks and manages memory objects currently held in resident RAM (ACTIVE, CACHED, COMPRESSED).
    """

    def __init__(self, ram_limit_mb: int = 2500):
        self.ram_limit_mb = ram_limit_mb
        self.items: Dict[str, MemoryItem] = {}

    def put(self, item: MemoryItem) -> None:
        self.items[item.id] = item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        return self.items.get(item_id)

    def remove(self, item_id: str) -> Optional[MemoryItem]:
        return self.items.pop(item_id, None)

    def list_by_state(self, state: LifecycleState) -> List[MemoryItem]:
        return [it for it in self.items.values() if it.state == state]

    def total_resident_bytes(self) -> int:
        total = 0
        for it in self.items.values():
            if it.state in (LifecycleState.ACTIVE, LifecycleState.CACHED):
                total += it.raw_size_bytes
            elif it.state == LifecycleState.COMPRESSED:
                total += it.compressed_size_bytes
        return total
