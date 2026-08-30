"""
CALM V2 — Systems Analytics & Lifecycle Management Console
Implementation aligned with Stitch Design System (Modern Minimalist Technical Console).
Supports: Overview, Lifecycle Monitor, Prediction & Confidence, Memory Management,
Benchmark Suite, Component Ablation, and AI Agent Context Memory.

Run with: streamlit run app.py
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calm.utils.config import (
    CALMConfig,
    DEFAULT_APPS,
    DEFAULT_APP_RAM,
    PRESET_NAMES,
    get_preset_config,
    PriorityWeights,
)
from calm.telemetry.workload import (
    WorkloadGenerator,
    WorkloadType,
    WorkloadSequence,
    temporal_split,
)
from calm.prediction.markov import MarkovPredictor
from calm.prediction.confidence import ConfidenceScorer
from calm.prediction.evaluation import PredictionEvaluator
from calm.benchmark.baselines import (
    create_strategy,
    STRATEGY_NAMES,
    BaseStrategy,
)
from calm.benchmark.metrics import BenchmarkMetricsCalculator, RunResultMetrics
from calm.benchmark.runner import BenchmarkRunner
from calm.benchmark.report import BenchmarkReporter
from calm.adapters.agent import AgentMemoryEngine
from calm.models.memory_item import ItemType
from calm.models.app_state import LifecycleState


# ── Page Configuration & Stitch Design System CSS ────────────────────────────

st.set_page_config(
    page_title="CALM Console — Lifecycle Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Stitch Design Tokens & Custom CSS
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />

<style>
    /* Global App Canvas & Typography */
    .stApp {
        background-color: #F8F9FB;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #191C1E;
    }
    
    /* Top Header Bar */
    .stitch-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 24px;
        border-radius: 8px;
    }
    .stitch-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .stitch-badge-icon {
        width: 36px;
        height: 36px;
        background: #2563EB;
        color: #FFFFFF;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .stitch-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
        line-height: 1.2;
    }
    .stitch-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0;
    }
    
    /* Bento Cards */
    .bento-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
    }
    .bento-card-header {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .bento-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0F172A;
        font-family: 'Inter', sans-serif;
        line-height: 1.1;
    }
    .bento-delta {
        font-size: 0.82rem;
        font-weight: 500;
        margin-top: 4px;
    }
    .delta-pos { color: #16A34A; }
    .delta-neg { color: #DC2626; }
    .delta-neu { color: #64748B; }

    /* State Chips */
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 0.02em;
    }
    .chip-active { background: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
    .chip-cached { background: #DBEAFE; color: #1D4ED8; border: 1px solid #BFDBFE; }
    .chip-compressed { background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
    .chip-archived { background: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; }
    
    /* Flow Diagrams */
    .lifecycle-flow-container {
        display: flex;
        align-items: center;
        justify-content: space-around;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 20px;
    }
    .flow-step {
        text-align: center;
        padding: 12px 18px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .flow-arrow {
        color: #94A3B8;
        font-size: 1.2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar Controls ─────────────────────────────────────────────────────────

st.sidebar.markdown("### 🎛️ CALM System Control")

mode = st.sidebar.radio(
    "Architecture Mode",
    ["📱 Mode A — Mobile Application Memory", "🤖 Mode B — AI Agent Context Memory"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**⚙️ Memory Budget & Profiles**")

aggression = st.sidebar.selectbox(
    "Aggression Preset",
    PRESET_NAMES,
    index=PRESET_NAMES.index("Less Aggressive"),
    help="Pre-configured aggression and budget profiles.",
)

preset_cfg = get_preset_config(aggression)

ram_limit_mb = st.sidebar.number_input(
    "System Memory Limit (MB)",
    min_value=500,
    max_value=16000,
    value=preset_cfg.ram_limit_mb,
    step=100,
)

compressed_factor = st.sidebar.slider(
    "Compressed Memory Factor",
    min_value=0.10,
    max_value=0.60,
    value=preset_cfg.storage.compressed_ram_factor,
    step=0.05,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Workload Archetype**")

workload_choice = st.sidebar.selectbox(
    "Workload Pattern",
    [w.value for w in WorkloadType],
    index=0,
)

num_events = st.sidebar.slider("Workload Length (Ticks)", 150, 600, 350, step=50)
seed = st.sidebar.number_input("RNG Seed", min_value=1, max_value=9999, value=42, step=1)

run_button = st.sidebar.button("▶ Run Full Benchmark", type="primary", use_container_width=True)

# Build Master Config
config = CALMConfig(
    mode="mobile" if "Mobile" in mode else "agent",
    ram_limit_mb=ram_limit_mb,
    app_ram=dict(preset_cfg.app_ram),
    aggression=aggression,
)
config.storage.compressed_ram_factor = compressed_factor


# ── Simulation Runner Engine (Cached) ────────────────────────────────────────

@st.cache_data(show_spinner=False)
def execute_benchmark_run(w_type_str: str, n_events: int, r_seed: int, cfg_dict: dict):
    """Executes full comparative simulation across CALM and all 7 baselines."""
    cfg = CALMConfig.from_dict(cfg_dict)
    w_type = WorkloadType(w_type_str)

    workload_seq = WorkloadGenerator.generate(
        workload_type=w_type,
        num_events=n_events,
        seed=r_seed,
        apps=DEFAULT_APPS,
        app_ram=cfg.app_ram,
    )

    train_seq, val_seq, test_seq = temporal_split(workload_seq, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    eval_events = val_seq.events + test_seq.events
    eval_items = [e.item_id for e in eval_events]

    # 1. Train Markov Predictor strictly on historical train sequence (Zero Data Leakage)
    predictor = MarkovPredictor(smoothing_alpha=cfg.prediction.smoothing_alpha)
    train_items = [e.item_id for e in train_seq.events]
    predictor.fit(train_items, all_items=DEFAULT_APPS)

    # 2. Evaluate Prediction Accuracy
    pred_metrics = PredictionEvaluator.evaluate(predictor, eval_items, top_k=cfg.prediction.top_k)

    # 3. Run all 7 strategies on identical eval events from identical initial states
    strategy_traces = {}
    strategy_metrics = {}

    for strat_name in STRATEGY_NAMES:
        strat = create_strategy(strat_name, cfg, DEFAULT_APPS, seed=r_seed)
        step_results = []
        for event in eval_events:
            req_item = event.item_id
            pred_res = predictor.predict(req_item, top_k=cfg.prediction.top_k)
            step_res = strat.step(requested_item=req_item, prediction_result=pred_res)
            step_results.append(step_res)

        metrics = BenchmarkMetricsCalculator.calculate(
            strategy_name=strat_name,
            workload_name=w_type.value,
            seed=r_seed,
            step_results=step_results,
            ram_limit_mb=cfg.ram_limit_mb,
            prediction_metrics=pred_metrics,
        )
        strategy_traces[strat_name] = step_results
        strategy_metrics[strat_name] = metrics.to_dict()

    return {
        "workload": workload_seq.to_dict(),
        "train_len": len(train_seq.events),
        "eval_len": len(eval_events),
        "predictor": predictor,
        "pred_metrics": pred_metrics,
        "traces": strategy_traces,
        "metrics": strategy_metrics,
        "config": cfg.to_dict(),
    }


# Auto-run initial simulation if needed
if "sim_results" not in st.session_state or run_button:
    with st.spinner("Executing CALM V2 Engine & Baseline Suites..."):
        st.session_state["sim_results"] = execute_benchmark_run(
            workload_choice, num_events, int(seed), config.to_dict()
        )


sim_data = st.session_state["sim_results"]
calm_trace = sim_data["traces"]["CALM"]
calm_metrics = sim_data["metrics"]["CALM"]
lru_metrics = sim_data["metrics"]["LRU"]
reactive_metrics = sim_data["metrics"]["Reactive"]
predictor = sim_data["predictor"]
pred_metrics = sim_data["pred_metrics"]

app_colors = {
    "Chrome": "#4285F4",
    "YouTube": "#EA4335",
    "Spotify": "#1DB954",
    "Gemini": "#8B5CF6",
    "WhatsApp": "#25D366",
}
state_colors = {
    "ACTIVE": "#16A34A",
    "CACHED": "#2563EB",
    "COMPRESSED": "#D97706",
    "ARCHIVED": "#DC2626",
}


# ── Top App Bar (Stitch Design) ──────────────────────────────────────────────

st.markdown(f"""
<div class="stitch-header">
    <div class="stitch-brand">
        <div class="stitch-badge-icon">C</div>
        <div>
            <h1 class="stitch-title">CALM Systems Console</h1>
            <p class="stitch-subtitle">Context-Aware Lifecycle Memory Analytics & Orchestration</p>
        </div>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
        <span class="chip chip-cached">MODE: {config.mode.upper()}</span>
        <span class="chip chip-active">BUDGET: {ram_limit_mb:,} MB</span>
        <span class="chip chip-compressed">WORKLOAD: {workload_choice.upper()}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Navigation Tabs (Matching Stitch Console Structure) ──────────────────────

tab_overview, tab_lifecycle, tab_prediction, tab_memory, tab_benchmarks, tab_ablation, tab_agent = st.tabs([
    "Overview",
    "Lifecycle Monitor",
    "Prediction & Confidence",
    "Memory Management",
    "Benchmark Suite",
    "Component Ablation",
    "Agent Memory (Mode B)",
])


# ══════════════════════════════════════════════════════════════════════════════
# 1. OVERVIEW (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.markdown("### 📊 System Telemetry & KPIs")

    # Bento KPI Grid
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        hit_val = calm_metrics["cache_hit_rate_pct"]
        hit_delta = hit_val - lru_metrics["cache_hit_rate_pct"]
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-header">Cache Hit Rate</div>
            <div class="bento-value">{hit_val:.1f}%</div>
            <div class="bento-delta delta-pos">+{hit_delta:.1f}% vs LRU Baseline</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        lat_val = calm_metrics["avg_launch_latency_sec"]
        lru_lat = lru_metrics["avg_launch_latency_sec"]
        lat_imp = (lru_lat - lat_val) / lru_lat * 100 if lru_lat > 0 else 0
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-header">Avg Launch Latency</div>
            <div class="bento-value">{lat_val:.3f}s</div>
            <div class="bento-delta delta-pos">-{lat_imp:.1f}% faster than LRU</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        thrash_val = calm_metrics["thrashing_count"]
        lru_thrash = lru_metrics["thrashing_count"]
        thrash_diff = lru_thrash - thrash_val
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-header">Thrashing Events</div>
            <div class="bento-value">{thrash_val}</div>
            <div class="bento-delta delta-pos">-{thrash_diff} fewer evictions vs LRU</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        p_top3 = pred_metrics["top_3_accuracy"]
        p_conf = pred_metrics["mean_confidence"]
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-header">Top-3 Prediction Acc</div>
            <div class="bento-value">{p_top3:.1f}%</div>
            <div class="bento-delta delta-neu">Certainty: {p_conf:.1%}</div>
        </div>
        """, unsafe_allow_html=True)

    # Strategy Table & Live Snapshot
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.markdown("#### 📋 Strategy Benchmarks (Evaluation Window)")
        rows = []
        for s in STRATEGY_NAMES:
            m = sim_data["metrics"][s]
            rows.append({
                "Strategy": s,
                "Hit Rate (%)": f"{m['cache_hit_rate_pct']:.1f}%",
                "Avg Latency": f"{m['avg_launch_latency_sec']:.4f}s",
                "P95 Latency": f"{m['p95_launch_latency_sec']:.4f}s",
                "Avg RAM": f"{m['avg_ram_mb']:,.0f} MB",
                "Memory-Time": f"{m['memory_time_mb_ticks']:,.0f}",
                "Thrashing": m["thrashing_count"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with col_t2:
        st.markdown("#### 🗂 Final Memory State Snapshot")
        final_step = calm_trace[-1]
        snap_rows = []
        for item in DEFAULT_APPS:
            st_val = final_step["post_states"][item]
            st_str = st_val.value if hasattr(st_val, "value") else str(st_val)
            eff_ram = config.effective_ram(item, st_str)
            p_score = final_step.get("priority_scores", {}).get(item, 0.0)
            snap_rows.append({
                "Item": item,
                "State": st_str,
                "RAM": f"{eff_ram} MB",
                "Priority": f"{p_score:.3f}",
            })
        st.dataframe(pd.DataFrame(snap_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. LIFECYCLE MONITOR (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_lifecycle:
    st.markdown("### 🔄 4-Tier Lifecycle Flow & Transitions")
    st.caption("Tracking proactive promotions, prewarming, compression, and archival.")

    # Visual Flow Diagram
    st.markdown("""
    <div class="lifecycle-flow-container">
        <div class="flow-step" style="background:#DCFCE7; color:#15803D; border:1px solid #BBF7D0;">
            ACTIVE<br><small style="font-weight:normal;">Foreground (0.05s)</small>
        </div>
        <div class="flow-arrow">⇄</div>
        <div class="flow-step" style="background:#DBEAFE; color:#1D4ED8; border:1px solid #BFDBFE;">
            CACHED<br><small style="font-weight:normal;">Resident (0.40s)</small>
        </div>
        <div class="flow-arrow">⇄</div>
        <div class="flow-step" style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A;">
            COMPRESSED<br><small style="font-weight:normal;">In-RAM (~35% RAM, 1.10s)</small>
        </div>
        <div class="flow-arrow">⇄</div>
        <div class="flow-step" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FECACA;">
            ARCHIVED<br><small style="font-weight:normal;">Cold Disk (0 MB, 2.40s)</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("**State Distribution Across Ticks (% Time in State)**")
        fig_pie, (ax_p1, ax_p2) = plt.subplots(1, 2, figsize=(8, 3.5))
        lru_dist = lru_metrics["state_distribution"]
        calm_dist = calm_metrics["state_distribution"]
        labels = ["ACTIVE", "CACHED", "COMPRESSED", "ARCHIVED"]
        colors = [state_colors[s] for s in labels]

        ax_p1.pie([lru_dist.get(s, 0) for s in labels], labels=labels, colors=colors, autopct="%1.0f%%", textprops={"fontsize": 8})
        ax_p1.set_title("LRU Baseline", fontsize=10, fontweight="bold")

        ax_p2.pie([calm_dist.get(s, 0) for s in labels], labels=labels, colors=colors, autopct="%1.0f%%", textprops={"fontsize": 8})
        ax_p2.set_title("CALM V2 (Adaptive)", fontsize=10, fontweight="bold")
        plt.tight_layout()
        st.pyplot(fig_pie)

    with col_l2:
        st.markdown("**State Transition Trajectory Matrix (First 50 Ticks)**")
        timeline_records = []
        for step in calm_trace[:50]:
            row = {"Tick": step["tick"], "Access": step["requested_item"]}
            for app in DEFAULT_APPS:
                st_val = step["post_states"][app]
                row[app] = st_val.value if hasattr(st_val, "value") else str(st_val)
            timeline_records.append(row)
        st.dataframe(pd.DataFrame(timeline_records), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# 3. PREDICTION & CONFIDENCE (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_prediction:
    st.markdown("### 🔮 Prediction Modeling & Lookahead Projections")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Learned Transition Matrix: $P(\\text{Next} \\mid \\text{Current})$**")
        matrix_df = pd.DataFrame(index=DEFAULT_APPS, columns=DEFAULT_APPS, dtype=float)
        for src in DEFAULT_APPS:
            probs = predictor.get_transition_probabilities(src)
            for dst in DEFAULT_APPS:
                matrix_df.loc[src, dst] = round(probs.get(dst, 0.0), 3)
        st.dataframe(matrix_df, use_container_width=True)

    with col_p2:
        st.markdown("**Prediction Evaluation Telemetry (Zero Data Leakage)**")
        st.markdown(f"""
        <div class="bento-card">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                <div>
                    <div class="bento-card-header">Top-1 Accuracy</div>
                    <div class="bento-value" style="font-size:1.6rem;">{pred_metrics['top_1_accuracy']:.1f}%</div>
                </div>
                <div>
                    <div class="bento-card-header">Top-3 Accuracy</div>
                    <div class="bento-value" style="font-size:1.6rem;">{pred_metrics['top_3_accuracy']:.1f}%</div>
                </div>
                <div>
                    <div class="bento-card-header">Mean Confidence</div>
                    <div class="bento-value" style="font-size:1.6rem;">{pred_metrics['mean_confidence']:.1%}</div>
                </div>
                <div>
                    <div class="bento-card-header">Brier Uncertainty</div>
                    <div class="bento-value" style="font-size:1.6rem;">{pred_metrics['brier_score']:.4f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🎯 Multi-Step Future Lookahead Simulator")
    sel_src = st.selectbox("Select Current Foreground Item:", DEFAULT_APPS, key="lookahead_sel_v2")

    probs_sel = predictor.get_transition_probabilities(sel_src)
    conf_sel = ConfidenceScorer.calculate_confidence(probs_sel)
    entropy_sel = ConfidenceScorer.calculate_entropy(probs_sel)
    multi_paths = predictor.predict_multi_step(sel_src, steps=2, top_k_per_step=2)

    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        fig_bar, ax_bar = plt.subplots(figsize=(8, 3))
        ax_bar.barh(list(probs_sel.keys()), list(probs_sel.values()), color=[app_colors.get(a, "#2563EB") for a in probs_sel.keys()])
        ax_bar.set_xlabel("Transition Probability")
        ax_bar.set_xlim(0, 1.0)
        for i, (k, v) in enumerate(probs_sel.items()):
            ax_bar.text(v + 0.02, i, f"{v:.1%}", va="center", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig_bar)

    with col_sim2:
        st.markdown(f"**Multi-Step Lookahead Projections ($P(A \\to B \\to C)$)**")
        st.write(f"• **Certainty Confidence:** `{conf_sel:.1%}` | **Entropy:** `{entropy_sel:.3f} bits`")
        for path in multi_paths:
            st.markdown(f"`{sel_src}` ➔ `{path[0][0]}` ({path[0][1]:.1%}) ➔ `{path[1][0]}` (cum: {path[1][1]:.1%})")


# ══════════════════════════════════════════════════════════════════════════════
# 4. MEMORY MANAGEMENT (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_memory:
    st.markdown("### 💾 Memory Allocation & Pressure Dynamics")

    m_col1, m_col2 = st.columns([1, 2])
    with m_col1:
        # Budget card
        curr_ram = calm_trace[-1]["total_ram"]
        util_pct = (curr_ram / ram_limit_mb) * 100 if ram_limit_mb > 0 else 0
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-header">Memory Budget Allocation</div>
            <div class="bento-value">{util_pct:.1f}%</div>
            <p style="color:#64748B; font-size:0.85rem; margin-bottom:12px;">Active Memory Utilization</p>
            <div style="background:#E2E8F0; height:8px; border-radius:4px; overflow:hidden; margin-bottom:16px;">
                <div style="background:#2563EB; height:100%; width:{min(100, util_pct)}%;"></div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:8px; font-family:'IBM Plex Mono', monospace; font-size:0.85rem;">
                <div><span style="color:#64748B;">USED</span><br><b>{curr_ram:,} MB</b></div>
                <div><span style="color:#64748B;">FREE</span><br><b>{max(0, ram_limit_mb - curr_ram):,} MB</b></div>
                <div><span style="color:#64748B;">LIMIT</span><br><b>{ram_limit_mb:,} MB</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m_col2:
        st.markdown("**Resident Memory Trajectory vs Budget Limit (MB)**")
        fig_mem, ax_mem = plt.subplots(figsize=(9, 3.8))
        calm_ram = [s["total_ram"] for s in calm_trace]
        lru_ram = [s["total_ram"] for s in sim_data["traces"]["LRU"]]
        reactive_ram = [s["total_ram"] for s in sim_data["traces"]["Reactive"]]

        ax_mem.plot(lru_ram, label="LRU", color="#94A3B8", linewidth=1.2, alpha=0.7)
        ax_mem.plot(reactive_ram, label="Reactive", color="#F59E0B", linewidth=1.2, alpha=0.8)
        ax_mem.plot(calm_ram, label="CALM V2", color="#2563EB", linewidth=1.8)
        ax_mem.axhline(y=ram_limit_mb, color="#EF4444", linestyle="--", label=f"RAM Limit ({ram_limit_mb:,} MB)")
        ax_mem.set_xlabel("Evaluation Event #")
        ax_mem.set_ylabel("RAM (MB)")
        ax_mem.legend(loc="upper right", fontsize=8)
        ax_mem.grid(True, linestyle=":", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig_mem)


# ══════════════════════════════════════════════════════════════════════════════
# 5. BENCHMARK SUITE (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_benchmarks:
    st.markdown("### 🏆 Comprehensive 7-Baseline Benchmark Suite")
    st.caption("Standardized evaluation across all lifecycle strategies under identical evaluation conditions.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown("**Cache Hit Rate (%)**")
        fig_b1, ax_b1 = plt.subplots(figsize=(8, 3.8))
        strat_names = list(sim_data["metrics"].keys())
        hit_values = [sim_data["metrics"][s]["cache_hit_rate_pct"] for s in strat_names]
        colors_b1 = ["#2563EB" if s == "CALM" else "#94A3B8" for s in strat_names]
        ax_b1.bar(strat_names, hit_values, color=colors_b1)
        ax_b1.set_ylabel("Hit Rate (%)")
        ax_b1.set_ylim(0, 100)
        for i, v in enumerate(hit_values):
            ax_b1.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=8)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        st.pyplot(fig_b1)

    with col_b2:
        st.markdown("**Average Launch Latency (seconds)**")
        fig_b2, ax_b2 = plt.subplots(figsize=(8, 3.8))
        lat_values = [sim_data["metrics"][s]["avg_launch_latency_sec"] for s in strat_names]
        colors_b2 = ["#16A34A" if s == "CALM" else "#F59E0B" for s in strat_names]
        ax_b2.bar(strat_names, lat_values, color=colors_b2)
        ax_b2.set_ylabel("Latency (s)")
        for i, v in enumerate(lat_values):
            ax_b2.text(i, v + 0.05, f"{v:.3f}s", ha="center", fontsize=8)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        st.pyplot(fig_b2)


# ══════════════════════════════════════════════════════════════════════════════
# 6. COMPONENT ABLATION (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_ablation:
    st.markdown("### 🧬 Component Ablation Study")
    st.caption("Isolating and quantifying the contribution of each architectural subsystem.")

    ablation_summary_file = os.path.join("results", "processed", "ablation_summary.json")
    if os.path.exists(ablation_summary_file):
        with open(ablation_summary_file, "r") as f:
            abl_data = json.load(f)
        st.dataframe(BenchmarkReporter.format_ablation_table(abl_data), use_container_width=True, hide_index=True)

        fig_abl, ax_abl = plt.subplots(figsize=(10, 4))
        variants = list(abl_data.keys())
        hr_means = [abl_data[v]["hit_rate_mean"] for v in variants]
        hr_stds = [abl_data[v]["hit_rate_std"] for v in variants]
        ax_abl.barh(variants, hr_means, xerr=hr_stds, color="#2563EB", capsize=4)
        ax_abl.set_xlabel("Cache Hit Rate (%)")
        ax_abl.set_title("Ablation Study: Cache Hit Rate by Variant (Mean ± Std across 5 seeds)")
        plt.tight_layout()
        st.pyplot(fig_abl)
    else:
        st.info("Run `python -m calm.benchmark.runner --ablation` to compute ablation statistics.")


# ══════════════════════════════════════════════════════════════════════════════
# 7. AGENT MEMORY (Stitch Console View)
# ══════════════════════════════════════════════════════════════════════════════

with tab_agent:
    st.markdown("### 🤖 Mode B — AI Agent Context Memory Orchestrator")
    st.caption("CALM managing working context, compressed tool outputs, and archival retrieval with real zlib compression.")

    if "agent_engine" not in st.session_state:
        eng = AgentMemoryEngine(token_or_byte_budget=1500)
        eng.register_chunk("task_curr", ItemType.TASK, "Current Task: Memory Subsystem Refactor", "User requested upgrade to CALM V2 architecture with strict temporal evaluation and baseline fairness.", importance=0.95, initial_state=LifecycleState.ACTIVE)
        eng.register_chunk("conv_1", ItemType.CONVERSATION, "Recent Conversation Turn", "User specified: do not remove mobile mode, support both mobile and agent memory in unified engine.", importance=0.85, initial_state=LifecycleState.CACHED)
        eng.register_chunk("dec_1", ItemType.DECISION, "Key Architecture Decision", "Adopt ACTIVE -> CACHED -> COMPRESSED -> ARCHIVED with explicit transition cost modeling.", importance=0.80, initial_state=LifecycleState.CACHED)
        eng.register_chunk("tool_res_1", ItemType.TOOL_RESULT, "Tool Trace: Profiling Logs", json.dumps({"telemetry_events": 400, "access_rate": 0.85, "avg_dwell_time_sec": 120, "burst_spikes": [12, 45, 98, 142]}), importance=0.45, initial_state=LifecycleState.COMPRESSED)
        eng.register_chunk("know_1", ItemType.KNOWLEDGE, "Architecture Reference: Linux Memory Management", "Android Low Memory Killer (LMK) and pressure-stall information (PSI) drivers monitor swap and kernel memory pressure.", importance=0.30, initial_state=LifecycleState.ARCHIVED)
        st.session_state["agent_engine"] = eng

    agent_eng: AgentMemoryEngine = st.session_state["agent_engine"]

    ag_c1, ag_c2, ag_c3 = st.columns(3)
    with ag_c1:
        st.metric("Total Resident Bytes", f"{agent_eng.total_resident_bytes():,} B", f"Budget: {agent_eng.byte_budget:,} B")
    with ag_c2:
        active_cnt = sum(1 for c in agent_eng.chunks.values() if c.state == LifecycleState.ACTIVE)
        st.metric("Active Context Chunks", f"{active_cnt}")
    with ag_c3:
        comp_cnt = sum(1 for c in agent_eng.chunks.values() if c.state == LifecycleState.COMPRESSED)
        st.metric("Compressed Chunks (zlib)", f"{comp_cnt}")

    st.markdown("---")
    st.markdown("#### 🗂 Agent Context Chunks Table")
    st.dataframe(pd.DataFrame(agent_eng.get_summary_table()), use_container_width=True, hide_index=True)

    st.markdown("#### ⚡ Query & Retrieve Context Chunk")
    sel_chunk_id = st.selectbox("Select context chunk to query/inject:", list(agent_eng.chunks.keys()), key="ag_chunk_sel")
    if st.button("🚀 Access / Inject Context Chunk", key="ag_access_btn"):
        retrieved_content = agent_eng.access_chunk(sel_chunk_id)
        st.success(f"Chunk `{sel_chunk_id}` promoted to ACTIVE. Content retrieved & decompressed:")
        st.code(retrieved_content)
        st.rerun()
