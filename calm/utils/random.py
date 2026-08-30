"""
Reproducibility and random seeding utilities.
"""

import random
import numpy as np


def set_seed(seed: int = 42) -> None:
    """Set seeds across Python's random and NumPy for deterministic reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
