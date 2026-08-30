"""
Unit tests for AI Agent Context Memory management mode.
"""

import unittest
from calm.adapters.agent import AgentMemoryEngine
from calm.models.app_state import LifecycleState
from calm.models.memory_item import ItemType


class TestAgentMemoryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AgentMemoryEngine(token_or_byte_budget=1000)

    def test_register_and_compression(self):
        chunk = self.engine.register_chunk(
            chunk_id="tool_out_1",
            chunk_type=ItemType.TOOL_RESULT,
            title="Database Query Result",
            content="[{'user_id': 1, 'role': 'admin', 'status': 'active'}, {'user_id': 2, 'role': 'user'}]" * 10,
            importance=0.6,
            initial_state=LifecycleState.COMPRESSED,
        )
        self.assertEqual(chunk.chunk_id, "tool_out_1")
        self.assertGreater(chunk.raw_bytes, chunk.compressed_bytes)
        self.assertLess(chunk.compression_ratio, 1.0)
        self.assertEqual(self.engine.total_resident_bytes(), chunk.compressed_bytes)

    def test_access_and_decompression(self):
        content_str = "Important architectural decision notes: Use CALM V2 unified engine."
        self.engine.register_chunk(
            chunk_id="decision_1",
            chunk_type=ItemType.DECISION,
            title="Architecture Decision",
            content=content_str,
            importance=0.9,
            initial_state=LifecycleState.COMPRESSED,
        )
        retrieved = self.engine.access_chunk("decision_1")
        self.assertEqual(retrieved, content_str)
        self.assertEqual(self.engine.chunks["decision_1"].state, LifecycleState.ACTIVE)

    def test_agent_budget_enforcement(self):
        # Register several heavy chunks until budget is exceeded
        for i in range(5):
            self.engine.register_chunk(
                chunk_id=f"doc_{i}",
                chunk_type=ItemType.DOCUMENT,
                title=f"Doc {i}",
                content="Long documentation text block. " * 30,
                importance=0.3 + 0.1 * i,
                initial_state=LifecycleState.CACHED,
            )
        self.engine.access_chunk("doc_4")
        self.assertLessEqual(self.engine.total_resident_bytes(), self.engine.byte_budget + 1000)


if __name__ == "__main__":
    unittest.main()
