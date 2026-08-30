"""
calm.prediction.predictor — Abstract predictor interface and baseline statistical predictors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from collections import Counter

from calm.models.prediction import PredictionResult, PredictionCandidate


class BasePredictor(ABC):
    """Abstract base class for all next-item predictors."""

    @abstractmethod
    def fit(self, sequence: List[str], all_items: Optional[List[str]] = None) -> None:
        """Fit the predictor on historical usage sequence."""
        pass

    @abstractmethod
    def predict(self, current_item: str, top_k: int = 3) -> PredictionResult:
        """Infers the next item and returns a structured PredictionResult."""
        pass

    @abstractmethod
    def get_transition_probabilities(self, current_item: str) -> Dict[str, float]:
        """Returns the full probability distribution over next items."""
        pass


class UniformPredictor(BasePredictor):
    """Baseline uniform random predictor (1/N probability for all items)."""

    def __init__(self):
        self.all_items: List[str] = []

    def fit(self, sequence: List[str], all_items: Optional[List[str]] = None) -> None:
        if all_items:
            self.all_items = list(all_items)
        else:
            self.all_items = sorted(list(set(sequence)))

    def get_transition_probabilities(self, current_item: str) -> Dict[str, float]:
        if not self.all_items:
            return {}
        p = 1.0 / len(self.all_items)
        return {item: p for item in self.all_items}

    def predict(self, current_item: str, top_k: int = 3) -> PredictionResult:
        probs = self.get_transition_probabilities(current_item)
        top_1 = self.all_items[0] if self.all_items else current_item
        candidates = [
            PredictionCandidate(item_id=item, probability=probs[item], rank=i + 1)
            for i, item in enumerate(self.all_items[:top_k])
        ]
        return PredictionResult(
            source_item=current_item,
            top_1=top_1,
            top_k=candidates,
            confidence=0.0,
            entropy=1.0,
            probability_distribution=probs,
        )


class FrequencyPredictor(BasePredictor):
    """Predicts next item purely based on static unigram frequency in training data."""

    def __init__(self):
        self.all_items: List[str] = []
        self.probs: Dict[str, float] = {}

    def fit(self, sequence: List[str], all_items: Optional[List[str]] = None) -> None:
        self.all_items = list(all_items) if all_items else sorted(list(set(sequence)))
        counts = Counter(sequence)
        total = sum(counts.values()) or 1
        self.probs = {item: counts.get(item, 0) / total for item in self.all_items}

    def get_transition_probabilities(self, current_item: str) -> Dict[str, float]:
        return dict(self.probs)

    def predict(self, current_item: str, top_k: int = 3) -> PredictionResult:
        probs = self.get_transition_probabilities(current_item)
        sorted_items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top_1 = sorted_items[0][0] if sorted_items else current_item
        candidates = [
            PredictionCandidate(item_id=item, probability=prob, rank=i + 1)
            for i, (item, prob) in enumerate(sorted_items[:top_k])
        ]
        return PredictionResult(
            source_item=current_item,
            top_1=top_1,
            top_k=candidates,
            confidence=sorted_items[0][1] if sorted_items else 0.0,
            entropy=0.5,
            probability_distribution=probs,
        )
