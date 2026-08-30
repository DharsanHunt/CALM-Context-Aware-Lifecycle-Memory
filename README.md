# CALM — Context-Aware Lifecycle Memory (CALM V2)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)

A predictive, multi-tier lifecycle memory orchestration engine for **Mobile Application Caching** and **AI Agent Context Management**.

---

## 1. Problem Statement

Conventional operating systems and agent runtimes manage memory reactively:
- **Reactive process killing / eviction**: Memory management logic remains idle until memory pressure reaches critical thresholds (e.g., Android Low Memory Killer or LLM prompt token limits), after which items are evicted blindly.
- **Cache thrashing**: Under constrained memory budgets, reactive LRU/LFU caches frequently evict items that are requested again moments later, leading to severe latency spikes and degraded user experience.
- **Binary state models**: Traditional caches treat items as either fully resident or completely evicted, ignoring intermediate lifecycle states such as in-memory compression.

---

## 2. Core Idea

**CALM (Context-Aware Lifecycle Memory)** replaces reactive eviction with **predictive, multi-tier lifecycle orchestration**:
Instead of waiting for memory pressure to become critical, CALM predicts future resource requirements and dynamically transitions memory items across four explicit lifecycle states:

$$\text{ACTIVE} \longleftrightarrow \text{CACHED} \longleftrightarrow \text{COMPRESSED} \longleftrightarrow \text{ARCHIVED}$$

Decisions are made by evaluating:
- Current foreground usage
- Harmonic recency and normalized frequency
- Access burst intensity
- Next-access prediction probability and prediction confidence
- Memory pressure levels and rolling pressure trend slopes
- State residency duration constraints (hysteresis)
- Directional transition costs

---

## 3. Why Existing LRU/LFU Is Not Enough

| Mechanism | LRU / LFU | Reactive Pressure | CALM V2 |
|:---|:---:|:---:|:---:|
| **Action Trigger** | Reactive on overflow | Reactive on thresholds | Predictive + Proactive trend analysis |
| **Lifecycle Tiers** | Binary (In-RAM / Evicted) | Multi-tier (Active / Evicted) | 4 Tiers (Active, Cached, Compressed, Archived) |
| **Prediction Signals** | ❌ None | ❌ None | ✅ Smoothed Markov + Confidence weighting |
| **Burst Protection** | ❌ None | ❌ None | ✅ Priority boost for rapid repeat accesses |
| **Thrashing Mitigation** | ❌ Vulnerable | ⚠️ Limited | ✅ Residency hysteresis & dual thresholds |
| **Context Memory Mode**| ❌ No payload model | ❌ No compression | ✅ Real zlib compression for agent chunks |

---

## 4. Architecture

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

## 5. Lifecycle States & Transition Cost Model

1. **`ACTIVE`**: Foreground process / prompt-injected LLM chunk. Consumes full base RAM. Launch latency: $0.05\text{s}$.
2. **`CACHED`**: Resident in RAM, uncompressed. Ready for immediate reuse. Launch latency: $0.40\text{s}$.
3. **`COMPRESSED`**: Compressed in RAM. Occupies $\approx 35\%$ base RAM (or real zlib compressed size). Launch latency: $1.10\text{s}$.
4. **`ARCHIVED`**: Evicted from resident RAM to persistent cold storage. Zero RAM footprint. Launch latency: $2.40\text{s}$.

Every transition incurs quantitative latency, CPU time, and I/O costs:
- **Promotion** (`ARCHIVED` $\to$ `ACTIVE`): $2.40\text{s}$ latency, $120\text{ms}$ CPU.
- **Decompress** (`COMPRESSED` $\to$ `ACTIVE`): $1.10\text{s}$ latency, $45\text{ms}$ CPU.
- **Preemptive Compress** (`CACHED` $\to$ `COMPRESSED`): $0.15\text{s}$ async latency, $50\text{ms}$ CPU.

---

## 6. Prediction Engine & Confidence Scoring

The predictor learns transition probabilities strictly from historical sequences:
$$P(\text{next} = j \mid \text{current} = i) = \frac{C(i, j) + \alpha}{\sum_k C(i, k) + \alpha \cdot N}$$

Prediction certainty is quantified using Shannon entropy and sample support:
$$H(X) = -\sum_j p_j \log_2(p_j), \quad \text{Confidence} = \left(1 - \frac{H(X)}{\log_2 N}\right) \cdot \min\left(1.0, \frac{\text{obs\_count}}{N_{\text{min}}}\right)$$

- **High Confidence ($\ge 0.70$)**: Strong proactive prewarming to `CACHED` state.
- **Medium Confidence ($0.45 - 0.70$)**: Moderate prewarming to `COMPRESSED` state.
- **Low Confidence ($< 0.45$)**: Conservative fallback to reactive LRU/pressure handling.

---

## 7. Context Awareness & Priority Function

The policy engine computes item priority without hard-coded constants:
$$\text{Priority} = w_{\text{fg}} \cdot \text{FG} + w_{\text{pred}} \cdot (\text{Prob} \cdot \text{Conf}) + w_{\text{rec}} \cdot \text{Rec} + w_{\text{freq}} \cdot \text{Freq} + w_{\text{burst}} \cdot \text{Burst} + w_{\text{ctx}} \cdot \text{Context} - w_{\text{cost}} \cdot \text{Cost}$$

All weights are configurable via `CALMConfig.priority_weights`.

---

## 8. Benchmark Methodology & Baselines

### Workload Suite
CALM V2 evaluates performance across 7 distinct workload archetypes:
1. `Predictable`: Regular Markov transitions.
2. `Random`: Uniform stochastic access patterns.
3. `Bursty`: High temporal locality with rapid repeat bursts.
4. `Productivity`: Workspace tool clustering (Browser, IDE, Docs).
5. `Social Media`: Fast interleaved switching across media and chat.
6. `Context Switching`: Multi-task switching between separate clusters.
7. `Adversarial`: Cyclic access patterns designed to stress traditional caches.

### Strict Fairness & Temporal Split
- **70% Training / 15% Validation / 15% Test**: The predictor is trained strictly on historical sequences and evaluated on unseen future sequences (zero data leakage).
- **Pre-Update Latency Measurement**: Latency and hit rate are measured using the state **before** the manager modifies it.

### Baselines Evaluated
1. **Random**
2. **LRU (Least Recently Used)**
3. **LFU (Least Frequently Used)**
4. **Reactive Pressure Management**
5. **Predictive-Only**
6. **Pressure-Only**
7. **CALM V2**

---

## 9. Experimental Results

### Head-to-Head Comparison (Predictable Workload, Mean across 5 Seeds)

| Strategy | Cache Hit Rate (%) | Avg Launch Latency (s) | Thrashing Count | Peak RAM (MB) |
|:---|:---:|:---:|:---:|:---:|
| **Random** | 35.8% | 1.68s | 74.2 | 2,450 |
| **LFU** | 41.2% | 1.54s | 68.0 | 2,500 |
| **LRU** | 48.5% | 1.42s | 58.6 | 2,500 |
| **Reactive** | 53.2% | 1.38s | 54.0 | 2,420 |
| **Predictive-Only** | 56.4% | 1.35s | 51.2 | 2,500 |
| **Pressure-Only** | 54.8% | 1.37s | 50.8 | 2,450 |
| **CALM V2** | **62.2%** | **1.29s** | **44.4** | **2,480** |

### Component Ablation Study (Predictable Workload, 5 Seeds)

| Variant | Cache Hit Rate (%) | Avg Latency (s) | Thrashing Count | Memory-Time (MB·ticks) |
|:---|:---:|:---:|:---:|:---:|
| **CALM Full** | **62.17% ± 2.33** | **1.2949s ± 0.029** | **44.4** | 270,498 |
| **w/o Prediction** | 55.83% ± 4.34 | 1.4052s ± 0.078 | 52.0 | 268,004 |
| **w/o Burst Protection** | 61.67% ± 0.91 | 1.3026s ± 0.020 | 45.0 | 270,374 |
| **w/o Hysteresis** | 62.50% ± 2.42 | 1.2964s ± 0.030 | 44.0 | 269,389 |
| **w/o Pressure Trend** | 62.17% ± 2.33 | 1.2949s ± 0.029 | 44.4 | 270,498 |
| **w/o Compression** | 43.00% ± 1.55 | 1.5161s ± 0.043 | 67.4 | 242,800 |
| **w/o Context Importance** | 62.17% ± 2.33 | 1.2949s ± 0.029 | 44.4 | 270,498 |

---

## 10. AI Agent Context Memory Extension (Mode B)

CALM V2 extends seamlessly to manage LLM working context and long-term memory chunks:
- **`ACTIVE`**: Prompt-injected working context (Current task, active user query).
- **`CACHED`**: Uncompressed recent discussion and critical decisions.
- **`COMPRESSED`**: Real `zlib` compressed memory (Tool outputs, execution traces).
- **`ARCHIVED`**: Cold vector / disk knowledge storage.

Includes real byte sizing, compression ratio calculation, and automatic decompression on query.

---

## 11. Quick Start & Execution Commands

### Installation
```bash
git clone https://github.com/DharsanHunt/CALM-Context-Aware-Lifecycle-Memory.git
cd CALM-Context-Aware-Lifecycle-Memory
pip install -r requirements.txt
```

### Running the Research Dashboard
```bash
streamlit run app.py
```

### Running Unit & Integration Tests
```bash
python -m unittest discover tests
```

### Running the Multi-Seed Benchmark Suite
```bash
python -m calm.benchmark.runner --seeds 42 43 44 45 46 --workloads all
```

### Running the Component Ablation Study
```bash
python -m calm.benchmark.runner --ablation --seeds 42 43 44 45 46
```

---

## 12. Project Structure

```
CALM/
├── app.py                     # Streamlit Research & Engineering Dashboard
├── README.md                  # Master documentation & technical guide
├── requirements.txt           # Version-pinned dependencies
├── pyproject.toml             # Build & packaging configuration
├── .gitignore                 # Repository hygiene
│
├── calm/                      # Core CALM V2 package
│   ├── __init__.py
│   ├── models/                # Domain entities (AppState, MemoryItem, Telemetry, Prediction)
│   ├── telemetry/             # Collectors, ContextExtractors, and 7 Workload generators
│   ├── prediction/            # Smoothed Markov predictor, Confidence, Entropy, Evaluation
│   ├── policy/                # Priority engine, Pressure engine, Hysteresis, Burst detector
│   ├── lifecycle/             # LifecycleManager, TransitionCostModel, State graphs
│   ├── storage/               # Real zlib compression, Cache pool, Cold archive
│   ├── adapters/              # Simulated Mobile and AI Agent Memory adapters
│   ├── benchmark/             # 7 Baselines, Metrics calculator, Multi-seed runner, Reporter
│   └── utils/                 # System config, Structured logging, Seeded RNG
│
├── workloads/                 # Pre-generated benchmark JSON suites
├── tests/                     # 33 unit and integration tests across 8 modules
├── results/                   # Benchmark output logs (raw/, processed/, figures/)
└── docs/                      # Technical documentation (architecture, methodology, metrics, experiments)
```

---

## 13. Technical Limitations & Honest Disclosures

- **Simulation Mode**: In Mobile Mode (Mode A), process memory and launch times are simulated using empirically calibrated hardware parameters. CALM does not directly hook into Linux kernel page tables or low-level Android cgroups.
- **Markov Predictor**: The default sequence predictor is a first-order / multi-step Markov chain. While effective for habitual app switching, it does not capture complex long-range dependencies requiring transformer models.
- **Agent Mode**: In Agent Mode (Mode B), context chunks are compressed using `zlib` and managed in memory; semantic importance scoring is deterministic and extensible to embedding-based retrieval.

---

## 14. License

Released under the [MIT License](LICENSE).
