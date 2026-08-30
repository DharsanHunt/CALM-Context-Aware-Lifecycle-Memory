"""
calm.telemetry.workload — Synthetic & realistic workload generation with temporal splitting.
Supports 7 distinct workload archetypes:
1. Predictable
2. Random
3. Bursty
4. Productivity
5. SocialMedia
6. ContextSwitching
7. Adversarial
"""

import json
import random
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

from calm.utils.config import DEFAULT_APPS, DEFAULT_APP_RAM


class WorkloadType(str, Enum):
    PREDICTABLE = "predictable"
    RANDOM = "random"
    BURSTY = "bursty"
    PRODUCTIVITY = "productivity"
    SOCIAL_MEDIA = "social_media"
    CONTEXT_SWITCHING = "context_switching"
    ADVERSARIAL = "adversarial"


@dataclass
class WorkloadEvent:
    """Individual access event in a workload sequence."""
    tick: int
    timestamp: str
    item_id: str
    ram_mb: int
    context_type: str = "APP"
    importance: float = 0.5


@dataclass
class WorkloadSequence:
    """A complete sequence of workload access events with metadata."""
    name: str
    workload_type: WorkloadType
    seed: int
    num_events: int
    events: List[WorkloadEvent]
    items: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "workload_type": self.workload_type.value,
            "seed": self.seed,
            "num_events": self.num_events,
            "items": self.items,
            "events": [asdict(e) for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkloadSequence":
        events = [WorkloadEvent(**e) for e in data["events"]]
        return cls(
            name=data["name"],
            workload_type=WorkloadType(data["workload_type"]),
            seed=data["seed"],
            num_events=data["num_events"],
            events=events,
            items=data["items"],
        )

    def to_item_sequence(self) -> List[str]:
        return [e.item_id for e in self.events]


def temporal_split(
    sequence: WorkloadSequence,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[WorkloadSequence, WorkloadSequence, WorkloadSequence]:
    """
    Performs strict temporal splitting with zero future data leakage.
    Returns (train_sequence, val_sequence, test_sequence).
    """
    total = len(sequence.events)
    train_end = int(total * train_ratio)
    val_end = int(total * (train_ratio + val_ratio))

    train_events = sequence.events[:train_end]
    val_events = sequence.events[train_end:val_end]
    test_events = sequence.events[val_end:]

    train_seq = WorkloadSequence(
        name=f"{sequence.name}_train",
        workload_type=sequence.workload_type,
        seed=sequence.seed,
        num_events=len(train_events),
        events=train_events,
        items=sequence.items,
    )
    val_seq = WorkloadSequence(
        name=f"{sequence.name}_val",
        workload_type=sequence.workload_type,
        seed=sequence.seed,
        num_events=len(val_events),
        events=val_events,
        items=sequence.items,
    )
    test_seq = WorkloadSequence(
        name=f"{sequence.name}_test",
        workload_type=sequence.workload_type,
        seed=sequence.seed,
        num_events=len(test_events),
        events=test_events,
        items=sequence.items,
    )
    return train_seq, val_seq, test_seq


class WorkloadGenerator:
    """
    Generates deterministic workloads for the 7 standard archetypes.
    """

    TRANSITION_MATRICES: Dict[WorkloadType, Dict[str, Dict[str, float]]] = {
        WorkloadType.PREDICTABLE: {
            "Chrome":   {"YouTube": 0.65, "Gemini": 0.20, "WhatsApp": 0.05, "Spotify": 0.05, "Chrome": 0.05},
            "YouTube":  {"Spotify": 0.60, "Chrome": 0.20, "WhatsApp": 0.10, "Gemini": 0.05, "YouTube": 0.05},
            "Spotify":  {"WhatsApp": 0.60, "Chrome": 0.15, "YouTube": 0.15, "Gemini": 0.05, "Spotify": 0.05},
            "WhatsApp": {"Gemini": 0.60, "Chrome": 0.20, "YouTube": 0.10, "Spotify": 0.05, "WhatsApp": 0.05},
            "Gemini":   {"Chrome": 0.65, "YouTube": 0.15, "WhatsApp": 0.10, "Spotify": 0.05, "Gemini": 0.05},
        },
        WorkloadType.RANDOM: {
            app: {other: 0.20 for other in DEFAULT_APPS} for app in DEFAULT_APPS
        },
        WorkloadType.BURSTY: {
            "Chrome":   {"Chrome": 0.60, "YouTube": 0.20, "Gemini": 0.10, "WhatsApp": 0.05, "Spotify": 0.05},
            "YouTube":  {"YouTube": 0.60, "Chrome": 0.20, "Spotify": 0.10, "WhatsApp": 0.05, "Gemini": 0.05},
            "Spotify":  {"Spotify": 0.60, "WhatsApp": 0.20, "YouTube": 0.10, "Chrome": 0.05, "Gemini": 0.05},
            "WhatsApp": {"WhatsApp": 0.60, "Gemini": 0.20, "Chrome": 0.10, "Spotify": 0.05, "YouTube": 0.05},
            "Gemini":   {"Gemini": 0.60, "Chrome": 0.20, "WhatsApp": 0.10, "YouTube": 0.05, "Spotify": 0.05},
        },
        WorkloadType.PRODUCTIVITY: {
            "Chrome":   {"Gemini": 0.50, "WhatsApp": 0.25, "Spotify": 0.15, "YouTube": 0.05, "Chrome": 0.05},
            "Gemini":   {"Chrome": 0.55, "WhatsApp": 0.25, "Spotify": 0.10, "YouTube": 0.05, "Gemini": 0.05},
            "WhatsApp": {"Chrome": 0.40, "Gemini": 0.40, "Spotify": 0.10, "YouTube": 0.05, "WhatsApp": 0.05},
            "Spotify":  {"Chrome": 0.35, "Gemini": 0.35, "WhatsApp": 0.20, "YouTube": 0.05, "Spotify": 0.05},
            "YouTube":  {"Chrome": 0.40, "Gemini": 0.40, "Spotify": 0.10, "WhatsApp": 0.05, "YouTube": 0.05},
        },
        WorkloadType.SOCIAL_MEDIA: {
            "WhatsApp": {"YouTube": 0.45, "Spotify": 0.30, "Chrome": 0.15, "Gemini": 0.05, "WhatsApp": 0.05},
            "YouTube":  {"WhatsApp": 0.45, "Spotify": 0.30, "Chrome": 0.15, "Gemini": 0.05, "YouTube": 0.05},
            "Spotify":  {"WhatsApp": 0.45, "YouTube": 0.30, "Chrome": 0.15, "Gemini": 0.05, "Spotify": 0.05},
            "Chrome":   {"WhatsApp": 0.35, "YouTube": 0.35, "Spotify": 0.20, "Gemini": 0.05, "Chrome": 0.05},
            "Gemini":   {"WhatsApp": 0.40, "YouTube": 0.30, "Spotify": 0.20, "Chrome": 0.05, "Gemini": 0.05},
        },
        WorkloadType.CONTEXT_SWITCHING: {
            # Bimodal cluster: Cluster A (Chrome, Gemini) vs Cluster B (YouTube, Spotify, WhatsApp)
            "Chrome":   {"Gemini": 0.60, "Chrome": 0.15, "WhatsApp": 0.15, "YouTube": 0.05, "Spotify": 0.05},
            "Gemini":   {"Chrome": 0.60, "Gemini": 0.15, "Spotify": 0.15, "YouTube": 0.05, "WhatsApp": 0.05},
            "YouTube":  {"Spotify": 0.45, "WhatsApp": 0.35, "YouTube": 0.10, "Chrome": 0.05, "Gemini": 0.05},
            "Spotify":  {"WhatsApp": 0.45, "YouTube": 0.35, "Spotify": 0.10, "Chrome": 0.05, "Gemini": 0.05},
            "WhatsApp": {"YouTube": 0.40, "Spotify": 0.40, "WhatsApp": 0.10, "Chrome": 0.05, "Gemini": 0.05},
        },
        WorkloadType.ADVERSARIAL: {
            # Cyclic access pattern that maximizes LRU/LFU cache evictions
            "Chrome":   {"YouTube": 0.85, "Spotify": 0.05, "Gemini": 0.05, "WhatsApp": 0.05},
            "YouTube":  {"Spotify": 0.85, "WhatsApp": 0.05, "Gemini": 0.05, "Chrome": 0.05},
            "Spotify":  {"WhatsApp": 0.85, "Gemini": 0.05, "Chrome": 0.05, "YouTube": 0.05},
            "WhatsApp": {"Gemini": 0.85, "Chrome": 0.05, "YouTube": 0.05, "Spotify": 0.05},
            "Gemini":   {"Chrome": 0.85, "YouTube": 0.05, "Spotify": 0.05, "WhatsApp": 0.05},
        },
    }

    @classmethod
    def generate(
        cls,
        workload_type: WorkloadType,
        num_events: int = 400,
        seed: int = 42,
        apps: Optional[List[str]] = None,
        app_ram: Optional[Dict[str, int]] = None,
    ) -> WorkloadSequence:
        """Generates a complete reproducible workload sequence."""
        rng = random.Random(seed)
        apps_list = apps or DEFAULT_APPS
        ram_map = app_ram or DEFAULT_APP_RAM
        matrix = cls.TRANSITION_MATRICES.get(workload_type, cls.TRANSITION_MATRICES[WorkloadType.PREDICTABLE])

        current_app = rng.choice(apps_list)
        ts = datetime(2026, 5, 12, 9, 0, 0)
        events: List[WorkloadEvent] = []

        for tick in range(num_events):
            base_ram = ram_map.get(current_app, 500)
            ram_variance = rng.randint(-50, 50)
            actual_ram = max(150, base_ram + ram_variance)
            importance = rng.uniform(0.4, 0.9)

            events.append(
                WorkloadEvent(
                    tick=tick,
                    timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
                    item_id=current_app,
                    ram_mb=actual_ram,
                    context_type="APP",
                    importance=round(importance, 2),
                )
            )

            # Advance timestamp by 1 to 4 minutes
            ts += timedelta(seconds=rng.randint(60, 240))

            # Pick next app using transition matrix
            targets = matrix.get(current_app, {a: 1.0 / len(apps_list) for a in apps_list})
            target_apps = list(targets.keys())
            weights = list(targets.values())
            current_app = rng.choices(target_apps, weights=weights, k=1)[0]

        return WorkloadSequence(
            name=f"{workload_type.value}_seed{seed}",
            workload_type=workload_type,
            seed=seed,
            num_events=num_events,
            events=events,
            items=apps_list,
        )
