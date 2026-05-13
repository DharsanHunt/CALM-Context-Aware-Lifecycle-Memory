# Context-Aware Adaptive Memory for Mobile Agentic Systems

Hackathon prototype demonstrating **adaptive lifecycle orchestration** — a multi-tiered memory management system that uses predictive modeling, telemetry, and pressure-aware transitions to optimize mobile app caching.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

```
app.py            ← Streamlit dashboard & simulation orchestrator
simulator.py      ← App usage log generator (weighted Markov transitions)
predictor.py      ← Markov chain predictor with confidence scoring
allocator.py      ← Priority scoring & pressure-aware memory allocation
cache.py          ← LifecycleEngine (proactive) + CacheManager (baseline)
metrics.py        ← Performance metrics (hit rate, latency, thrashing, lifecycle)
utils.py          ← Shared constants and helpers
data/             ← Generated usage logs (usage_logs.csv)
```

## How It Works

### Lifecycle Engine (cache.py)

Instead of reactive process killing, apps flow through a **4-tier lifecycle**:

```
EVICTED  →  COMPRESSED  →  CACHED  →  ACTIVE
```

Transitions are driven by:

| Signal | Source | Effect |
|--------|--------|--------|
| **Per-app telemetry** | Access count, dwell time, burst score | Protect bursty apps from eviction |
| **Memory pressure** | Utilization trend (rising/falling/stable) | Preemptive compression before critical |
| **Prediction** | Markov chain next-app probability | Pre-warm likely apps |
| **Hysteresis** | Minimum ticks in state | Prevent rapid oscillation |

### Key Difference from Reactive Systems

- **Reactive**: waits until RAM limit is hit, then kills processes
- **Adaptive (this system)**: monitors pressure trends, preemptively compresses/evicts low-priority apps BEFORE pressure becomes critical

### Simulation Flow

1. **Simulate** — Generate 200–500 app-switch events using weighted transitions
2. **Predict** — Markov chain learns switch patterns, predicts next app with confidence
3. **Score** — Priority = 0.4×foreground + 0.3×prediction + 0.2×frequency + 0.1×recency
4. **Allocate** — Pressure-aware memory tiers (HIGH/MEDIUM/LOW scale with system load)
5. **Lifecycle** — Proactive state transitions driven by telemetry + pressure + prediction
6. **Measure** — Compare baseline (reactive CacheManager) vs adaptive (LifecycleEngine)

## Key Metrics

| Metric | Baseline | Adaptive |
|--------|----------|----------|
| Thrashing Events | Higher | Lower (-10%) |
| Avg Launch Time | Higher | Lower |
| EVICTED states | Higher | Lower |
| COMPRESSED states | Lower | Higher (proactive compression) |

## Tech Stack

- Python 3.10+
- Streamlit
- pandas
- matplotlib
