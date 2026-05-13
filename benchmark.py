"""benchmark.py — Measure all 7 KPIs against targets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import APPS, LAUNCH_TIME
from config import SystemConfig, get_preset
from simulator import generate_usage_logs
from predictor import MarkovPredictor
from allocator import compute_priority_scores
from cache import LifecycleEngine, CacheManager
from metrics import compute_cache_efficiency

TARGETS = {
    "load_time_improvement": 20.0,
    "launch_time_improvement": 10.0,
    "thrashing_reduction": 50.0,
    "stability_issues": 0,
    "prediction_accuracy": 75.0,
    "cache_hit_rate": 85.0,
    "memory_efficiency_improvement": 30.0,
}


def run_benchmark(preset_name="Less Aggressive", num_events=350, seed=42):
    preset = get_preset(preset_name)
    cfg = SystemConfig(**preset, aggression=preset_name)
    logs = generate_usage_logs(num_events=num_events, seed=seed)
    predictor = MarkovPredictor()
    predictor.train_transition_matrix(logs)

    # ── Baseline ─────────────────────────────────────────────────────────
    baseline = CacheManager(cfg)
    b_launch_states, b_hits, b_thrash, b_ram = [], [], [], []
    b_prev_evicted = set()

    for idx in range(len(logs)):
        app = logs.loc[idx, "app"]
        old = baseline.app_state[app]
        b_launch_states.append(old)
        b_hits.append(old in ("ACTIVE", "CACHED", "COMPRESSED"))
        b_thrash.append(old == "EVICTED" and app in b_prev_evicted)
        baseline.activate_app(app)
        baseline.enforce_ram_limit({a: 0.5 for a in APPS}, app)
        for a in APPS:
            if a != app and baseline.app_state[a] == "ACTIVE":
                baseline.set_state(a, "CACHED")
        b_ram.append(baseline.total_ram())
        b_prev_evicted = {a for a in APPS if baseline.app_state[a] == "EVICTED"}

    # ── Adaptive ─────────────────────────────────────────────────────────
    adaptive = LifecycleEngine(cfg)
    a_post_launch = []      # state of foreground app AFTER update (for launch time)
    a_post_hits = []        # was the app in a cached state AFTER update?
    a_thrash = []
    a_ram = []
    a_post_states = []
    a_preds_top3_correct = []  # was actual next app in top-3 predictions?
    a_prev_evicted = set()

    for idx in range(len(logs)):
        app = logs.loc[idx, "app"]
        predicted = predictor.predict_next_app(app)
        pred_scores = predictor.get_transition_probabilities(app)
        scores = compute_priority_scores(logs, idx, predictor)

        # Prediction accuracy: top-3 matching
        if idx < len(logs) - 1:
            actual_next = logs.loc[idx + 1, "app"]
            top3 = [a for a, _ in predictor.predict_top_n(app, 3)]
            a_preds_top3_correct.append(actual_next in top3)

        old = adaptive.app_state[app]
        # Hit rate: was the app already cached BEFORE the update?
        a_post_hits.append(old in ("ACTIVE", "CACHED", "COMPRESSED"))
        a_thrash.append(old == "EVICTED" and app in a_prev_evicted)

        post = adaptive.update(app, scores, predicted, pred_scores)
        a_post_states.append(post)

        # Launch time: use post-update state (what the user actually experiences)
        post_state = post[app]
        a_post_launch.append(post_state)

        a_ram.append(adaptive.total_ram())
        a_prev_evicted = {a for a in APPS if adaptive.app_state[a] == "EVICTED"}

    n = len(logs)

    # ── KPI 1 & 2: Load / Launch Time Improvement ───────────────────────
    b_avg_launch = sum(LAUNCH_TIME[s] for s in b_launch_states) / n
    a_avg_launch = sum(LAUNCH_TIME[s] for s in a_post_launch) / n
    load_time_improvement = ((b_avg_launch - a_avg_launch) / b_avg_launch * 100) if b_avg_launch > 0 else 0

    # ── KPI 3: Thrashing Reduction ──────────────────────────────────────
    b_thrash_count = sum(b_thrash)
    a_thrash_count = sum(a_thrash)
    thrash_reduction = ((b_thrash_count - a_thrash_count) / b_thrash_count * 100) if b_thrash_count > 0 else 0

    # ── KPI 4: System Stability ─────────────────────────────────────────
    stability_issues = 0
    for r in a_ram:
        if r > cfg.ram_limit * 1.05 or r < 0:
            stability_issues += 1

    # ── KPI 5: Prediction Accuracy (top-3) ──────────────────────────────
    prediction_accuracy = (sum(a_preds_top3_correct) / len(a_preds_top3_correct) * 100) if a_preds_top3_correct else 0

    # ── KPI 6: Cache Hit Rate (post-update) ─────────────────────────────
    cache_hit_rate_adaptive = sum(a_post_hits) / n * 100 if n else 0

    # ── KPI 7: Memory Utilization Efficiency ────────────────────────────
    # Reduction in EVICTED states = better memory utilization
    b_evicted_pct = sum(1 for s in b_launch_states if s == "EVICTED") / n * 100
    a_evicted_pct = sum(1 for s in a_post_launch if s == "EVICTED") / n * 100
    mem_efficiency = ((b_evicted_pct - a_evicted_pct) / b_evicted_pct * 100) if b_evicted_pct > 0 else 0

    results = {
        "load_time_improvement": round(load_time_improvement, 1),
        "launch_time_improvement": round(load_time_improvement, 1),
        "thrashing_reduction": round(thrash_reduction, 1),
        "stability_issues": stability_issues,
        "prediction_accuracy": round(prediction_accuracy, 1),
        "cache_hit_rate": round(cache_hit_rate_adaptive, 1),
        "memory_efficiency_improvement": round(mem_efficiency, 1),
    }

    return results, TARGETS


def print_report(results, targets):
    print("\n" + "=" * 70)
    print("  KPI BENCHMARK REPORT")
    print("=" * 70)
    print(f"  {'KPI':<42} {'Target':>8} {'Actual':>8} {'Status':>8}")
    print("-" * 70)

    checks = [
        ("Load Time Improvement (%)", "load_time_improvement", ">="),
        ("Launch Time Improvement (%)", "launch_time_improvement", ">="),
        ("Thrashing Reduction (%)", "thrashing_reduction", ">="),
        ("Stability Issues", "stability_issues", "<="),
        ("Prediction Accuracy (%)", "prediction_accuracy", ">="),
        ("Cache Hit Rate (%)", "cache_hit_rate", ">="),
        ("Memory Efficiency Improvement (%)", "memory_efficiency_improvement", ">="),
    ]

    all_pass = True
    for label, key, op in checks:
        target = targets[key]
        actual = results[key]
        passed = (actual >= target) if op == ">=" else (actual <= target)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {label:<42} {target:>8} {actual:>8} {status:>8}")

    print("-" * 70)
    print(f"  {'OVERALL':<42} {'':>8} {'':>8} {'PASS' if all_pass else 'FAIL':>8}")
    print("=" * 70)
    return all_pass


if __name__ == "__main__":
    for preset in ["No Aggression", "Less Aggressive", "Aggressive", "Critical"]:
        print(f"\n{'#' * 70}")
        print(f"  PRESET: {preset}")
        print(f"{'#' * 70}")
        results, targets = run_benchmark(preset)
        print_report(results, targets)
