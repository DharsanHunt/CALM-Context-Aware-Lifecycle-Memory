"""
calm.telemetry.collector — Real-time telemetry collector for items and system memory.
"""

from typing import Dict, List, Optional, Any
from calm.models.telemetry import ItemTelemetry, SystemTelemetrySnapshot
from calm.models.app_state import LifecycleState


class TelemetryCollector:
    """
    Maintains telemetry statistics across all tracked items and system ticks.
    """

    def __init__(self, item_ids: Optional[List[str]] = None):
        self.items: Dict[str, ItemTelemetry] = {}
        if item_ids:
            for item_id in item_ids:
                self.items[item_id] = ItemTelemetry(item_id=item_id)
        self.snapshots: List[SystemTelemetrySnapshot] = []

    def get_or_create(self, item_id: str) -> ItemTelemetry:
        if item_id not in self.items:
            self.items[item_id] = ItemTelemetry(item_id=item_id)
        return self.items[item_id]

    def record_access(self, item_id: str, tick: int) -> None:
        telemetry = self.get_or_create(item_id)
        telemetry.record_access(tick)

    def advance_tick(self) -> None:
        for telemetry in self.items.values():
            telemetry.tick()

    def record_snapshot(self, snapshot: SystemTelemetrySnapshot) -> None:
        self.snapshots.append(snapshot)

    def get_telemetry_table(self) -> List[Dict[str, Any]]:
        rows = []
        for item_id, t in self.items.items():
            rows.append({
                "item_id": item_id,
                "access_count": t.access_count,
                "avg_interval": round(t.avg_interval, 2),
                "burst_score": round(t.burst_score, 3),
                "ticks_in_state": t.ticks_in_state,
                "last_access_tick": t.last_access_tick,
            })
        return rows
