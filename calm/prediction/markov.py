"""
calm.prediction.markov — Robust Markov Chain predictor with smoothing, confidence, and multi-step projection.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np

from calm.models.prediction import PredictionResult, PredictionCandidate
from calm.prediction.predictor import BasePredictor
from calm.prediction.confidence import ConfidenceScorer


class MarkovPredictor(BasePredictor):
    """
    First-order & multi-step Markov Chain transition predictor.
    Supports Laplace smoothing, confidence estimation, and multi-step sequence projection.
    """

    def __init__(self, smoothing_alpha: float = 0.05):
        self.smoothing_alpha = smoothing_alpha
        self.all_items: List[str] = []
        self.item_to_idx: Dict[str, int] = {}
        self.idx_to_item: Dict[int, str] = {}
        
        self.transition_counts: Dict[str, Dict[str, int]] = {}
        self.transition_probs: Dict[str, Dict[str, float]] = {}
        self.state_observation_counts: Dict[str, int] = {}
        self.transition_matrix_np: Optional[np.ndarray] = None
        self.is_trained: bool = False

    def fit(self, sequence: List[str], all_items: Optional[List[str]] = None) -> None:
        """
        Builds transition counts strictly from sequence without future leakage.
        Applies Laplace smoothing: P(dst|src) = (count(src, dst) + alpha) / (total(src) + alpha * N).
        """
        if all_items:
            self.all_items = list(all_items)
        else:
            self.all_items = sorted(list(set(sequence)))

        n = len(self.all_items)
        self.item_to_idx = {item: i for i, item in enumerate(self.all_items)}
        self.idx_to_item = {i: item for i, item in enumerate(self.all_items)}

        self.transition_counts = {src: {dst: 0 for dst in self.all_items} for src in self.all_items}
        self.state_observation_counts = {src: 0 for src in self.all_items}

        # Count consecutive pairs
        for i in range(len(sequence) - 1):
            src, dst = sequence[i], sequence[i + 1]
            if src in self.transition_counts and dst in self.transition_counts[src]:
                self.transition_counts[src][dst] += 1
                self.state_observation_counts[src] += 1

        # Calculate smoothed probability matrix
        self.transition_probs = {}
        matrix = np.zeros((n, n), dtype=np.float64)

        for i, src in enumerate(self.all_items):
            total_obs = self.state_observation_counts[src]
            denom = total_obs + self.smoothing_alpha * n
            row_probs: Dict[str, float] = {}

            for j, dst in enumerate(self.all_items):
                count = self.transition_counts[src][dst]
                if denom > 0:
                    prob = (count + self.smoothing_alpha) / denom
                else:
                    prob = 1.0 / n
                row_probs[dst] = float(prob)
                matrix[i, j] = prob

            # Normalize row to ensure exact sum = 1.0
            row_sum = sum(row_probs.values())
            if row_sum > 0:
                row_probs = {k: v / row_sum for k, v in row_probs.items()}
                matrix[i, :] = matrix[i, :] / np.sum(matrix[i, :])

            self.transition_probs[src] = row_probs

        self.transition_matrix_np = matrix
        self.is_trained = True

    def get_transition_probabilities(self, current_item: str) -> Dict[str, float]:
        """Returns the full probability distribution P(next | current_item)."""
        if not self.is_trained:
            raise RuntimeError("Predictor is not trained. Call fit() first.")
        if current_item not in self.transition_probs:
            # Fallback uniform for unknown items
            n = len(self.all_items) or 1
            return {item: 1.0 / n for item in self.all_items}
        return dict(self.transition_probs[current_item])

    def predict(self, current_item: str, top_k: int = 3) -> PredictionResult:
        """
        Performs inference given current item.
        Calculates top-1 candidate, top-k ranking, Shannon entropy, and sample-adjusted confidence.
        """
        probs = self.get_transition_probabilities(current_item)
        sorted_candidates = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        top_1 = sorted_candidates[0][0] if sorted_candidates else current_item
        candidates = [
            PredictionCandidate(item_id=item, probability=prob, rank=rank + 1)
            for rank, (item, prob) in enumerate(sorted_candidates[:top_k])
        ]

        obs_count = self.state_observation_counts.get(current_item, 0)
        entropy = ConfidenceScorer.calculate_entropy(probs)
        confidence = ConfidenceScorer.calculate_confidence(probs, observation_count=obs_count)

        return PredictionResult(
            source_item=current_item,
            top_1=top_1,
            top_k=candidates,
            confidence=confidence,
            entropy=entropy,
            probability_distribution=probs,
        )

    def predict_multi_step(
        self,
        current_item: str,
        steps: int = 2,
        top_k_per_step: int = 2,
    ) -> List[List[Tuple[str, float]]]:
        """
        Computes multi-step future lookahead paths: P(A -> B -> C).
        Returns list of sequential path tuples: [(step_1_app, prob), (step_2_app, cumulative_prob), ...].
        """
        if not self.is_trained or self.transition_matrix_np is None:
            return []
        if current_item not in self.item_to_idx:
            return []

        paths: List[List[Tuple[str, float]]] = []
        src_idx = self.item_to_idx[current_item]
        
        # Step 1 top candidates
        step1_probs = self.transition_matrix_np[src_idx]
        top_indices = np.argsort(step1_probs)[::-1][:top_k_per_step]

        for idx1 in top_indices:
            p1 = float(step1_probs[idx1])
            app1 = self.idx_to_item[idx1]
            if steps == 1:
                paths.append([(app1, p1)])
            else:
                step2_probs = self.transition_matrix_np[idx1]
                top2_indices = np.argsort(step2_probs)[::-1][:top_k_per_step]
                for idx2 in top2_indices:
                    p2 = float(step2_probs[idx2])
                    app2 = self.idx_to_item[idx2]
                    paths.append([(app1, p1), (app2, p1 * p2)])

        return paths
