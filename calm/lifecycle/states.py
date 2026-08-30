"""
calm.lifecycle.states — Directional state navigation helpers for 4-tier lifecycle.
"""

from typing import Dict, Optional, Set, Tuple
from calm.models.app_state import LifecycleState


# Promotion graph: ARCHIVED -> COMPRESSED -> CACHED -> ACTIVE
PROMOTION_GRAPH: Dict[LifecycleState, LifecycleState] = {
    LifecycleState.ARCHIVED: LifecycleState.COMPRESSED,
    LifecycleState.COMPRESSED: LifecycleState.CACHED,
    LifecycleState.CACHED: LifecycleState.ACTIVE,
}

# Demotion graph: ACTIVE -> CACHED -> COMPRESSED -> ARCHIVED
DEMOTION_GRAPH: Dict[LifecycleState, LifecycleState] = {
    LifecycleState.ACTIVE: LifecycleState.CACHED,
    LifecycleState.CACHED: LifecycleState.COMPRESSED,
    LifecycleState.COMPRESSED: LifecycleState.ARCHIVED,
}

VALID_TRANSITIONS: Set[Tuple[LifecycleState, LifecycleState]] = {
    # Direct promotions
    (LifecycleState.ARCHIVED, LifecycleState.ACTIVE),
    (LifecycleState.ARCHIVED, LifecycleState.COMPRESSED),
    (LifecycleState.ARCHIVED, LifecycleState.CACHED),
    (LifecycleState.COMPRESSED, LifecycleState.CACHED),
    (LifecycleState.COMPRESSED, LifecycleState.ACTIVE),
    (LifecycleState.CACHED, LifecycleState.ACTIVE),
    # Direct demotions
    (LifecycleState.ACTIVE, LifecycleState.CACHED),
    (LifecycleState.ACTIVE, LifecycleState.COMPRESSED),
    (LifecycleState.ACTIVE, LifecycleState.ARCHIVED),
    (LifecycleState.CACHED, LifecycleState.COMPRESSED),
    (LifecycleState.CACHED, LifecycleState.ARCHIVED),
    (LifecycleState.COMPRESSED, LifecycleState.ARCHIVED),
}


def get_next_promotion_state(current: LifecycleState) -> Optional[LifecycleState]:
    return PROMOTION_GRAPH.get(current)


def get_next_demotion_state(current: LifecycleState) -> Optional[LifecycleState]:
    return DEMOTION_GRAPH.get(current)
