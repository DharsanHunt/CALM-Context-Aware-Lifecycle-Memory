"""
calm.models.prediction — Prediction outputs, candidate rankings, and confidence models.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class PredictionCandidate:
    """Individual candidate predicted for next access."""
    item_id: str
    probability: float
    rank: int = 1


@dataclass
class PredictionResult:
    """Complete prediction inference result from the prediction engine."""
    source_item: str
    top_1: str
    top_k: List[PredictionCandidate] = field(default_factory=list)
    confidence: float = 0.0
    entropy: float = 0.0
    probability_distribution: Dict[str, float] = field(default_factory=dict)
    multi_step_paths: List[List[Tuple[str, float]]] = field(default_factory=list)

    def is_correct_top_k(self, actual_target: str, k: Optional[int] = None) -> bool:
        """Check if actual target appears within top-k candidates."""
        candidates = self.top_k if k is None else self.top_k[:k]
        return any(c.item_id == actual_target for c in candidates)
