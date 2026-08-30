"""
calm.models.memory_item — Unified memory object representation for Mobile & Agent modes.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from calm.models.app_state import LifecycleState


class ItemType(str, Enum):
    """Memory item type categories."""
    APP = "APP"
    CONVERSATION = "CONVERSATION"
    DOCUMENT = "DOCUMENT"
    TASK = "TASK"
    DECISION = "DECISION"
    TOOL_RESULT = "TOOL_RESULT"
    SESSION = "SESSION"
    KNOWLEDGE = "KNOWLEDGE"


@dataclass
class MemoryItem:
    """
    Unified memory item managed by CALM.
    Supports both mobile application process representations and AI agent context chunks.
    """
    id: str
    type: ItemType = ItemType.APP
    content: Any = None
    state: LifecycleState = LifecycleState.ARCHIVED
    
    # Sizing & resource footprint (in bytes for agent mode, or mapped MB for mobile mode)
    raw_size_bytes: int = 0
    compressed_size_bytes: int = 0
    resident_size_mb: int = 0
    
    # Priority & context attributes
    importance: float = 0.5
    recency: float = 0.0
    frequency: float = 0.0
    burst_score: float = 0.0
    predicted_need: float = 0.0
    prediction_confidence: float = 0.0
    priority_score: float = 0.0
    
    # Retrieval & lifecycle metadata
    retrieval_cost: float = 1.0
    last_access_tick: int = -999
    ticks_in_state: int = 0
    created_tick: int = 0
    compressed_payload: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        if self.raw_size_bytes <= 0 or self.compressed_size_bytes <= 0:
            return 1.0
        return self.compressed_size_bytes / self.raw_size_bytes

    def reset_state_timer(self) -> None:
        self.ticks_in_state = 0

    def tick(self) -> None:
        self.ticks_in_state += 1
