"""
CALM V2 — Research & Engineering Platform Dashboard
Interactive visualization, lifecycle monitoring, prediction telemetry, multi-seed benchmarking,
ablation studies, and AI Agent Context Memory demonstration.

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

# Ensure repository root is on sys.path
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


# ── Page Configuration & CSS Styling ─────────────────────────────────────────

st.set_page_config(
    page_title="CALM V2 — Context-Aware Lifecycle Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .kpi-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar Controls ─────────────────────────────────────────────────────────

st.sidebar.title("🧠 CALM V2 Control Plane")
st.sidebar.caption("Context-Aware Lifecycle Memory Platform")

mode = st.sidebar.radio(
    "Execution Mode",
    ["📱 Mode A — Mobile Application Memory", "🤖 Mode B — AI Agent Context Memory"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Memory & Aggression Profile")

aggression = st.sidebar.selectbox(
    "Aggression Preset",
    PRESET_NAMES,
    index=PRESET_NAMES.index("Less Aggressive"),
    help="Select a standard system aggression profile.",
)

preset_cfg = get_preset_config(aggression)

ram_limit_mb = st.sidebar.number_input(
    "System Memory Limit (MB)",
    min_value=500,
    max_value=16000,
    value=preset_cfg.ram_limit_mb,
    step=100,
    help="Total resident memory budget.",
)

compressed_factor = st.sidebar.slider(
    "Compressed Memory Factor",
    min_value=0.10,
    max_value=0.60,
    value=preset_cfg.storage.compressed_ram_factor,
    step=0.05,
    help="Fraction of base memory occupied when an item is in COMPRESSED state.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Workload Configuration")

workload_choice = st.sidebar.selectbox(
    "Workload Archetype",
    [w.value for w in WorkloadType],
    index=0,
    help="Select empirical access pattern.",
)

num_events = st.sidebar.slider("Sequence Length (Events)", 150, 600, 350, step=50)
seed = st.sidebar.number_input("Random Seed", min_value=1, max_value=9999, value=42, step=1)

run_button = st.sidebar.button("▶ Run CALM V2 Simulation", type="primary", use_container_width=True)

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
    """Executes a full comparative simulation across CALM and baselines."""
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

    # 1. Train Markov Predictor strictly on historical train sequence
    predictor = MarkovPredictor(smoothing_alpha=cfg.prediction.smoothing_alpha)
    train_items = [e.item_id for e in train_seq.events]
    predictor.fit(train_items, all_items=DEFAULT_APPS)

    # 2. Evaluate Prediction Accuracy
    pred_metrics = PredictionEvaluator.evaluate(predictor, eval_items, top_k=cfg.prediction.top_k)

    # 3. Run all strategies on identical eval events
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


# Auto-run initial simulation if not present
if "sim_results" not in st.session_state or run_button:
    with st.spinner("Executing CALM V2 Lifecycle Engine & Baselines..."):
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
    "ACTIVE": "#22C55E",
    "CACHED": "#3B82F6",
    "COMPRESSED": "#F59E0B",
    "ARCHIVED": "#EF4444",
}


# ── Main Header ──────────────────────────────────────────────────────────────

st.markdown('<div class="main-header">🧠 CALM V2 — Context-Aware Lifecycle Memory</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Predictive, Multi-Tier Lifecycle Memory Orchestrator for Mobile Applications & AI Agent Systems</div>',
    unsafe_allow_html=True,
)


# ── Navigation Tabs ──────────────────────────────────────────────────────────

tab_overview, tab_lifecycle, tab_prediction, tab_benchmark, tab_ablation, tab_agent = st.tabs([
    "🔬 System Overview",
    "📈 Lifecycle & Memory Monitor",
    "🔮 Prediction & Confidence",
    "🏆 Benchmark Suite",
    "🧬 Component Ablation",
    "🤖 AI Agent Memory Demo",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SYSTEM OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.subheader("📊 Key Performance Telemetry")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        hit_delta = calm_metrics["cache_hit_rate_pct"] - lru_metrics["cache_hit_rate_pct"]
        st.metric("Cache Hit Rate", f"{calm_metrics['cache_hit_rate_pct']:.1f}%", f"{hit_delta:+.1f}% vs LRU")
    with c2:
        lat_delta = (lru_metrics["avg_launch_latency_sec"] - calm_metrics["avg_launch_latency_sec"]) / lru_metrics["avg_launch_latency_sec"] * 100.0 if lru_metrics["avg_launch_latency_sec"] > 0 else 0.0
        st.metric("Avg Launch Latency", f"{calm_metrics['avg_launch_latency_sec']:.3f}s", f"-{lat_delta:.1f}% vs LRU", delta_color="normal")
    with c3:
        thrash_delta = lru_metrics["thrashing_count"] - calm_metrics["thrashing_count"]
        st.metric("Thrashing Events", f"{calm_metrics['thrashing_count']}", f"-{thrash_delta} vs LRU", delta_color="normal")
    with c4:
        st.metric("Peak Memory", f"{calm_metrics['peak_ram_mb']:,.0f} MB", f"Budget: {ram_limit_mb:,} MB")
    with c5:
        st.metric("Top-3 Prediction Acc", f"{pred_metrics['top_3_accuracy']:.1f}%", f"Conf: {pred_metrics['mean_confidence']:.1%}")

    st.markdown("---")

    col_sum1, col_sum2 = st.columns([3, 2])

    with col_sum1:
        st.markdown("#### 📋 Strategy Performance Summary")
        summary_rows = []
        for s in STRATEGY_NAMES:
            m = sim_data["metrics"][s]
            summary_rows.append({
                "Strategy": s,
                "Hit Rate (%)": f"{m['cache_hit_rate_pct']:.1f}%",
                "Avg Latency (s)": f"{m['avg_launch_latency_sec']:.4f}s",
                "P95 Latency (s)": f"{m['p95_launch_latency_sec']:.4f}s",
                "Avg RAM (MB)": f"{m['avg_ram_mb']:,.0f}",
                "Memory-Time": f"{m['memory_time_mb_ticks']:,.0f}",
                "Thrashing": m["thrashing_count"],
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    with col_sum2:
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
                "Lifecycle State": st_str,
                "Resident RAM": f"{eff_ram} MB",
                "Priority Score": f"{p_score:.3f}",
            })
        st.dataframe(pd.DataFrame(snap_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: LIFECYCLE & MEMORY MONITOR
# ══════════════════════════════════════════════════════════════════════════════

with tab_lifecycle:
    st.subheader("📈 Real-Time Lifecycle & Memory Trajectory")

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("**Resident Memory Over Time (MB)**")
        fig_mem, ax_mem = plt.subplots(figsize=(9, 4))
        
        calm_ram = [s["total_ram"] for s in calm_trace]
        lru_ram = [s["total_ram"] for s in sim_data["traces"]["LRU"]]
        reactive_ram = [s["total_ram"] for s in sim_data["traces"]["Reactive"]]

        ax_mem.plot(lru_ram, label="LRU", color="#94A3B8", linewidth=1.2, alpha=0.7)
        ax_mem.plot(reactive_ram, label="Reactive", color="#F59E0B", linewidth=1.2, alpha=0.8)
        ax_mem.plot(calm_ram, label="CALM V2", color="#2563EB", linewidth=1.8)
        ax_mem.axhline(y=ram_limit_mb, color="#EF4444", linestyle="--", label=f"RAM Budget ({ram_limit_mb:,} MB)")
        ax_mem.set_xlabel("Evaluation Event #")
        ax_mem.set_ylabel("RAM (MB)")
        ax_mem.set_title("Memory Consumption Comparison")
        ax_mem.legend(loc="upper right", fontsize=8)
        ax_mem.grid(True, linestyle=":", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig_mem)

    with col_l2:
        st.markdown("**State Distribution Breakdown (% of Total Ticks)**")
        fig_pie, (ax_p1, ax_p2) = plt.subplots(1, 2, figsize=(9, 4))
        
        lru_dist = lru_metrics["state_distribution"]
        calm_dist = calm_metrics["state_distribution"]

        labels = ["ACTIVE", "CACHED", "COMPRESSED", "ARCHIVED"]
        colors = [state_colors[s] for s in labels]

        ax_p1.pie([lru_dist.get(s, 0) for s in labels], labels=labels, colors=colors, autopct="%1.0f%%", textprops={"fontsize": 8})
        ax_p1.set_title("LRU Baseline", fontsize=10)

        ax_p2.pie([calm_dist.get(s, 0) for s in labels], labels=labels, colors=colors, autopct="%1.0f%%", textprops={"fontsize": 8})
        ax_p2.set_title("CALM V2 (Proactive)", fontsize=10)
        plt.tight_layout()
        st.pyplot(fig_pie)

    st.markdown("---")

    st.markdown("**Item Lifecycle State Progression Matrix**")
    # Build timeline matrix
    timeline_records = []
    for step in calm_trace[:100]:  # First 100 events
        t_idx = step["tick"]
        row = {"Tick": t_idx, "Requested": step["requested_item"]}
        for app in DEFAULT_APPS:
            st_val = step["post_states"][app]
            row[app] = st_val.value if hasattr(st_val, "value") else str(st_val)
        timeline_records.append(row)

    st.dataframe(pd.DataFrame(timeline_records).head(50), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: PREDICTION & CONFIDENCE
# ══════════════════════════════════════════════════════════════════════════════

with tab_prediction:
    st.subheader("🔮 Predictive Modeling & Uncertainty Quantification")

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
        st.markdown("**Prediction Evaluation (Zero Data Leakage)**")
        st.metric("Top-1 Prediction Accuracy", f"{pred_metrics['top_1_accuracy']:.1f}%")
        st.metric("Top-3 Prediction Accuracy", f"{pred_metrics['top_3_accuracy']:.1f}%")
        st.metric("Mean Predictive Confidence", f"{pred_metrics['mean_confidence']:.2%}")
        st.metric("Brier Uncertainty Score", f"{pred_metrics['brier_score']:.4f}")

    st.markdown("---")

    st.markdown("#### 🎯 Interactive Lookahead Simulator")
    selected_src = st.selectbox("Select Current Foreground Item:", DEFAULT_APPS, key="lookahead_sel")

    probs_sel = predictor.get_transition_probabilities(selected_src)
    conf_sel = ConfidenceScorer.calculate_confidence(probs_sel)
    entropy_sel = ConfidenceScorer.calculate_entropy(probs_sel)
    multi_paths = predictor.predict_multi_step(selected_src, steps=2, top_k_per_step=2)

    col_sim1, col_sim2 = st.columns(2)

    with col_sim1:
        st.markdown(f"**Single-Step Distribution from `{selected_src}`**")
        fig_bar, ax_bar = plt.subplots(figsize=(8, 3))
        ax_bar.barh(list(probs_sel.keys()), list(probs_sel.values()), color=[app_colors.get(a, "#999") for a in probs_sel.keys()])
        ax_bar.set_xlabel("Transition Probability")
        ax_bar.set_xlim(0, 1.0)
        for i, (k, v) in enumerate(probs_sel.items()):
            ax_bar.text(v + 0.02, i, f"{v:.1%}", va="center", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig_bar)

    with col_sim2:
        st.markdown(f"**Multi-Step Lookahead Projections ($P(A \\to B \\to C)$)**")
        st.write(f"• **Confidence:** `{conf_sel:.1%}` | **Entropy:** `{entropy_sel:.3f} bits`")
        for path in multi_paths:
            path_str = f"`{selected_src}` ➔ `{path[0][0]}` ({path[0][1]:.1%}) ➔ `{path[1][0]}` (cum: {path[1][1]:.1%})"
            st.markdown(path_str)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: BENCHMARK SUITE
# ══════════════════════════════════════════════════════════════════════════════

with tab_benchmark:
    st.subheader("🏆 Multi-Baseline Benchmark Comparison")
    st.caption("Standardized evaluation across all 7 lifecycle management strategies.")

    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.markdown("**Cache Hit Rate Comparison (%)**")
        fig_b1, ax_b1 = plt.subplots(figsize=(8, 4))
        strat_names = list(sim_data["metrics"].keys())
        hit_values = [sim_data["metrics"][s]["cache_hit_rate_pct"] for s in strat_names]
        colors_b1 = ["#2563EB" if s == "CALM" else "#94A3B8" for s in strat_names]
        ax_b1.bar(strat_names, hit_values, color=colors_b1)
        ax_b1.set_ylabel("Cache Hit Rate (%)")
        ax_b1.set_ylim(0, 100)
        for i, v in enumerate(hit_values):
            ax_b1.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=8)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        st.pyplot(fig_b1)

    with col_b2:
        st.markdown("**Launch Latency Comparison (seconds)**")
        fig_b2, ax_b2 = plt.subplots(figsize=(8, 4))
        lat_values = [sim_data["metrics"][s]["avg_launch_latency_sec"] for s in strat_names]
        colors_b2 = ["#22C55E" if s == "CALM" else "#F59E0B" for s in strat_names]
        ax_b2.bar(strat_names, lat_values, color=colors_b2)
        ax_b2.set_ylabel("Avg Launch Latency (s)")
        for i, v in enumerate(lat_values):
            ax_b2.text(i, v + 0.05, f"{v:.3f}s", ha="center", fontsize=8)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        st.pyplot(fig_b2)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: COMPONENT ABLATION STUDIES
# ══════════════════════════════════════════════════════════════════════════════

with tab_ablation:
    st.subheader("🧬 Component Ablation Analysis")
    st.caption("Quantifying the individual contribution of each CALM mechanism.")

    ablation_summary_file = os.path.join("results", "processed", "ablation_summary.json")
    if os.path.exists(ablation_summary_file):
        with open(ablation_summary_file, "r") as f:
            abl_data = json.load(f)
        st.dataframe(BenchmarkReporter.format_ablation_table(abl_data), use_container_width=True, hide_index=True)

        fig_abl, ax_abl = plt.subplots(figsize=(10, 4))
        variants = list(abl_data.keys())
        hr_means = [abl_data[v]["hit_rate_mean"] for v in variants]
        hr_stds = [abl_data[v]["hit_rate_std"] for v in variants]
        ax_abl.barh(variants, hr_means, xerr=hr_stds, color="#3B82F6", capsize=4)
        ax_abl.set_xlabel("Cache Hit Rate (%)")
        ax_abl.set_title("Ablation Study: Cache Hit Rate by Variant (Mean ± Std across 5 seeds)")
        plt.tight_layout()
        st.pyplot(fig_abl)
    else:
        st.info("Run `python -m calm.benchmark.runner --ablation` to generate statistical ablation summaries.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: AI AGENT CONTEXT MEMORY DEMO
# ══════════════════════════════════════════════════════════════════════════════

with tab_agent:
    st.subheader("🤖 Mode B — AI Agent Context Memory Orchestrator")
    st.caption("CALM managing LLM working context, compressed tool outputs, and archival retrieval.")

    # Initialize Agent Demo Engine in Session State
    if "agent_engine" not in st.session_state:
        eng = AgentMemoryEngine(token_or_byte_budget=1500)
        # Register sample agent context items
        eng.register_chunk("task_curr", ItemType.TASK, "Current Task: Refactor Memory Module", "User requested upgrade to CALM V2 architecture with strict temporal evaluation and baseline fairness.", importance=0.95, initial_state=LifecycleState.ACTIVE)
        eng.register_chunk("conv_1", ItemType.CONVERSATION, "Recent Conversation: User Feedback", "User specified: do not remove mobile mode, support both mobile and agent memory in unified engine.", importance=0.85, initial_state=LifecycleState.CACHED)
        eng.register_chunk("dec_1", ItemType.DECISION, "Key Decision: 4-Tier Lifecycle", "Adopt ACTIVE -> CACHED -> COMPRESSED -> ARCHIVED with explicit transition cost modeling.", importance=0.80, initial_state=LifecycleState.CACHED)
        eng.register_chunk("tool_res_1", ItemType.TOOL_RESULT, "Tool Result: Telemetry Profiling Trace", json.dumps({"telemetry_events": 400, "access_rate": 0.85, "avg_dwell_time_sec": 120, "burst_spikes": [12, 45, 98, 142]}), importance=0.45, initial_state=LifecycleState.COMPRESSED)
        eng.register_chunk("know_1", ItemType.KNOWLEDGE, "Architecture Doc: Linux & Android Memory Subsystems", "Android Low Memory Killer (LMK) and pressure-stall information (PSI) drivers monitor swap and kernel memory pressure.", importance=0.30, initial_state=LifecycleState.ARCHIVED)
        st.session_state["agent_engine"] = eng

    agent_eng: AgentMemoryEngine = st.session_state["agent_engine"]

    c_ag1, c_ag2, c_ag3 = st.columns(3)
    with c_ag1:
        st.metric("Total Resident Bytes", f"{agent_eng.total_resident_bytes():,} Bytes", f"Budget: {agent_eng.byte_budget:,} Bytes")
    with c_ag2:
        active_cnt = sum(1 for c in agent_eng.chunks.values() if c.state == LifecycleState.ACTIVE)
        st.metric("Active Context Chunks", f"{active_cnt}")
    with c_ag3:
        comp_cnt = sum(1 for c in agent_eng.chunks.values() if c.state == LifecycleState.COMPRESSED)
        st.metric("Compressed Chunks (zlib)", f"{comp_cnt}")

    st.markdown("---")

    st.markdown("#### 🗂 Agent Context Chunks Table")
    st.dataframe(pd.DataFrame(agent_eng.get_summary_table()), use_container_width=True, hide_index=True)

    st.markdown("#### ⚡ Query & Retrieve Context Chunk")
    sel_chunk_id = st.selectbox("Select context chunk to query/inject:", list(agent_eng.chunks.keys()))
    if st.button("🚀 Access / Inject Context Chunk"):
        retrieved_content = agent_eng.access_chunk(sel_chunk_id)
        st.success(f"Chunk `{sel_chunk_id}` promoted to ACTIVE. Content retrieved & decompressed:")
        st.code(retrieved_content)
        st.rerun()
