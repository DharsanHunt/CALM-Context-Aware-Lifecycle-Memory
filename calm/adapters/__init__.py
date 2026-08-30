"""
calm.adapters — Adapter abstraction layer for Simulated Mobile, Real Android interfaces, and AI Agent Context.
"""

from calm.adapters.base import (
    TelemetryProvider,
    MemoryProvider,
    LifecycleAdapter,
    StorageAdapter,
)
from calm.adapters.simulated import (
    SimulatedTelemetryProvider,
    SimulatedMemoryProvider,
    SimulatedLifecycleAdapter,
)
from calm.adapters.agent import (
    AgentMemoryAdapter,
    AgentContextChunk,
    AgentMemoryEngine,
)

__all__ = [
    "TelemetryProvider",
    "MemoryProvider",
    "LifecycleAdapter",
    "StorageAdapter",
    "SimulatedTelemetryProvider",
    "SimulatedMemoryProvider",
    "SimulatedLifecycleAdapter",
    "AgentMemoryAdapter",
    "AgentContextChunk",
    "AgentMemoryEngine",
]
