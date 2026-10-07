"""
tests.test_variable_order — Unit tests for VariableOrderMarkovPredictor.
"""

import unittest
from calm.prediction.variable_order import VariableOrderMarkovPredictor


class TestVariableOrderMarkov(unittest.TestCase):

    def setUp(self):
        self.pred = VariableOrderMarkovPredictor(max_order=2, smoothing_alpha=0.01)
        # Sequence where [A, B] -> C and [D, B] -> E
        self.seq = ["A", "B", "C", "A", "B", "C", "D", "B", "E", "D", "B", "E"] * 10
        self.pred.fit(self.seq, all_items=["A", "B", "C", "D", "E"])

    def test_order_2_prediction(self):
        res1 = self.pred.predict_with_history(["A", "B"])
        self.assertEqual(res1.top_1, "C")
        self.assertGreater(res1.confidence, 0.70)

        res2 = self.pred.predict_with_history(["D", "B"])
        self.assertEqual(res2.top_1, "E")
        self.assertGreater(res2.confidence, 0.70)

    def test_order_1_fallback(self):
        # [Z, B] is unseen in order-2, should fall back to order-1
        res = self.pred.predict_with_history(["Z", "B"])
        self.assertIn(res.top_1, ["C", "E"])

    def test_transition_probabilities(self):
        probs = self.pred.get_transition_probabilities("B")
        self.assertIn("C", probs)
        self.assertIn("E", probs)
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
