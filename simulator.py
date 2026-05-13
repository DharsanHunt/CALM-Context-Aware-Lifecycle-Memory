"""
simulator.py — Generate realistic mobile app usage logs using weighted transitions.
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from utils import APPS, APP_RAM_USAGE, CACHE_STATES

# ── Transition probability matrix (hand-tuned for realism) ───────────────────
# Each row maps current_app → {next_app: probability}
# Chrome users often switch to YouTube; Spotify users often stay or go to WhatsApp, etc.

TRANSITION_MAP = {
    "Chrome":   {"YouTube": 0.45, "Gemini": 0.25, "WhatsApp": 0.15, "Spotify": 0.10, "Chrome": 0.05},
    "YouTube":  {"Chrome": 0.30, "Spotify": 0.30, "WhatsApp": 0.20, "Gemini": 0.10, "YouTube": 0.10},
    "Spotify":  {"YouTube": 0.25, "WhatsApp": 0.25, "Chrome": 0.20, "Gemini": 0.15, "Spotify": 0.15},
    "Gemini":   {"Chrome": 0.35, "YouTube": 0.25, "WhatsApp": 0.20, "Spotify": 0.10, "Gemini": 0.10},
    "WhatsApp": {"Chrome": 0.30, "YouTube": 0.25, "Spotify": 0.20, "Gemini": 0.15, "WhatsApp": 0.10},
}


def _pick_next(current_app: str) -> str:
    """Choose next app based on weighted transition probabilities."""
    targets = TRANSITION_MAP[current_app]
    apps = list(targets.keys())
    weights = list(targets.values())
    return random.choices(apps, weights=weights, k=1)[0]


def _random_cache_state() -> str:
    """Assign a cache state with realistic distribution."""
    return random.choices(
        CACHE_STATES,
        weights=[0.15, 0.40, 0.25, 0.20],
        k=1,
    )[0]


def generate_usage_logs(num_events: int = 350, seed: int = 42) -> pd.DataFrame:
    """
    Generate a sequence of app usage events.

    Each event:
        timestamp, app, ram_mb, cache_state

    Returns:
        DataFrame with num_events rows.
    """
    random.seed(seed)

    records = []
    current_app = random.choice(APPS)
    ts = datetime(2026, 5, 12, 8, 0, 0)  # start at 8 AM

    for i in range(num_events):
        ram = APP_RAM_USAGE[current_app] + random.randint(-80, 80)
        cache = _random_cache_state()

        records.append({
            "event_id":    i,
            "timestamp":   ts.strftime("%Y-%m-%d %H:%M:%S"),
            "app":         current_app,
            "ram_mb":      max(200, ram),
            "cache_state": cache,
        })

        # Advance time: 1–4 minutes between switches
        ts += timedelta(seconds=random.randint(60, 240))
        current_app = _pick_next(current_app)

    df = pd.DataFrame(records)
    df.to_csv("data/usage_logs.csv", index=False)
    return df


if __name__ == "__main__":
    df = generate_usage_logs()
    print(f"Generated {len(df)} events → data/usage_logs.csv")
    print(df.head(10))
