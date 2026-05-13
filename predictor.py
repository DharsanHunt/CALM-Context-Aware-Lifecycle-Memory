"""
predictor.py — Markov-chain based next-app predictor with confidence scoring.
"""

import pandas as pd

from utils import APPS


class MarkovPredictor:
    """
    Learns app-switch transition probabilities from usage logs
    and predicts the most likely next app(s).

    Enhanced with:
      • Confidence scoring (how certain is the prediction?)
      • Multi-step lookahead (top-N predictions)
      • Entropy-based uncertainty measurement
    """

    def __init__(self):
        self.transition_counts: dict[str, dict[str, int]] = {}
        self.transition_probs: dict[str, dict[str, float]] = {}
        self.is_trained = False

    def train_transition_matrix(self, logs: pd.DataFrame) -> None:
        """
        Build transition count matrix from consecutive app switches,
        then convert to probability matrix.
        """
        apps = logs["app"].tolist()

        for i in range(len(apps) - 1):
            src, dst = apps[i], apps[i + 1]
            if src not in self.transition_counts:
                self.transition_counts[src] = {}
            self.transition_counts[src][dst] = self.transition_counts[src].get(dst, 0) + 1

        for src, destinations in self.transition_counts.items():
            total = sum(destinations.values())
            self.transition_probs[src] = {
                dst: count / total for dst, count in destinations.items()
            }

        for app in APPS:
            if app not in self.transition_probs:
                self.transition_probs[app] = {a: 1 / len(APPS) for a in APPS}

        self.is_trained = True

    def get_transition_probabilities(self, current_app: str) -> dict[str, float]:
        """Return full probability distribution for next app given current app."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train_transition_matrix() first.")
        probs = self.transition_probs.get(current_app, {})
        return {app: probs.get(app, 0.0) for app in APPS}

    def predict_next_app(self, current_app: str) -> str:
        """Return the single most likely next app."""
        probs = self.get_transition_probabilities(current_app)
        return max(probs, key=probs.get)

    def predict_top_n(self, current_app: str, n: int = 3) -> list[tuple[str, float]]:
        """
        Return the top-N most likely next apps with probabilities.
        Useful for pre-warming multiple candidates.
        """
        probs = self.get_transition_probabilities(current_app)
        ranked = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        return ranked[:n]

    def get_prediction_score(self, current_app: str, target_app: str) -> float:
        """Return probability that target_app is the next switch from current_app."""
        probs = self.get_transition_probabilities(current_app)
        return probs.get(target_app, 0.0)

    def get_confidence(self, current_app: str) -> float:
        """
        How confident is the prediction? Returns 0–1.
        High confidence = one app dominates the probability distribution.
        Low confidence = probabilities are spread evenly.

        Computed as: 1 - normalized_entropy.
        """
        import math

        probs = self.get_transition_probabilities(current_app)
        n = len(probs)
        if n <= 1:
            return 1.0

        entropy = 0.0
        for p in probs.values():
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(n)
        if max_entropy == 0:
            return 1.0

        return 1.0 - (entropy / max_entropy)
