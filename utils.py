"""
utils.py — Shared constants and helper functions for the mobile memory simulation.
"""

# ── App definitions ──────────────────────────────────────────────────────────

APPS = ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"]

# Realistic base RAM usage per app (MB)
APP_RAM_USAGE = {
    "Chrome":    1200,
    "YouTube":   900,
    "Spotify":   600,
    "Gemini":    800,
    "WhatsApp":  500,
}

# Compressed RAM usage (when app state = COMPRESSED)
COMPRESSED_RAM_FACTOR = 0.35

# System-wide RAM limit (MB) — tight enough to force evictions with 5 apps
RAM_LIMIT = 2500

# Launch time by cache state (seconds)
LAUNCH_TIME = {
    "ACTIVE":     0.3,
    "CACHED":     0.8,
    "COMPRESSED": 1.5,
    "EVICTED":    2.5,
}

# Cache states ordered from best to worst
CACHE_STATES = ["ACTIVE", "CACHED", "COMPRESSED", "EVICTED"]

# ── Priority score weights ──────────────────────────────────────────────────

WEIGHT_FOREGROUND  = 0.4
WEIGHT_PREDICTION  = 0.3
WEIGHT_FREQUENCY   = 0.2
WEIGHT_RECENCY     = 0.1

# ── Allocation thresholds ──────────────────────────────────────────────────

HIGH_PRIORITY_THRESH   = 0.8
MED_PRIORITY_THRESH    = 0.5

# Allocation memory tiers (MB)
HIGH_ALLOC   = 900
MED_ALLOC    = 500
LOW_ALLOC    = 200

# ── Lifecycle engine constants ─────────────────────────────────────────────

# Memory pressure thresholds (fraction of RAM_LIMIT)
PRESSURE_LOW       = 0.55
PRESSURE_MEDIUM    = 0.75
PRESSURE_HIGH      = 0.90

# Rolling window size for memory pressure trend (events)
PRESSURE_WINDOW    = 15

# Hysteresis: minimum ticks an app must stay in a state before demotion
MIN_STATE_TICKS    = 5

# Telemetry: rolling window for access-interval stats
TELEMETRY_WINDOW   = 20

# Burst detection: threshold for burst_score to trigger pre-warm
BURST_THRESHOLD    = 0.4

# Preemptive compression: promote to COMPRESSED when pressure rising
# and app priority below this value
PREEMPTIVE_COMPRESS_PRIORITY = 0.35


def normalize(value: float, max_val: float) -> float:
    """Normalize a value to [0, 1]. Avoid division by zero."""
    if max_val == 0:
        return 0.0
    return min(value / max_val, 1.0)
