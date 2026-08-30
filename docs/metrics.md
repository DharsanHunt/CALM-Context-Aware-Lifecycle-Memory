# CALM V2 Metric Definitions

This document details the mathematical formulations and definitions for all performance, memory, stability, and prediction metrics in CALM V2.

---

## 1. Performance Metrics

### 1.1 Cache Hit Rate (%)
The percentage of access requests where the requested item was already resident in memory (`ACTIVE`, `CACHED`, or `COMPRESSED`) **prior** to the request execution:
$$\text{Hit Rate} = \frac{\sum_{t=1}^T \mathbb{I}(\text{State}_{t-1}(\text{req}_t) \in \{\text{ACTIVE}, \text{CACHED}, \text{COMPRESSED}\})}{T} \times 100\%$$

### 1.2 Launch / Retrieval Latency (seconds)
The time taken to transition the requested item to `ACTIVE` state based on its pre-request state:
$$\text{Avg Latency} = \frac{1}{T} \sum_{t=1}^T L(\text{State}_{t-1}(\text{req}_t))$$
where:
$$L(\text{ACTIVE}) = 0.05s, \quad L(\text{CACHED}) = 0.40s, \quad L(\text{COMPRESSED}) = 1.10s, \quad L(\text{ARCHIVED}) = 2.40s$$

### 1.3 Percentile Latencies ($P_{95}$, $P_{99}$)
The 95th and 99th percentiles of the empirical launch latency distribution.

---

## 2. Memory Metrics

### 2.1 Average & Peak RAM (MB)
- **Average RAM**: $\bar{R} = \frac{1}{T} \sum_{t=1}^T R_t$
- **Peak RAM**: $R_{\max} = \max_{t \in [1, T]} R_t$

### 2.2 Memory-Time Integral ($\text{MB} \cdot \text{ticks}$)
The cumulative area under the memory usage curve over the entire sequence duration:
$$\text{Memory-Time} = \sum_{t=1}^T R_t$$

### 2.3 Memory Reclaimed (MB)
Total RAM released back to the system via demotions to `COMPRESSED` or `ARCHIVED`:
$$\text{Reclaimed} = \sum_{t=1}^T \max(0, R_{t,\text{before\_evict}} - R_{t,\text{after\_evict}})$$

### 2.4 Budget Violations
Total number of simulation ticks where total resident RAM exceeded the allocated system budget:
$$\text{Violations} = \sum_{t=1}^T \mathbb{I}(R_t > R_{\text{limit}})$$

---

## 3. Stability & Lifecycle Metrics

### 3.1 Thrashing Count
The number of times an item is evicted to `ARCHIVED` and subsequently re-requested within a short sliding window ($W_{\text{thrash}} = 5$ ticks):
$$\text{Thrashing} = \sum_{t=1}^T \mathbb{I}(\text{State}_{t-1}(\text{req}_t) = \text{ARCHIVED} \land (t - t_{\text{last\_evict}}(\text{req}_t) \le W_{\text{thrash}}))$$

### 3.2 State Distribution (%)
The percentage of total item-ticks spent in each lifecycle state across all items:
$$\text{Dist}(S) = \frac{\sum_{t=1}^T \sum_{i=1}^N \mathbb{I}(\text{State}_t(i) = S)}{N \cdot T} \times 100\%$$

---

## 4. Prediction Metrics

### 4.1 Top-$k$ Accuracy (%)
The percentage of sequence steps where the actual next item was present within the predictor's top-$k$ ranked candidates:
$$\text{Acc}_k = \frac{\sum_{t=1}^{T-1} \mathbb{I}(\text{item}_{t+1} \in \text{TopK}(\text{item}_t, k))}{T - 1} \times 100\%$$

### 4.2 Mean Confidence
The average prediction confidence across all evaluation steps:
$$\bar{C} = \frac{1}{T-1} \sum_{t=1}^{T-1} \text{Confidence}(\text{item}_t)$$

### 4.3 Brier Score
Mean squared error between predicted transition probabilities and the one-hot actual target:
$$\text{Brier} = \frac{1}{T-1} \sum_{t=1}^{T-1} \sum_{j=1}^N (P(\text{next} = j \mid \text{item}_t) - \mathbb{I}(\text{item}_{t+1} = j))^2$$
