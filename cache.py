"""
cache.py — Multi-tiered lifecycle management engine.

Instead of simple state + eviction, apps flow through a 4-tier lifecycle:
    ACTIVE  →  CACHED  →  COMPRESSED  →  EVICTED

Key design principle: KEEP apps in cache as long as possible.
Only demote when the hard RAM limit is actually exceeded.
Pre-warm predicted apps to COMPRESSED state for fast access.

All RAM values are read from a SystemConfig instance (config.py).
"""

from collections import deque

from utils import (
    APPS,
    PRESSURE_LOW, PRESSURE_MEDIUM, PRESSURE_HIGH,
    PRESSURE_WINDOW, MIN_STATE_TICKS, TELEMETRY_WINDOW,
    BURST_THRESHOLD,
)
from config import SystemConfig


# ── Per-App Telemetry ──────────────────────────────────────────────────────

class AppTelemetry:
    """Tracks real-time usage signals for a single app."""

    def __init__(self):
        self.access_count: int = 0
        self.last_access_tick: int = -999
        self.ticks_in_state: int = 0
        self.access_intervals: deque = deque(maxlen=TELEMETRY_WINDOW)
        self._prev_access_tick: int = -999

    def record_access(self, tick: int) -> None:
        if self.last_access_tick > -999:
            gap = tick - self.last_access_tick
            self.access_intervals.append(gap)
        self._prev_access_tick = self.last_access_tick
        self.last_access_tick = tick
        self.access_count += 1

    def tick(self) -> None:
        self.ticks_in_state += 1

    def reset_state_timer(self) -> None:
        self.ticks_in_state = 0

    @property
    def avg_interval(self) -> float:
        if not self.access_intervals:
            return 999.0
        return sum(self.access_intervals) / len(self.access_intervals)

    @property
    def burst_score(self) -> float:
        if len(self.access_intervals) < 2:
            return 0.0
        recent = list(self.access_intervals)
        last_two = sum(recent[-2:]) / 2
        overall = sum(recent) / len(recent)
        if overall == 0:
            return 0.0
        ratio = overall / (last_two + 0.1)
        return min(ratio / 3.0, 1.0)

    @property
    def can_demote(self) -> bool:
        return self.ticks_in_state >= MIN_STATE_TICKS


# ── Memory Pressure Tracker ───────────────────────────────────────────────

class MemoryPressure:
    """Tracks system-wide memory pressure as a fraction of ram_limit."""

    def __init__(self, ram_limit: int):
        self.ram_limit = ram_limit
        self.history: deque = deque(maxlen=PRESSURE_WINDOW)
        self.current: float = 0.0
        self.trend: float = 0.0

    def update(self, used_ram: int) -> None:
        self.current = used_ram / self.ram_limit if self.ram_limit else 0.0
        self.history.append(self.current)
        if len(self.history) >= 3:
            recent = list(self.history)
            first_half = sum(recent[:len(recent) // 2]) / (len(recent) // 2)
            second_half = sum(recent[len(recent) // 2:]) / (len(recent) - len(recent) // 2)
            self.trend = second_half - first_half
        else:
            self.trend = 0.0

    @property
    def level(self) -> str:
        if self.current < PRESSURE_LOW:
            return "LOW"
        elif self.current < PRESSURE_MEDIUM:
            return "MEDIUM"
        elif self.current < PRESSURE_HIGH:
            return "HIGH"
        return "CRITICAL"

    @property
    def is_rising(self) -> bool:
        return self.trend > 0.02

    @property
    def is_falling(self) -> bool:
        return self.trend < -0.02


# ── Lifecycle Engine ───────────────────────────────────────────────────────

class LifecycleEngine:
    """
    Manages the full lifecycle of all apps through 4 states:
        ACTIVE → CACHED → COMPRESSED → EVICTED

    Design philosophy: CONSERVATIVE demotion, AGGRESSIVE pre-warming.
    Only demote when the hard RAM limit is actually exceeded.
    Pre-warm top-N predicted apps to COMPRESSED for fast access.
    """

    _PROMOTE = {"EVICTED": "COMPRESSED", "COMPRESSED": "CACHED", "CACHED": "ACTIVE"}
    _DEMOTE  = {"ACTIVE": "CACHED", "CACHED": "COMPRESSED", "COMPRESSED": "EVICTED"}

    def __init__(self, config: SystemConfig):
        self.config = config
        self.app_state: dict[str, str] = {app: "EVICTED" for app in APPS}
        self.app_ram: dict[str, int] = {app: 0 for app in APPS}
        self.telemetry: dict[str, AppTelemetry] = {app: AppTelemetry() for app in APPS}
        self.pressure = MemoryPressure(config.ram_limit)
        self.tick: int = 0
        self.transition_log: list[dict] = []

    # ── RAM helpers ────────────────────────────────────────────────────────

    def _effective_ram(self, app: str, state: str) -> int:
        return self.config.effective_ram(app, state)

    def total_ram(self) -> int:
        return sum(self.app_ram.values())

    def _apply_state(self, app: str, new_state: str) -> None:
        old = self.app_state[app]
        if old == new_state:
            return
        self.app_state[app] = new_state
        self.app_ram[app] = self._effective_ram(app, new_state)
        self.telemetry[app].reset_state_timer()
        self.transition_log.append({
            "tick": self.tick, "app": app, "from": old, "to": new_state
        })

    # ── State helpers ──────────────────────────────────────────────────────

    def _promote(self, app: str) -> None:
        nxt = self._PROMOTE.get(self.app_state[app])
        if nxt:
            self._apply_state(app, nxt)

    def _demote(self, app: str) -> None:
        nxt = self._DEMOTE.get(self.app_state[app])
        if nxt:
            self._apply_state(app, nxt)

    # ── Core update cycle ──────────────────────────────────────────────────

    def update(
        self,
        foreground_app: str,
        priority_scores: dict[str, float],
        predicted_app: str | None = None,
        prediction_scores: dict[str, float] | None = None,
    ) -> dict[str, str]:
        """
        Full lifecycle update for one simulation tick.

        Strategy:
          1. Record telemetry.
          2. Pre-warm top-3 predicted apps to COMPRESSED (cheap, keeps them ready).
          3. Promote foreground to ACTIVE.
          4. ONLY if over RAM limit: demote lowest-priority apps.
          5. Downgrade stale ACTIVE → CACHED (only foreground stays ACTIVE).
        """
        self.tick += 1
        pred_scores = prediction_scores or {}

        # 1. Record foreground access
        self.telemetry[foreground_app].record_access(self.tick)
        for app in APPS:
            self.telemetry[app].tick()

        # 2. Update pressure
        self.pressure.update(self.total_ram())

        # 3. Pre-warm predicted apps to COMPRESSED (cheap — uses ~35% RAM)
        #    This ensures predicted apps are at least partially cached
        if predicted_app and predicted_app != foreground_app:
            pred_score = pred_scores.get(predicted_app, 0.0)
            if pred_score > 0.15:
                # Promote from EVICTED → COMPRESSED if needed
                if self.app_state[predicted_app] == "EVICTED":
                    self._apply_state(predicted_app, "COMPRESSED")
                # If prediction is strong, promote further
                if pred_score > 0.35:
                    self._promote(predicted_app)

        # 4. Promote foreground to ACTIVE
        self._apply_state(foreground_app, "ACTIVE")

        # 5. ONLY enforce RAM limit when actually exceeded
        #    No speculative/proactive demotion — keep apps cached as long as possible
        if self.total_ram() > self.config.ram_limit:
            self._enforce_ram_limit(foreground_app, priority_scores)

        # 6. Downgrade non-foreground ACTIVE apps to CACHED
        for app in APPS:
            if app != foreground_app and self.app_state[app] == "ACTIVE":
                self._apply_state(app, "CACHED")

        # 7. Final pressure snapshot
        self.pressure.update(self.total_ram())
        return dict(self.app_state)

    # ── Hard limit enforcement ─────────────────────────────────────────────

    def _enforce_ram_limit(self, foreground, priority_scores):
        """Downgrade apps until total RAM <= RAM_LIMIT. Conservative: one step at a time."""
        protect = {foreground}
        attempts = 0
        while self.total_ram() > self.config.ram_limit and attempts < 30:
            if not self._demote_lowest_priority(priority_scores, protect):
                break
            attempts += 1

    def _demote_lowest_priority(self, priority_scores, exclude):
        """Demote the lowest-priority app that isn't protected. One step only."""
        candidates = [
            app for app in APPS
            if app not in exclude and self.app_state[app] != "EVICTED"
        ]
        if not candidates:
            return False

        # Sort by: lowest priority first, then highest state first (demote biggest consumers)
        state_rank = {"COMPRESSED": 0, "CACHED": 1, "ACTIVE": 2}
        candidates.sort(
            key=lambda a: (
                priority_scores.get(a, 0) - state_rank.get(self.app_state[a], 0) * 0.1,
            )
        )
        self._demote(candidates[0])
        return True

    # ── Backwards-compatible aliases ────────────────────────────────────────

    def activate_app(self, app: str) -> None:
        self._apply_state(app, "ACTIVE")

    def set_state(self, app: str, state: str) -> None:
        self._apply_state(app, state)

    def get_state_table(self) -> list[dict]:
        rows = []
        for app in APPS:
            tel = self.telemetry[app]
            rows.append({
                "App": app,
                "State": self.app_state[app],
                "RAM (MB)": self.app_ram[app],
                "Accesses": tel.access_count,
                "Burst Score": round(tel.burst_score, 2),
                "Ticks in State": tel.ticks_in_state,
            })
        return rows


# ── Simple Baseline Cache Manager (reactive, no telemetry) ───────────────

class CacheManager:
    """
    Simple reactive cache manager for baseline comparison.
    No telemetry, no prediction, no proactive demotion.
    All RAM values from SystemConfig.
    """

    def __init__(self, config: SystemConfig):
        self.config = config
        self.app_state: dict[str, str] = {app: "EVICTED" for app in APPS}
        self.app_ram: dict[str, int] = {app: 0 for app in APPS}

    def _effective_ram(self, app: str, state: str) -> int:
        return self.config.effective_ram(app, state)

    def total_ram(self) -> int:
        return sum(self.app_ram.values())

    def set_state(self, app: str, state: str) -> None:
        self.app_state[app] = state
        self.app_ram[app] = self._effective_ram(app, state)

    def activate_app(self, app: str) -> None:
        self.set_state(app, "ACTIVE")

    def _evict_lowest_priority(self, priority_scores, exclude):
        candidates = [
            (app, self.app_state[app])
            for app in APPS
            if app not in exclude and self.app_state[app] != "EVICTED"
        ]
        if not candidates:
            return False
        state_order = {"COMPRESSED": 0, "CACHED": 1, "ACTIVE": 2}
        candidates.sort(key=lambda x: (priority_scores.get(x[0], 0), state_order.get(x[1], 0)))
        target = candidates[0][0]
        current = self.app_state[target]
        if current == "ACTIVE":
            self.set_state(target, "CACHED")
        elif current == "CACHED":
            self.set_state(target, "COMPRESSED")
        else:
            self.set_state(target, "EVICTED")
        return True

    def enforce_ram_limit(self, priority_scores, foreground_app):
        protect = {foreground_app}
        attempts = 0
        while self.total_ram() > self.config.ram_limit and attempts < 20:
            if not self._evict_lowest_priority(priority_scores, protect):
                break
            attempts += 1
