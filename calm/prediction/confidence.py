"""
calm.prediction.confidence — Information-theoretic confidence scoring and uncertainty quantification.
"""

import math
from typing import Dict, Optional


class ConfidenceScorer:
    """
    Computes rigorous confidence and entropy metrics from probability distributions.
    Modulates confidence using both distributional peakedness (entropy) and sample support.
    """

    @staticmethod
    def calculate_entropy(probabilities: Dict[str, float]) -> float:
        """Computes Shannon entropy in bits (base 2)."""
        entropy = 0.0
        for p in probabilities.values():
            if p > 1e-9:
                entropy -= p * math.log2(p)
        return max(0.0, entropy)

    @staticmethod
    def calculate_confidence(
        probabilities: Dict[str, float],
        observation_count: Optional[int] = None,
        min_observations_for_full_confidence: int = 6,
    ) -> float:
        """
        Calculates normalized confidence in [0.0, 1.0].
        Confidence = 1.0 - (Entropy / MaxEntropy)
        Further penalized if sample count from this state is small.
        """
        n = len(probabilities)
        if n <= 1:
            return 1.0

        max_entropy = math.log2(n)
        if max_entropy <= 0:
            return 1.0

        entropy = ConfidenceScorer.calculate_entropy(probabilities)
        normalized_entropy = min(1.0, max(0.0, entropy / max_entropy))
        raw_confidence = 1.0 - normalized_entropy

        if observation_count is not None:
            sample_weight = min(1.0, observation_count / float(min_observations_for_full_confidence))
            return max(0.0, min(1.0, raw_confidence * sample_weight))

        return max(0.0, min(1.0, raw_confidence))

    @staticmethod
    def confidence_category(confidence: float) -> str:
        """Categorizes confidence into HIGH, MEDIUM, LOW."""
        if confidence >= 0.70:
            return "HIGH"
        elif confidence >= 0.45:
            return "MEDIUM"
        return "LOW"
