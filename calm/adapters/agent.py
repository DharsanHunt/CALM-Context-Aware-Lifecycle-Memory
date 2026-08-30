"""
calm.adapters.agent — AI Agent Context & Working Memory Orchestrator powered by CALM.
Manages Tasks, Conversation Turns, Tool Results, Decisions, and Knowledge chunks with real payload compression.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from calm.models.app_state import LifecycleState
from calm.models.memory_item import MemoryItem, ItemType
from calm.storage.compression import CompressionEngine, CompressionResult
from calm.utils.config import CALMConfig


@dataclass
class AgentContextChunk:
    """Individual AI agent context memory block."""
    chunk_id: str
    chunk_type: ItemType
    title: str
    content: str
    importance: float = 0.5
    state: LifecycleState = LifecycleState.ARCHIVED
    raw_bytes: int = 0
    compressed_bytes: int = 0
    compressed_payload: Optional[bytes] = None
    compression_ratio: float = 1.0
    access_count: int = 0
    last_access_tick: int = -1
    tags: List[str] = field(default_factory=list)


class AgentMemoryEngine:
    """
    Manages AI agent context items across the 4-tier lifecycle:
    ACTIVE      : Directly loaded in current LLM prompt context window.
    CACHED      : Uncompressed working memory ready for immediate prompt injection.
    COMPRESSED  : Real zlib compressed memory in RAM (low token/memory footprint).
    ARCHIVED    : Cold persistent disk/vector storage chunk.
    """

    def __init__(self, token_or_byte_budget: int = 50000):
        self.byte_budget = token_or_byte_budget
        self.compressor = CompressionEngine(level=6)
        self.chunks: Dict[str, AgentContextChunk] = {}
        self.tick: int = 0
        self.transition_log: List[Dict[str, Any]] = []

    def register_chunk(
        self,
        chunk_id: str,
        chunk_type: ItemType,
        title: str,
        content: str,
        importance: float = 0.5,
        initial_state: LifecycleState = LifecycleState.ARCHIVED,
        tags: Optional[List[str]] = None,
    ) -> AgentContextChunk:
        """Registers a new context item and measures its raw and compressed byte footprints."""
        raw_b = len(content.encode("utf-8"))
        comp_payload, comp_res = self.compressor.compress_payload(content)

        chunk = AgentContextChunk(
            chunk_id=chunk_id,
            chunk_type=chunk_type,
            title=title,
            content=content,
            importance=importance,
            state=initial_state,
            raw_bytes=raw_b,
            compressed_bytes=comp_res.compressed_bytes,
            compressed_payload=comp_payload,
            compression_ratio=comp_res.compression_ratio,
            tags=tags or [],
        )
        self.chunks[chunk_id] = chunk
        return chunk

    def total_resident_bytes(self) -> int:
        """Calculates total resident memory bytes occupied by ACTIVE, CACHED, and COMPRESSED chunks."""
        total = 0
        for chunk in self.chunks.values():
            if chunk.state in (LifecycleState.ACTIVE, LifecycleState.CACHED):
                total += chunk.raw_bytes
            elif chunk.state == LifecycleState.COMPRESSED:
                total += chunk.compressed_bytes
        return total

    def access_chunk(self, chunk_id: str) -> Optional[str]:
        """
        Retrieves context chunk, automatically decompressing if necessary, and promotes to ACTIVE.
        """
        self.tick += 1
        if chunk_id not in self.chunks:
            return None

        chunk = self.chunks[chunk_id]
        prev_state = chunk.state
        chunk.access_count += 1
        chunk.last_access_tick = self.tick

        # Promote to ACTIVE
        chunk.state = LifecycleState.ACTIVE
        self.transition_log.append({
            "tick": self.tick,
            "chunk_id": chunk_id,
            "from": prev_state.value,
            "to": LifecycleState.ACTIVE.value,
            "reason": "agent_query_access",
        })

        # Evict / compress background items if over budget
        self._enforce_budget(active_id=chunk_id)

        return chunk.content

    def transition_chunk(self, chunk_id: str, new_state: LifecycleState, reason: str = "") -> None:
        if chunk_id in self.chunks:
            old = self.chunks[chunk_id].state
            self.chunks[chunk_id].state = new_state
            self.transition_log.append({
                "tick": self.tick,
                "chunk_id": chunk_id,
                "from": old.value,
                "to": new_state.value,
                "reason": reason,
            })

    def _enforce_budget(self, active_id: str) -> None:
        """Demotes non-active chunks if total resident bytes exceed byte_budget."""
        while self.total_resident_bytes() > self.byte_budget:
            candidates = [
                c for c in self.chunks.values()
                if c.chunk_id != active_id and c.state != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break

            # Sort by priority: lowest importance and oldest access first
            candidates.sort(key=lambda c: (c.importance, c.last_access_tick))
            victim = candidates[0]

            if victim.state in (LifecycleState.ACTIVE, LifecycleState.CACHED):
                self.transition_chunk(victim.chunk_id, LifecycleState.COMPRESSED, reason="agent_memory_pressure")
            else:
                self.transition_chunk(victim.chunk_id, LifecycleState.ARCHIVED, reason="agent_memory_budget_exceeded")

    def get_summary_table(self) -> List[Dict[str, Any]]:
        rows = []
        for c in self.chunks.values():
            resident = c.raw_bytes if c.state in (LifecycleState.ACTIVE, LifecycleState.CACHED) else (
                c.compressed_bytes if c.state == LifecycleState.COMPRESSED else 0
            )
            rows.append({
                "Chunk ID": c.chunk_id,
                "Type": c.chunk_type.value,
                "Title": c.title,
                "State": c.state.value,
                "Importance": c.importance,
                "Raw (B)": c.raw_bytes,
                "Comp (B)": c.compressed_bytes,
                "Savings": f"{(1.0 - c.compression_ratio) * 100:.1f}%",
                "Resident (B)": resident,
                "Accesses": c.access_count,
            })
        return rows


class AgentMemoryAdapter:
    """Adapter bridging CALM Lifecycle Engine with Agent Memory."""

    def __init__(self, engine: Optional[AgentMemoryEngine] = None):
        self.engine = engine or AgentMemoryEngine()
