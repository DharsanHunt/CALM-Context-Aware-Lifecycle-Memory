"""
calm.utils.config — Centralized system configuration for CALM V2.
Encapsulates all weights, thresholds, memory budgets, and aggression presets.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict


# Default mobile application list and RAM allocations in MB
DEFAULT_APPS = ["Chrome", "YouTube", "Spotify", "Gemini", "WhatsApp"]

DEFAULT_APP_RAM: Dict[str, int] = {
    "Chrome": 1200,
    "YouTube": 900,
    "Spotify": 600,
    "Gemini": 800,
    "WhatsApp": 500,
}

# Retrieval / launch latency costs (in seconds)
DEFAULT_LAUNCH_TIMES: Dict[str, float] = {
    "ACTIVE": 0.05,
    "CACHED": 0.40,
    "COMPRESSED": 1.10,
    "ARCHIVED": 2.40,
}


@dataclass
class PriorityWeights:
    """Configurable weights for the CALM Priority Function."""
    foreground: float = 0.25
    prediction: float = 0.25
    recency: float = 0.15
    frequency: float = 0.15
    burst: float = 0.10
    context_importance: float = 0.10
    memory_cost: float = 0.05

    def validate(self) -> None:
        positive_sum = (
            self.foreground
            + self.prediction
            + self.recency
            + self.frequency
            + self.burst
            + self.context_importance
        )
        if positive_sum <= 0:
            raise ValueError(f"Sum of positive priority weights must be positive, got {positive_sum}")


@dataclass
class PressureThresholds:
    """Memory pressure levels and trend tracking configuration."""
    low: float = 0.55
    moderate: float = 0.75
    high: float = 0.88
    critical: float = 0.95
    rolling_window: int = 15
    rising_slope_threshold: float = 0.015
    falling_slope_threshold: float = -0.015


@dataclass
class HysteresisConfig:
    """Hysteresis parameters to prevent oscillation and thrashing."""
    min_state_ticks: int = 3
    promote_threshold: float = 0.18
    demote_threshold: float = 0.25
    cooldown_ticks: int = 2


@dataclass
class PredictionConfig:
    """Prediction engine parameters."""
    top_k: int = 3
    confidence_threshold: float = 0.45
    high_confidence_threshold: float = 0.70
    smoothing_alpha: float = 0.05
    multi_step_horizon: int = 2


@dataclass
class StorageConfig:
    """Storage and compression parameters."""
    compressed_ram_factor: float = 0.35  # Simulated factor for mobile apps
    compression_algorithm: str = "zlib"   # Real algorithm for agent memory
    compression_level: int = 6


@dataclass
class CALMConfig:
    """
    Master configuration for CALM V2.
    Single source of truth for all memory budgets, policies, and parameters.
    """
    mode: str = "mobile"  # "mobile" or "agent"
    ram_limit_mb: int = 2500
    app_ram: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_APP_RAM))
    launch_times: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_LAUNCH_TIMES))
    
    priority_weights: PriorityWeights = field(default_factory=PriorityWeights)
    pressure: PressureThresholds = field(default_factory=PressureThresholds)
    hysteresis: HysteresisConfig = field(default_factory=HysteresisConfig)
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    aggression: str = "Less Aggressive"

    @property
    def total_app_ram(self) -> int:
        return sum(self.app_ram.values())

    @property
    def pressure_ratio(self) -> float:
        return self.total_app_ram / self.ram_limit_mb if self.ram_limit_mb > 0 else 0.0

    def effective_ram(self, item_id: str, state: str) -> int:
        """Calculate effective RAM used by an item in a given state."""
        base = self.app_ram.get(item_id, 500)
        if state in ("ACTIVE", "CACHED"):
            return base
        elif state == "COMPRESSED":
            return int(base * self.storage.compressed_ram_factor)
        elif state == "ARCHIVED":
            return 0
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CALMConfig":
        data_copy = dict(data)
        if "priority_weights" in data_copy and isinstance(data_copy["priority_weights"], dict):
            data_copy["priority_weights"] = PriorityWeights(**data_copy["priority_weights"])
        if "pressure" in data_copy and isinstance(data_copy["pressure"], dict):
            data_copy["pressure"] = PressureThresholds(**data_copy["pressure"])
        if "hysteresis" in data_copy and isinstance(data_copy["hysteresis"], dict):
            data_copy["hysteresis"] = HysteresisConfig(**data_copy["hysteresis"])
        if "prediction" in data_copy and isinstance(data_copy["prediction"], dict):
            data_copy["prediction"] = PredictionConfig(**data_copy["prediction"])
        if "storage" in data_copy and isinstance(data_copy["storage"], dict):
            data_copy["storage"] = StorageConfig(**data_copy["storage"])
        return cls(**data_copy)


# ── Presets ──────────────────────────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, Any]] = {
    "No Aggression": {
        "ram_limit_mb": 6000,
        "app_ram": {
            "Chrome": 1400,
            "YouTube": 1100,
            "Spotify": 800,
            "Gemini": 1000,
            "WhatsApp": 700,
        },
        "storage": StorageConfig(compressed_ram_factor=0.45),
        "aggression": "No Aggression",
    },
    "Less Aggressive": {
        "ram_limit_mb": 3500,
        "app_ram": {
            "Chrome": 1200,
            "YouTube": 900,
            "Spotify": 600,
            "Gemini": 800,
            "WhatsApp": 500,
        },
        "storage": StorageConfig(compressed_ram_factor=0.35),
        "aggression": "Less Aggressive",
    },
    "Aggressive": {
        "ram_limit_mb": 2000,
        "app_ram": {
            "Chrome": 800,
            "YouTube": 600,
            "Spotify": 400,
            "Gemini": 550,
            "WhatsApp": 350,
        },
        "storage": StorageConfig(compressed_ram_factor=0.25),
        "aggression": "Aggressive",
    },
    "Critical": {
        "ram_limit_mb": 1200,
        "app_ram": {
            "Chrome": 400,
            "YouTube": 300,
            "Spotify": 200,
            "Gemini": 275,
            "WhatsApp": 175,
        },
        "storage": StorageConfig(compressed_ram_factor=0.15),
        "aggression": "Critical",
    },
}

PRESET_NAMES = list(PRESETS.keys())


def get_preset_config(name: str) -> CALMConfig:
    preset_data = PRESETS.get(name, PRESETS["Less Aggressive"])
    cfg = CALMConfig(
        ram_limit_mb=preset_data["ram_limit_mb"],
        app_ram=dict(preset_data["app_ram"]),
        storage=preset_data.get("storage", StorageConfig()),
        aggression=name,
    )
    return cfg
