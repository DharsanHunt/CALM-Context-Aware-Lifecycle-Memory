"""
server.py — Python REST API Server for CALM V2 & React Console (Powered by Flask).
Exposes simulation, prediction, lifecycle management, benchmarks, and agent memory endpoints,
and serves the React production frontend from frontend/dist.

Run with: python server.py
"""

import os
import json
from flask import Flask, request, jsonify, send_from_directory

from calm.utils.config import (
    CALMConfig,
    DEFAULT_APPS,
    DEFAULT_APP_RAM,
    PRESET_NAMES,
    PRESETS,
    get_preset_config,
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
from calm.benchmark.metrics import BenchmarkMetricsCalculator
from calm.adapters.agent import AgentMemoryEngine
from calm.models.memory_item import ItemType
from calm.models.app_state import LifecycleState


# Paths
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")


# ── CORS Middleware ──────────────────────────────────────────────────────────

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/<path:dummy>", methods=["OPTIONS"])
def handle_options(dummy):
    return "", 200


# ── Global Agent Engine Instance ─────────────────────────────────────────────

agent_engine = AgentMemoryEngine(token_or_byte_budget=1500)
agent_engine.register_chunk(
    "task_curr", ItemType.TASK, "Current Task: Memory Subsystem Refactor",
    "User requested upgrade to CALM V2 architecture with strict temporal evaluation and baseline fairness.",
    importance=0.95, initial_state=LifecycleState.ACTIVE
)
agent_engine.register_chunk(
    "conv_1", ItemType.CONVERSATION, "Recent Conversation Turn",
    "User specified: do not remove mobile mode, support both mobile and agent memory in unified engine.",
    importance=0.85, initial_state=LifecycleState.CACHED
)
agent_engine.register_chunk(
    "dec_1", ItemType.DECISION, "Key Architecture Decision",
    "Adopt ACTIVE -> CACHED -> COMPRESSED -> ARCHIVED with explicit transition cost modeling.",
    importance=0.80, initial_state=LifecycleState.CACHED
)
agent_engine.register_chunk(
    "tool_res_1", ItemType.TOOL_RESULT, "Tool Trace: Profiling Logs",
    json.dumps({"telemetry_events": 400, "access_rate": 0.85, "avg_dwell_time_sec": 120, "burst_spikes": [12, 45, 98, 142]}),
    importance=0.45, initial_state=LifecycleState.COMPRESSED
)
agent_engine.register_chunk(
    "know_1", ItemType.KNOWLEDGE, "Architecture Reference: Linux Memory Management",
    "Android Low Memory Killer (LMK) and pressure-stall information (PSI) drivers monitor swap and kernel memory pressure.",
    importance=0.30, initial_state=LifecycleState.ARCHIVED
)


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def get_health():
    return jsonify({"status": "online", "version": "2.0.0", "engine": "CALM V2"})


@app.route("/api/config/presets", methods=["GET"])
def get_presets():
    return jsonify({
        "presets": PRESET_NAMES,
        "details": {
            k: {
                "ram_limit_mb": v["ram_limit_mb"],
                "app_ram": v["app_ram"],
                "compressed_factor": v["storage"].compressed_ram_factor,
            }
            for k, v in PRESETS.items()
        },
        "default_apps": DEFAULT_APPS,
        "default_app_ram": DEFAULT_APP_RAM,
    })


@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    req = request.get_json(force=True) or {}
    workload_type_str = req.get("workload_type", "predictable")
    num_events = int(req.get("num_events", 350))
    seed = int(req.get("seed", 42))
    ram_limit_mb = int(req.get("ram_limit_mb", 2500))
    compressed_factor = float(req.get("compressed_factor", 0.35))
    aggression = req.get("aggression", "Less Aggressive")
    mode = req.get("mode", "mobile")

    try:
        w_type = WorkloadType(workload_type_str)
    except ValueError:
        w_type = WorkloadType.PREDICTABLE

    cfg = CALMConfig(
        mode=mode,
        ram_limit_mb=ram_limit_mb,
        app_ram=dict(DEFAULT_APP_RAM),
        aggression=aggression,
    )
    cfg.storage.compressed_ram_factor = compressed_factor

    # 1. Workload generation
    workload_seq = WorkloadGenerator.generate(
        workload_type=w_type,
        num_events=num_events,
        seed=seed,
        apps=DEFAULT_APPS,
        app_ram=cfg.app_ram,
    )

    # 2. Strict temporal split (70% train, 15% val, 15% test)
    train_seq, val_seq, test_seq = temporal_split(workload_seq, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    eval_events = val_seq.events + test_seq.events
    eval_items = [e.item_id for e in eval_events]

    # 3. Train Markov predictor on historical train sequence
    predictor = MarkovPredictor(smoothing_alpha=cfg.prediction.smoothing_alpha)
    train_items = [e.item_id for e in train_seq.events]
    predictor.fit(train_items, all_items=DEFAULT_APPS)

    pred_metrics = PredictionEvaluator.evaluate(predictor, eval_items, top_k=cfg.prediction.top_k)

    # 4. Run all strategies
    strategy_traces = {}
    strategy_metrics = {}

    for strat_name in STRATEGY_NAMES:
        strat = create_strategy(strat_name, cfg, DEFAULT_APPS, seed=seed)
        step_results = []
        for event in eval_events:
            req_item = event.item_id
            pred_res = predictor.predict(req_item, top_k=cfg.prediction.top_k)
            step_res = strat.step(requested_item=req_item, prediction_result=pred_res)
            step_results.append(step_res)

        metrics = BenchmarkMetricsCalculator.calculate(
            strategy_name=strat_name,
            workload_name=w_type.value,
            seed=seed,
            step_results=step_results,
            ram_limit_mb=cfg.ram_limit_mb,
            prediction_metrics=pred_metrics,
        )

        serialized_trace = []
        for s in step_results:
            post_st = {k: (v.value if hasattr(v, "value") else str(v)) for k, v in s["post_states"].items()}
            pre_st = s["pre_launch_state"].value if hasattr(s["pre_launch_state"], "value") else str(s["pre_launch_state"])
            serialized_trace.append({
                "tick": s["tick"],
                "requested_item": s["requested_item"],
                "pre_launch_state": pre_st,
                "is_cache_hit": s["is_cache_hit"],
                "launch_latency": s["launch_latency"],
                "post_states": post_st,
                "total_ram": s["total_ram"],
                "reclaimed_mb": s.get("reclaimed_mb", 0.0),
                "priority_scores": s.get("priority_scores", {}),
            })

        strategy_traces[strat_name] = serialized_trace
        strategy_metrics[strat_name] = metrics.to_dict()

    # Transition probability matrix dict
    trans_matrix = {}
    for src in DEFAULT_APPS:
        probs = predictor.get_transition_probabilities(src)
        trans_matrix[src] = {dst: round(probs.get(dst, 0.0), 3) for dst in DEFAULT_APPS}

    # Multi-step paths for each app
    lookaheads = {}
    for app_name in DEFAULT_APPS:
        paths = predictor.predict_multi_step(app_name, steps=2, top_k_per_step=2)
        lookaheads[app_name] = paths

    return jsonify({
        "workload_type": w_type.value,
        "seed": seed,
        "num_events": num_events,
        "eval_len": len(eval_events),
        "pred_metrics": pred_metrics,
        "transition_matrix": trans_matrix,
        "lookaheads": lookaheads,
        "traces": strategy_traces,
        "metrics": strategy_metrics,
        "config": cfg.to_dict(),
    })


@app.route("/api/benchmarks/summary", methods=["GET"])
def get_benchmark_summary():
    summary_path = os.path.join("results", "processed", "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Summary not found"}), 404


@app.route("/api/benchmarks/ablation", methods=["GET"])
def get_ablation_summary():
    ablation_path = os.path.join("results", "processed", "ablation_summary.json")
    if os.path.exists(ablation_path):
        with open(ablation_path, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Ablation summary not found"}), 404


@app.route("/api/agent/chunks", methods=["GET"])
def get_agent_chunks():
    return jsonify({
        "total_resident_bytes": agent_engine.total_resident_bytes(),
        "byte_budget": agent_engine.byte_budget,
        "chunks": agent_engine.get_summary_table(),
    })


@app.route("/api/agent/access", methods=["POST"])
def access_agent_chunk():
    req = request.get_json(force=True) or {}
    chunk_id = req.get("chunk_id")
    if not chunk_id:
        return jsonify({"error": "Missing chunk_id"}), 400
    content = agent_engine.access_chunk(chunk_id)
    if content is None:
        return jsonify({"error": f"Chunk {chunk_id} not found"}), 404
    return jsonify({
        "chunk_id": chunk_id,
        "content": content,
        "total_resident_bytes": agent_engine.total_resident_bytes(),
        "chunks": agent_engine.get_summary_table(),
    })


# ── Serve Built React Frontend ───────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    elif os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return send_from_directory(FRONTEND_DIST, "index.html")
    else:
        return "CALM V2 API is online. Build the frontend with 'cd frontend && npm run build'.", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 CALM V2 React + Flask Console running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
