"""
calm.policy.priority — Multi-signal confidence-aware priority function for CALM V2.
"""

from typing import Dict, List, Optional
from calm.utils.config import PriorityWeights
from calm.models.prediction import PredictionResult


class PriorityEngine:
    """
    Computes priority scores for all items across multiple telemetry, prediction,
    and context signals with confidence modulation and ablation support.
    """

    def __init__(self, weights: Optional[PriorityWeights] = None):
        self.weights = weights or PriorityWeights()

    def compute_scores(
        self,
        all_items: List[str],
        foreground_item: str,
        prediction_result: Optional[PredictionResult],
        recency_scores: Dict[str, float],
        frequency_scores: Dict[str, float],
        burst_scores: Dict[str, float],
        context_importances: Optional[Dict[str, float]] = None,
        memory_cost_factors: Optional[Dict[str, float]] = None,
        # Ablation overrides
        enable_prediction: bool = True,
        enable_burst: bool = True,
        enable_context: bool = True,
    ) -> Dict[str, float]:
        """
        Computes composite priority in [0.0, 1.0] for every item.
        """
        ctx_map = context_importances or {item: 0.5 for item in all_items}
        cost_map = memory_cost_factors or {item: 0.2 for item in all_items}

        pred_probs = prediction_result.probability_distribution if prediction_result else {}
        confidence = prediction_result.confidence if prediction_result else 0.0

        scores: Dict[str, float] = {}

        for item in all_items:
            # 1. Foreground signal
            fg_val = 1.0 if item == foreground_item else 0.0

            # 2. Prediction signal modulated by confidence
            if enable_prediction and prediction_result:
                prob = pred_probs.get(item, 0.0)
                # Confidence scaling: high confidence gives strong boost, low confidence decays
                pred_val = prob * (0.3 + 0.7 * confidence)
            else:
                pred_val = 0.0

            # 3. Recency & Frequency signals
            rec_val = recency_scores.get(item, 0.0)
            freq_val = frequency_scores.get(item, 0.0)

            # 4. Burst signal
            burst_val = burst_scores.get(item, 0.0) if enable_burst else 0.0

            # 5. Context Importance signal
            ctx_val = ctx_map.get(item, 0.5) if enable_context else 0.0

            # 6. Memory Cost penalty
            cost_val = cost_map.get(item, 0.0)

            # Weighted linear combination
            raw_score = (
                self.weights.foreground * fg_val
                + (self.weights.prediction if enable_prediction else 0.0) * pred_val
                + self.weights.recency * rec_val
                + self.weights.frequency * freq_val
                + (self.weights.burst if enable_burst else 0.0) * burst_val
                + (self.weights.context_importance if enable_context else 0.0) * ctx_val
                - self.weights.memory_cost * cost_val
            )

            # Normalize to [0.0, 1.0]
            scores[item] = max(0.0, min(1.0, raw_score))

        return scores
