# CALM V2 Experimental Methodology

## 1. Overview & Research Principles

The evaluation methodology of CALM V2 is designed to adhere to standard scientific principles:
1. **Zero Future Data Leakage**: The predictor is trained strictly on historical sequences and evaluated on unseen future sequences.
2. **Strict Baseline Fairness**: All baselines and CALM start from identical initial states, observe identical request streams under identical resource budgets, and record performance metrics on the state **before** modification.
3. **Statistical Reproducibility**: Experiments are executed across multiple random seeds (e.g., 42, 43, 44, 45, 46) and report mean, standard deviation, minimum, and maximum statistics.

---

## 2. Dataset & Workload Generation

CALM V2 evaluates strategies across 7 distinct workload archetypes:

| Workload | Dynamics | Key Characteristics |
|:---|:---|:---|
| **`Predictable`** | Strong Markov transitions | Regular sequential access patterns with high prediction confidence. |
| **`Random`** | Uniform transitions | Maximum entropy transitions with low predictability. |
| **`Bursty`** | High temporal locality | Rapid repeat bursts on active items testing burst protection. |
| **`Productivity`** | Workspace clustering | Frequent switching between productivity tools (Docs, Browser, IDE). |
| **`Social Media`** | Rapid feed switching | Fast interleaved switching across messaging, media, and browser apps. |
| **`Context Switching`** | Bimodal task clusters | Multi-task switching between separate clusters of related items. |
| **`Adversarial`** | Cyclic cache stress | Access sequences specifically engineered to maximize LRU/LFU thrashing. |

### Temporal Train / Validation / Test Separation
Each workload sequence ($N=400$ events) is partitioned temporally:
- **Training Set (70%)**: Events $0 \dots 279$. Used strictly for Markov transition matrix estimation.
- **Validation Set (15%)**: Events $280 \dots 339$. Used for threshold calibration.
- **Test Set (15%)**: Events $340 \dots 399$. Used strictly for final unseen evaluation.

---

## 3. Baseline Evaluation Protocols

All strategies implement the standardized `BaseStrategy` interface:

```python
def step(requested_item: str, prediction_result: Optional[PredictionResult]) -> Dict[str, Any]:
    # 1. FAIRNESS: Capture state BEFORE the lifecycle engine modifies it
    pre_launch_state = self.states[requested_item]
    is_cache_hit = pre_launch_state in (ACTIVE, CACHED, COMPRESSED)
    launch_latency = self.config.launch_times[pre_launch_state]
    
    # 2. Execute strategy-specific state transitions and budget enforcement
    ...
    return telemetry_snapshot
```

### Baselines Included:
1. **Random**: Randomly evicts items when system memory limit is exceeded.
2. **LRU (Least Recently Used)**: Evicts the item with the oldest last-access timestamp.
3. **LFU (Least Frequently Used)**: Evicts the item with the lowest cumulative access count.
4. **Reactive**: Multi-tier reactive demotion (`ACTIVE` $\to$ `CACHED` $\to$ `COMPRESSED` $\to$ `ARCHIVED`) triggered only upon hard memory limit violations.
5. **Predictive-Only**: Uses predictive prewarming but purely reactive eviction without pressure trend analysis or hysteresis.
6. **Pressure-Only**: Uses memory pressure levels and trend slopes for proactive demotion, but lacks predictive prewarming.
7. **CALM V2**: Full integration of prediction confidence, multi-tier states, pressure trends, hysteresis, and burst protection.

---

## 4. Multi-Seed Statistical Reporting

To measure stability across random seeds, the benchmark runner evaluates 5 fixed seeds ($S = \{42, 43, 44, 45, 46\}$).

For every metric $M$, we report:
- **Sample Mean**: $\mu = \frac{1}{|S|} \sum_{s \in S} M_s$
- **Sample Standard Deviation**: $\sigma = \sqrt{\frac{1}{|S|-1} \sum_{s \in S} (M_s - \mu)^2}$
- **Range**: $[\min_{s} M_s, \max_{s} M_s]$
