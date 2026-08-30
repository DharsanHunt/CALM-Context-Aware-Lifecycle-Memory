"""
calm.prediction.evaluation — Strict temporal evaluation for prediction models with zero future data leakage.
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np

from calm.prediction.predictor import BasePredictor


class PredictionEvaluator:
    """
    Evaluates predictors on unseen test sequences.
    Calculates top-1, top-3, top-k accuracy, mean confidence, mean entropy, and Brier score.
    """

    @staticmethod
    def evaluate(
        predictor: BasePredictor,
        test_sequence: List[str],
        top_k: int = 3,
    ) -> Dict[str, float]:
        """
        Evaluates predictions for every consecutive pair (test_sequence[i], test_sequence[i+1]).
        """
        if len(test_sequence) < 2:
            return {
                "top_1_accuracy": 0.0,
                "top_3_accuracy": 0.0,
                "top_k_accuracy": 0.0,
                "mean_confidence": 0.0,
                "mean_entropy": 0.0,
                "brier_score": 0.0,
                "sample_count": 0,
            }

        top_1_hits = 0
        top_3_hits = 0
        top_k_hits = 0
        confidences = []
        entropies = []
        brier_errors = []

        total_pairs = len(test_sequence) - 1

        for i in range(total_pairs):
            current_item = test_sequence[i]
            actual_next = test_sequence[i + 1]

            pred_res = predictor.predict(current_item, top_k=max(3, top_k))
            confidences.append(pred_res.confidence)
            entropies.append(pred_res.entropy)

            if pred_res.top_1 == actual_next:
                top_1_hits += 1

            if pred_res.is_correct_top_k(actual_next, k=3):
                top_3_hits += 1

            if pred_res.is_correct_top_k(actual_next, k=top_k):
                top_k_hits += 1

            # Brier score: sum((prob - 1(y=k))^2)
            probs = pred_res.probability_distribution
            brier_sum = 0.0
            for item, p in probs.items():
                target = 1.0 if item == actual_next else 0.0
                brier_sum += (p - target) ** 2
            brier_errors.append(brier_sum)

        return {
            "top_1_accuracy": round((top_1_hits / total_pairs) * 100.0, 2),
            "top_3_accuracy": round((top_3_hits / total_pairs) * 100.0, 2),
            "top_k_accuracy": round((top_k_hits / total_pairs) * 100.0, 2),
            "mean_confidence": round(float(np.mean(confidences)), 4),
            "mean_entropy": round(float(np.mean(entropies)), 4),
            "brier_score": round(float(np.mean(brier_errors)), 4),
            "sample_count": total_pairs,
        }
