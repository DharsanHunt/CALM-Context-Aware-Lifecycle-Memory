"""
calm.prediction.variable_order — Variable-Order Markov & PPM (Prediction by Partial Matching).
Captures higher-order access patterns (order-2 and order-1 contexts) with fallback smoothing,
enabling accurate prediction of complex user multi-app workflows.
"""

from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
from calm.models.prediction import PredictionResult, PredictionCandidate
from calm.prediction.predictor import BasePredictor
from calm.prediction.confidence import ConfidenceScorer


class VariableOrderMarkovPredictor(BasePredictor):
    """
    Higher-Order Markov model supporting multi-step context history (Order-2 & Order-1)
    with hierarchical fallback smoothing.
    """

    def __init__(self, max_order: int = 2, smoothing_alpha: float = 0.05, min_context_count: int = 2):
        self.max_order = max_order
        self.smoothing_alpha = smoothing_alpha
        self.min_context_count = min_context_count
        self.all_items: List[str] = []

        # Transition frequency tables:
        # Order 1: counts_1[src][dst]
        # Order 2: counts_2[(src1, src2)][dst]
        self.counts_1: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.counts_2: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.unigram_counts: Dict[str, int] = defaultdict(int)

    def fit(self, sequence: List[str], all_items: Optional[List[str]] = None) -> "VariableOrderMarkovPredictor":
        if all_items:
            self.all_items = list(all_items)
        else:
            self.all_items = sorted(list(set(sequence)))

        # Reset counts
        self.counts_1.clear()
        self.counts_2.clear()
        self.unigram_counts.clear()

        for item in sequence:
            self.unigram_counts[item] += 1

        # Build order-1 and order-2 counts
        for i in range(len(sequence) - 1):
            src = sequence[i]
            dst = sequence[i + 1]
            self.counts_1[src][dst] += 1

            if i < len(sequence) - 2:
                src1 = sequence[i]
                src2 = sequence[i + 1]
                dst2 = sequence[i + 2]
                self.counts_2[(src1, src2)][dst2] += 1

        return self

    def predict_with_history(
        self,
        history: List[str],
        top_k: int = 3,
    ) -> PredictionResult:
        """
        Predicts next item using recent history.
        Uses order-2 if len(history) >= 2 and observations exist, otherwise order-1.
        """
        if not self.all_items:
            return PredictionResult(predicted_item="", confidence=0.0, top_candidates=[], is_fallback=True)

        probs: Dict[str, float] = {}
        used_order = 1

        # Check Order-2 context
        if len(history) >= 2 and self.max_order >= 2:
            ctx2 = (history[-2], history[-1])
            total_obs = sum(self.counts_2[ctx2].values())
            if total_obs >= self.min_context_count:
                used_order = 2
                N = len(self.all_items)
                denom = total_obs + self.smoothing_alpha * N
                for item in self.all_items:
                    c = self.counts_2[ctx2].get(item, 0)
                    probs[item] = (c + self.smoothing_alpha) / denom

        # Fallback to Order-1 context
        if not probs and len(history) >= 1:
            used_order = 1
            src1 = history[-1]
            total_obs = sum(self.counts_1[src1].values())
            N = len(self.all_items)
            denom = total_obs + self.smoothing_alpha * N if total_obs > 0 else N
            for item in self.all_items:
                c = self.counts_1[src1].get(item, 0) if total_obs > 0 else 1
                probs[item] = (c + self.smoothing_alpha) / denom if total_obs > 0 else 1.0 / N

        # Uniform fallback if empty
        if not probs:
            p_uniform = 1.0 / len(self.all_items)
            probs = {item: p_uniform for item in self.all_items}
            used_order = 0

        # Sort candidates
        sorted_candidates = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top_items = [
            PredictionCandidate(item_id=k, probability=round(v, 4), rank=idx + 1)
            for idx, (k, v) in enumerate(sorted_candidates[:top_k])
        ]

        best_item = top_items[0].item_id if top_items else ""
        confidence = ConfidenceScorer.calculate_confidence(probs)
        entropy = ConfidenceScorer.calculate_entropy(probs)
        src_str = history[-1] if history else ""

        return PredictionResult(
            source_item=src_str,
            top_1=best_item,
            top_k=top_items,
            confidence=round(confidence, 4),
            entropy=round(entropy, 4),
            probability_distribution={k: round(v, 4) for k, v in probs.items()},
        )

    def get_transition_probabilities(self, current_item: str) -> Dict[str, float]:
        """Returns order-1 transition distribution P(Next | current_item)."""
        if current_item not in self.counts_1 or not self.all_items:
            p_unif = 1.0 / len(self.all_items) if self.all_items else 0.0
            return {item: p_unif for item in self.all_items}

        total_obs = sum(self.counts_1[current_item].values())
        N = len(self.all_items)
        denom = total_obs + self.smoothing_alpha * N
        return {
            item: round((self.counts_1[current_item].get(item, 0) + self.smoothing_alpha) / denom, 4)
            for item in self.all_items
        }

    def predict(self, current_item: str, top_k: int = 3) -> PredictionResult:
        return self.predict_with_history([current_item], top_k=top_k)
