"""
calm.models.app_state — Explicit lifecycle states and transition modeling.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class LifecycleState(str, Enum):
    """
    The 4-tier lifecycle states for CALM V2:
    ACTIVE      : Currently in the foreground / executing. Highest priority.
    CACHED      : Resident in RAM, uncompressed. Instant launch / reuse.
    COMPRESSED  : In-memory compressed state. Low RAM footprint, fast decompression.
    ARCHIVED    : Evicted from resident RAM to backing store / cold archive.
    """
    ACTIVE = "ACTIVE"
    CACHED = "CACHED"
    COMPRESSED = "COMPRESSED"
    ARCHIVED = "ARCHIVED"


@dataclass
class TransitionCost:
    """Quantitative cost breakdown for state transitions."""
    latency_seconds: float = 0.0
    memory_freed_mb: float = 0.0
    cpu_cost_ms: float = 0.0
    io_cost_kb: float = 0.0


@dataclass
class StateTransition:
    """Record of an explicit lifecycle transition."""
    tick: int
    item_id: str
    from_state: LifecycleState
    to_state: LifecycleState
    cost: TransitionCost
    reason: str = ""
    confidence: float = 0.0
    priority: float = 0.0
