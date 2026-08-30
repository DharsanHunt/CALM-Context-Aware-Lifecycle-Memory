# CALM V2 Automated Experiments & Empirical Results

This document describes the 10 automated benchmark experiments supported in CALM V2 and analyzes the empirical findings across workloads and ablation variants.

---

## Experiment Index

1. **Experiment 1: Prediction Accuracy & Uncertainty** — Evaluates top-1/top-3 accuracy, Shannon entropy, and Brier calibration across regular and stochastic workloads.
2. **Experiment 2: CALM vs. LRU** — Compares hit rate, launch latency, and memory utilization against standard Least Recently Used caching.
3. **Experiment 3: CALM vs. LFU** — Evaluates performance against Least Frequently Used frequency-based eviction.
4. **Experiment 4: CALM vs. Reactive Pressure Management** — Quantifies the benefit of proactive prediction and pressure slope tracking over reactive limit enforcement.
5. **Experiment 5: Effect of Prediction Confidence** — Measures system behavior under high-confidence vs. low-confidence regimes.
6. **Experiment 6: Effect of Memory Budget** — Evaluates performance across tight (1200 MB), moderate (2500 MB), and generous (6000 MB) RAM allocations.
7. **Experiment 7: Effect of Workload Randomness** — Evaluates robustness across high-entropy uniform random streams.
8. **Experiment 8: Effect of Burstiness** — Analyzes burst protection on high-frequency access spikes.
9. **Experiment 9: Effect of Payload Compression** — Compares multi-tier compressed memory vs. two-tier eviction.
10. **Experiment 10: Component Ablation Study** — Measures the isolated contribution of each architectural subsystem.

---

## Key Experimental Findings

### 1. Head-to-Head Baseline Comparison (Predictable Workload, Mean across 5 Seeds)

| Strategy | Cache Hit Rate (%) | Avg Launch Latency (s) | Thrashing Count | Peak RAM (MB) |
|:---|:---:|:---:|:---:|:---:|
| **Random** | 35.8% | 1.68s | 74.2 | 2,450 |
| **LFU** | 41.2% | 1.54s | 68.0 | 2,500 |
| **LRU** | 48.5% | 1.42s | 58.6 | 2,500 |
| **Reactive** | 53.2% | 1.38s | 54.0 | 2,420 |
| **Predictive-Only** | 56.4% | 1.35s | 51.2 | 2,500 |
| **Pressure-Only** | 54.8% | 1.37s | 50.8 | 2,450 |
| **CALM V2** | **62.2%** | **1.29s** | **44.4** | **2,480** |

**Observation**: CALM V2 improves cache hit rate by **+13.7%** over LRU and reduces thrashing by **-24.2%** while strictly respecting the 2,500 MB RAM budget.

---

### 2. Component Ablation Study Results (Predictable Workload, 5 Seeds)

| Variant | Cache Hit Rate (%) | Avg Latency (s) | Thrashing Count | Memory-Time (MB·ticks) |
|:---|:---:|:---:|:---:|:---:|
| **CALM Full** | **62.17% ± 2.33** | **1.2949s ± 0.029** | **44.4** | 270,498 |
| **w/o Prediction** | 55.83% ± 4.34 | 1.4052s ± 0.078 | 52.0 | 268,004 |
| **w/o Burst Protection** | 61.67% ± 0.91 | 1.3026s ± 0.020 | 45.0 | 270,374 |
| **w/o Hysteresis** | 62.50% ± 2.42 | 1.2964s ± 0.030 | 44.0 | 269,389 |
| **w/o Pressure Trend** | 62.17% ± 2.33 | 1.2949s ± 0.029 | 44.4 | 270,498 |
| **w/o Compression** | 43.00% ± 1.55 | 1.5161s ± 0.043 | 67.4 | 242,800 |
| **w/o Context Importance** | 62.17% ± 2.33 | 1.2949s ± 0.029 | 44.4 | 270,498 |

**Key Takeaways**:
- **Compression**: The most vital tier for capacity extension; disabling compression collapses hit rate from 62.2% to 43.0% and spikes thrashing by +51.8%.
- **Prediction**: Predictive prewarming accounts for a **+6.3%** absolute hit rate boost and significantly reduces launch latency.
