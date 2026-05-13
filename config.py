"""
config.py — System configuration with aggression presets and per-app overrides.

All RAM-related values flow from a single SystemConfig instance.
Presets act as "default value generators" — selecting one populates the
sidebar inputs, but the user can manually override any field afterward.
"""

from dataclasses import dataclass, field

from utils import APPS


# ── Default per-app RAM usage (realistic mobile values, MB) ──────────────────

DEFAULT_APP_RAM = {
    "Chrome":    1200,
    "YouTube":   900,
    "Spotify":   600,
    "Gemini":    800,
    "WhatsApp":  500,
}


@dataclass
class SystemConfig:
    """
    Single source of truth for all memory parameters.
    Every module reads from an instance of this class instead of globals.
    """
    ram_limit: int = 2500
    app_ram: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_APP_RAM))
    compressed_ram_factor: float = 0.35
    aggression: str = "Less Aggressive"

    @property
    def total_app_ram(self) -> int:
        return sum(self.app_ram.values())

    @property
    def pressure_ratio(self) -> float:
        """How tight is the budget? >1.0 means apps exceed limit."""
        return self.total_app_ram / self.ram_limit if self.ram_limit else 0

    def effective_ram(self, app: str, state: str) -> int:
        """RAM consumed by an app in a given cache state."""
        base = self.app_ram.get(app, 500)
        if state in ("ACTIVE", "CACHED"):
            return base
        elif state == "COMPRESSED":
            return int(base * self.compressed_ram_factor)
        return 0

    def to_dict(self) -> dict:
        return {
            "ram_limit": self.ram_limit,
            "app_ram": dict(self.app_ram),
            "compressed_ram_factor": self.compressed_ram_factor,
            "aggression": self.aggression,
        }


# ── Aggression Presets ───────────────────────────────────────────────────────
#
# Each preset returns a dict of "suggested values" that populate the sidebar.
# The user can override any value after selecting a preset.
#
# Logic:
#   No Aggression   → generous system RAM, low per-app restrictions
#   Less Aggressive → moderate constraints, prevent bloat
#   Aggressive      → strict limits, prioritize system stability
#   Critical        → minimal footprint, maximum system overhead

_PRESETS = {
    "No Aggression": {
        "ram_limit": 6000,
        "app_ram": {
            "Chrome":    1400,
            "YouTube":   1100,
            "Spotify":   800,
            "Gemini":    1000,
            "WhatsApp":  700,
        },
        "compressed_ram_factor": 0.45,
    },
    "Less Aggressive": {
        "ram_limit": 3500,
        "app_ram": {
            "Chrome":    1200,
            "YouTube":   900,
            "Spotify":   600,
            "Gemini":    800,
            "WhatsApp":  500,
        },
        "compressed_ram_factor": 0.35,
    },
    "Aggressive": {
        "ram_limit": 2000,
        "app_ram": {
            "Chrome":    800,
            "YouTube":   600,
            "Spotify":   400,
            "Gemini":    550,
            "WhatsApp":  350,
        },
        "compressed_ram_factor": 0.25,
    },
    "Critical": {
        "ram_limit": 1200,
        "app_ram": {
            "Chrome":    400,
            "YouTube":   300,
            "Spotify":   200,
            "Gemini":    275,
            "WhatsApp":  175,
        },
        "compressed_ram_factor": 0.15,
    },
}

PRESET_NAMES = list(_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return the raw preset dict for a given aggression level."""
    return _PRESETS.get(name, _PRESETS["Less Aggressive"])


def build_config(
    ram_limit: int,
    app_ram: dict[str, int],
    compressed_ram_factor: float,
    aggression: str,
) -> SystemConfig:
    """Construct a SystemConfig from sidebar values."""
    return SystemConfig(
        ram_limit=ram_limit,
        app_ram={app: app_ram.get(app, DEFAULT_APP_RAM[app]) for app in APPS},
        compressed_ram_factor=compressed_ram_factor,
        aggression=aggression,
    )
