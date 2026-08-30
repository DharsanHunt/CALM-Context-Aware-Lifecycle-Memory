# CALM V2 Architecture Specification

## 1. System Overview

**CALM (Context-Aware Lifecycle Memory)** is a predictive lifecycle-memory management system. Instead of waiting for memory pressure to become critical and reactively evicting processes or context, CALM predicts future resource requirements and proactively transitions memory items across a multi-tier lifecycle.

CALM operates across two primary execution modes:
- **Mode A — Mobile Application Memory**: Manages mobile app process states (Chrome, YouTube, Spotify, WhatsApp, Gemini).
- **Mode B — AI Agent Context Memory**: Manages LLM working context, active tasks, conversation turns, tool results, decisions, and cold knowledge archives.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            TELEMETRY LAYER                              │
│         Access intervals, dwell time, burst rate, system RAM, CPU       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT EXTRACTION                            │
│         Harmonic recency, normalized frequency, burst intensity         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│        PREDICTION ENGINE        │     │        RESOURCE MONITOR         │
│  Smoothed Markov Chain          │     │  Memory Pressure Ratio          │
│  Top-k Candidate Ranking        │     │  Trend Slope (RISING/FALLING)   │
│  Confidence & Entropy Scoring   │     │  Headroom & Budget Enforcement  │
└────────────────┬────────────────┘     └────────────────┬────────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CALM POLICY ENGINE                            │
│  Multi-Signal Priority Scoring + Confidence Weighting                   │
│  Hysteresis Constraints + Burst Protection + Demotion Thresholds       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           LIFECYCLE MANAGER                             │
│     ACTIVE  ◄────────►  CACHED  ◄────────►  COMPRESSED  ◄────────►  ARCHIVED│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│        STORAGE ADAPTER          │     │      METRICS & BENCHMARKING     │
│  In-Memory Resident Pool        │     │  Pre-launch Latency, Hit Rate   │
│  Real Payload Compression       │     │  Memory-Time (MB·ticks)         │
│  Cold Persistent Archive        │     │  Thrashing & State Distributions│
└─────────────────────────────────┘     └─────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Telemetry Layer (`calm/telemetry/collector.py`)
Collects and tracks real-time execution signals:
- **Per-Item Telemetry**: Access counts, last access tick, state residency duration (`ticks_in_state`), access interval history (rolling window $W=20$), and burst score calculation.
- **System Telemetry**: Total resident RAM, memory budget limit, utilization ratio, and pressure trend slope.

### 2.2 Prediction Engine (`calm/prediction/markov.py`, `calm/prediction/confidence.py`)
- **Transition Probability Model**: Learns transition probabilities strictly from historical sequences:
  $$P(\text{next} = j \mid \text{current} = i) = \frac{C(i, j) + \alpha}{\sum_{k} C(i, k) + \alpha \cdot N}$$
  where $\alpha$ is the Laplace smoothing parameter and $N$ is the item vocabulary size.
- **Confidence & Uncertainty Quantification**:
  $$H(X) = -\sum_{j} p_j \log_2(p_j), \quad H_{\max} = \log_2(N)$$
  $$\text{Confidence} = \left(1 - \frac{H(X)}{H_{\max}}\right) \cdot \min\left(1.0, \frac{\text{obs\_count}}{N_{\text{min}}}\right)$$
- **Multi-Step Lookahead**: Computes multi-hop paths $P(A \to B \to C) = P(B \mid A) \cdot P(C \mid B)$.

### 2.3 Policy Engine (`calm/policy/priority.py`, `calm/policy/policy_engine.py`)
- **Composite Priority Function**:
  $$\text{Priority} = w_{\text{fg}} \cdot \text{FG} + w_{\text{pred}} \cdot (\text{Prob} \cdot \text{Conf}) + w_{\text{rec}} \cdot \text{Rec} + w_{\text{freq}} \cdot \text{Freq} + w_{\text{burst}} \cdot \text{Burst} + w_{\text{ctx}} \cdot \text{Context} - w_{\text{cost}} \cdot \text{Cost}$$
- **Memory Pressure Tracking**: Categorizes pressure into `LOW (<0.55)`, `MODERATE (0.55-0.75)`, `HIGH (0.75-0.95)`, and `CRITICAL (>=0.95)` with linear trend slope detection (`RISING`, `STABLE`, `FALLING`).
- **Hysteresis Controller**: Enforces minimum state duration (`min_state_ticks`) and dual asymmetric thresholds ($\text{promote} \ge 0.18$, $\text{demote} \le 0.25$) to eliminate cache thrashing and state oscillation.
- **Burst Protection**: Detects rapid repeat accesses and boosts priority to shield active items from premature eviction.

### 2.4 Lifecycle Manager (`calm/lifecycle/manager.py`)
Manages transitions across the 4 explicit states:
- **`ACTIVE`**: Item currently executing or injected into prompt. Full RAM / token allocation.
- **`CACHED`**: Resident in RAM, uncompressed. Rapid reuse with low launch latency.
- **`COMPRESSED`**: Compressed in RAM. Low memory footprint, fast decompression.
- **`ARCHIVED`**: Evicted from resident RAM to cold backing store. Zero resident RAM, high retrieval latency.

### 2.5 Storage & Compression Layer (`calm/storage/compression.py`)
- **Agent Mode**: Actual byte payload compression via `zlib` (levels 1–9) with exact tracking of original bytes, compressed bytes, compression ratio, and compression/decompression CPU latencies.
- **Mobile Simulation Mode**: Calibrated compression scaling factor ($0.35 \times \text{Base RAM}$) representing compressed process states / zRAM.

### 2.6 Benchmark & Baselines (`calm/benchmark/baselines.py`, `calm/benchmark/runner.py`)
Supports 7 standard strategies:
1. `Random`: Random eviction under memory pressure.
2. `LRU`: Least Recently Used eviction.
3. `LFU`: Least Frequently Used eviction.
4. `Reactive`: Multi-tier reactive demotion under hard limit without predictive prewarming.
5. `Predictive-Only`: Predictive prewarming without pressure trends or hysteresis.
6. `Pressure-Only`: Proactive pressure demotion without predictions.
7. `CALM V2`: Full unified predictive lifecycle orchestration.

---

## 3. Directional State Transition & Cost Model

```
       [ Cold Launch / Archive Retrieval (2.40s) ]
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  ▼                   Promote (0.40s)                │
ACTIVE ◄────────────────────────────────────────── CACHED
  │   ▲                                             │   ▲
  │   │          Decompress & Activate (1.10s)      │   │
  │   └─────────────────────────────────────────┐   │   │ Prewarm (0.40s)
  │                                             │   │   │
  │ Yield (0.05s)                               ▼   │   │
  │                                           COMPRESSED
  │                                             │   ▲
  │                               Demote (0.15s)│   │ Prewarm (0.60s)
  ▼                                             ▼   │
ARCHIVED ◄──────────────────────────────────────────┘
             Demote / Evict to Backing Store (0.10s)
```
