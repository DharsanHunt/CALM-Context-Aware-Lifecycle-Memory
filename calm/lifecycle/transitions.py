"""
calm.lifecycle.transitions — Transition cost models quantifying latency, CPU, and I/O overhead.
"""

from typing import Dict, Tuple, Optional
from calm.models.app_state import LifecycleState, TransitionCost


class TransitionCostModel:
    """
    Computes latency, CPU time, and I/O cost incurred when transitioning between lifecycle states.
    """

    # Base latency cost in seconds for transitions (from_state, to_state)
    BASE_LATENCIES: Dict[Tuple[LifecycleState, LifecycleState], float] = {
        # Promotions
        (LifecycleState.ARCHIVED, LifecycleState.ACTIVE): 2.40,
        (LifecycleState.ARCHIVED, LifecycleState.COMPRESSED): 0.60,
        (LifecycleState.ARCHIVED, LifecycleState.CACHED): 1.80,
        (LifecycleState.COMPRESSED, LifecycleState.CACHED): 0.40,
        (LifecycleState.COMPRESSED, LifecycleState.ACTIVE): 1.10,
        (LifecycleState.CACHED, LifecycleState.ACTIVE): 0.40,
        # Demotions (occur asynchronously in background)
        (LifecycleState.ACTIVE, LifecycleState.CACHED): 0.05,
        (LifecycleState.CACHED, LifecycleState.COMPRESSED): 0.15,
        (LifecycleState.COMPRESSED, LifecycleState.ARCHIVED): 0.10,
        (LifecycleState.CACHED, LifecycleState.ARCHIVED): 0.20,
        (LifecycleState.ACTIVE, LifecycleState.COMPRESSED): 0.20,
        (LifecycleState.ACTIVE, LifecycleState.ARCHIVED): 0.25,
    }

    # Base CPU processing time in milliseconds
    BASE_CPU_MS: Dict[Tuple[LifecycleState, LifecycleState], float] = {
        (LifecycleState.ARCHIVED, LifecycleState.ACTIVE): 120.0,
        (LifecycleState.ARCHIVED, LifecycleState.COMPRESSED): 40.0,
        (LifecycleState.COMPRESSED, LifecycleState.ACTIVE): 45.0,
        (LifecycleState.COMPRESSED, LifecycleState.CACHED): 35.0,
        (LifecycleState.CACHED, LifecycleState.COMPRESSED): 50.0,  # Compression CPU cost
        (LifecycleState.CACHED, LifecycleState.ACTIVE): 10.0,
        (LifecycleState.ACTIVE, LifecycleState.CACHED): 5.0,
        (LifecycleState.COMPRESSED, LifecycleState.ARCHIVED): 20.0,
    }

    @classmethod
    def calculate_cost(
        cls,
        from_state: LifecycleState,
        to_state: LifecycleState,
        item_base_ram_mb: int = 500,
        compressed_factor: float = 0.35,
    ) -> TransitionCost:
        """Calculates quantitative cost for a given transition."""
        if from_state == to_state:
            return TransitionCost()

        latency = cls.BASE_LATENCIES.get((from_state, to_state), 0.50)
        cpu_ms = cls.BASE_CPU_MS.get((from_state, to_state), 15.0)

        # Calculate RAM change
        def ram_for(s: LifecycleState) -> float:
            if s in (LifecycleState.ACTIVE, LifecycleState.CACHED):
                return float(item_base_ram_mb)
            elif s == LifecycleState.COMPRESSED:
                return float(item_base_ram_mb * compressed_factor)
            return 0.0

        ram_before = ram_for(from_state)
        ram_after = ram_for(to_state)
        mem_freed = max(0.0, ram_before - ram_after)

        io_kb = 0.0
        if from_state == LifecycleState.ARCHIVED or to_state == LifecycleState.ARCHIVED:
            io_kb = float(item_base_ram_mb * 1024 * 0.1)  # Disk / cold retrieval I/O

        return TransitionCost(
            latency_seconds=latency,
            memory_freed_mb=mem_freed,
            cpu_cost_ms=cpu_ms,
            io_cost_kb=io_kb,
        )
