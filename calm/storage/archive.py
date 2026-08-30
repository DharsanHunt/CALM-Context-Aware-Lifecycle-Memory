"""
calm.storage.archive — Cold persistent backing store for evicted or long-term archived items.
"""

from typing import Dict, List, Optional, Any
from calm.models.memory_item import MemoryItem
from calm.models.app_state import LifecycleState


class ColdArchiveStore:
    """
    Simulated or persistent cold archive store.
    Items in ARCHIVED state reside here, freeing system RAM at the cost of disk retrieval latency.
    """

    def __init__(self):
        self.archive_pool: Dict[str, MemoryItem] = {}

    def archive(self, item: MemoryItem) -> None:
        item.state = LifecycleState.ARCHIVED
        self.archive_pool[item.id] = item

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        return self.archive_pool.pop(item_id, None)

    def contains(self, item_id: str) -> bool:
        return item_id in self.archive_pool

    def count(self) -> int:
        return len(self.archive_pool)
