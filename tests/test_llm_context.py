"""
tests.test_llm_context — Unit tests for LLMContextManager and prompt token reduction.
"""

import unittest
from calm.adapters.llm_context import LLMContextManager, ContextOptimizationResult
from calm.models.memory_item import ItemType
from calm.models.app_state import LifecycleState


class TestLLMContextManager(unittest.TestCase):

    def setUp(self):
        self.mgr = LLMContextManager(active_window_turns=2, token_budget=1500)

    def test_add_and_optimize_context(self):
        self.mgr.add_message("system", "System prompt", importance=1.0)
        self.mgr.add_message("user", "User question 1", importance=0.8)
        self.mgr.add_message("assistant", "Assistant response 1", importance=0.7)
        self.mgr.add_message("tool", "TOOL LOG " * 40, item_type=ItemType.TOOL_RESULT, importance=0.3)
        self.mgr.add_message("user", "User question 2", importance=0.9)
        self.mgr.add_message("assistant", "Assistant response 2", importance=0.85)

        res = self.mgr.optimize_context()
        self.assertIsInstance(res, ContextOptimizationResult)
        self.assertGreater(res.original_tokens, res.optimized_tokens)
        self.assertGreater(res.token_savings_pct, 0.0)
        self.assertGreater(res.ttft_speedup_factor, 1.0)
        self.assertEqual(res.active_message_count, 3)

    def test_archival_and_retrieval(self):
        msg1 = self.mgr.add_message("user", "Old cold query 1", msg_id="cold_1", importance=0.1)
        self.mgr.add_message("assistant", "Response 1", importance=0.2)
        self.mgr.add_message("user", "Question 2", importance=0.2)
        self.mgr.add_message("assistant", "Response 2", importance=0.8)
        self.mgr.add_message("user", "Recent question", importance=0.9)

        self.mgr.optimize_context()
        self.assertEqual(msg1.state, LifecycleState.ARCHIVED)

        retrieved = self.mgr.retrieve_archived_message("cold_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.state, LifecycleState.CACHED)


if __name__ == "__main__":
    unittest.main()
