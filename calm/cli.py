"""
calm.cli — Unified Command-Line Interface for CALM V2.
Provides commands for running simulations, multi-seed benchmarks, real OS monitoring,
LLM context optimization, and launching the research console.
"""

import sys
import os
import argparse
import json
from typing import List

from calm.utils.config import CALMConfig, DEFAULT_APPS, DEFAULT_APP_RAM, get_preset_config
from calm.telemetry.workload import WorkloadGenerator, WorkloadType, temporal_split
from calm.prediction.markov import MarkovPredictor
from calm.prediction.evaluation import PredictionEvaluator
from calm.benchmark.baselines import create_strategy, STRATEGY_NAMES
from calm.benchmark.metrics import BenchmarkMetricsCalculator
from calm.benchmark.runner import BenchmarkRunner
from calm.benchmark.report import BenchmarkReporter
from calm.adapters.real_os import RealOSTelemetryAdapter
from calm.adapters.llm_context import LLMContextManager, ItemType


def cmd_simulate(args: argparse.Namespace) -> None:
    """Runs a single comparative simulation on an unseen evaluation sequence."""
    w_type = WorkloadType(args.workload)
    cfg = CALMConfig(
        mode=args.mode,
        ram_limit_mb=args.budget,
        app_ram=dict(DEFAULT_APP_RAM),
        aggression=args.aggression,
    )

    print(f"\n=======================================================")
    print(f"  CALM V2 Simulation: Workload={w_type.value}, Budget={args.budget} MB, Seed={args.seed}")
    print(f"=======================================================\n")

    seq = WorkloadGenerator.generate(
        workload_type=w_type,
        num_events=args.events,
        seed=args.seed,
        apps=DEFAULT_APPS,
        app_ram=cfg.app_ram,
    )

    train_seq, val_seq, test_seq = temporal_split(seq, 0.70, 0.15, 0.15)
    eval_events = val_seq.events + test_seq.events
    eval_items = [e.item_id for e in eval_events]

    predictor = MarkovPredictor(smoothing_alpha=cfg.prediction.smoothing_alpha)
    predictor.fit([e.item_id for e in train_seq.events], all_items=DEFAULT_APPS)
    pred_metrics = PredictionEvaluator.evaluate(predictor, eval_items, top_k=cfg.prediction.top_k)

    print(f"[PREDICTION] Top-1 Acc: {pred_metrics['top_1_accuracy']:.1f}%, Top-3 Acc: {pred_metrics['top_3_accuracy']:.1f}%, Mean Certainty: {pred_metrics['mean_confidence']:.1%}\n")

    results = []
    for strat_name in STRATEGY_NAMES:
        strat = create_strategy(strat_name, cfg, DEFAULT_APPS, seed=args.seed)
        step_results = []
        for event in eval_events:
            p_res = predictor.predict(event.item_id, top_k=cfg.prediction.top_k)
            res = strat.step(requested_item=event.item_id, prediction_result=p_res)
            step_results.append(res)

        m = BenchmarkMetricsCalculator.calculate(
            strategy_name=strat_name,
            workload_name=w_type.value,
            seed=args.seed,
            step_results=step_results,
            ram_limit_mb=cfg.ram_limit_mb,
            prediction_metrics=pred_metrics,
        )
        results.append(m)

    print(BenchmarkReporter.format_comparison_table(results))


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Runs full multi-seed benchmark runner across all workloads and baselines."""
    runner = BenchmarkRunner(
        seeds=args.seeds,
        workload_types=[w.value for w in WorkloadType] if "all" in args.workloads else args.workloads,
        events_per_workload=args.events,
    )
    runner.run_all()


def cmd_ablation(args: argparse.Namespace) -> None:
    """Runs full component ablation study across seeds."""
    runner = BenchmarkRunner(seeds=args.seeds, events_per_workload=args.events)
    runner.run_ablation()


def cmd_real_os(args: argparse.Namespace) -> None:
    """Scans and monitors live host processes and memory."""
    adapter = RealOSTelemetryAdapter()
    mem = adapter.get_host_memory()
    print("\n=======================================================")
    print("  CALM Live Host OS Memory Telemetry")
    print("=======================================================")
    print(f"Total Physical RAM : {mem.total_mb:,.1f} MB")
    print(f"Used RAM           : {mem.used_mb:,.1f} MB ({mem.percent_used:.1f}%)")
    print(f"Available RAM      : {mem.available_mb:,.1f} MB")
    print(f"Pressure Level     : [{mem.pressure_level}]\n")

    procs = adapter.scan_target_processes()
    print(f"Top {min(args.limit, len(procs))} Memory-Consuming Processes:")
    print(f"{'PID':<8} {'Process Name':<24} {'RSS (MB)':<12} {'VMS (MB)':<12} {'CPU %':<8}")
    print("-" * 68)
    for p in procs[:args.limit]:
        print(f"{p.pid:<8} {p.name:<24} {p.rss_mb:<12.1f} {p.vms_mb:<12.1f} {p.cpu_percent:<8.1f}")
    print("")


def cmd_llm(args: argparse.Namespace) -> None:
    """Demonstrates real prompt token reduction and TTFT speedup."""
    mgr = LLMContextManager(active_window_turns=args.window, token_budget=args.budget)
    mgr.add_message("system", "You are an autonomous AI systems architect managing memory lifecycles.", importance=1.0)
    mgr.add_message("user", "Analyze the Android Low Memory Killer (LMK) trace logs.", importance=0.8)
    mgr.add_message("assistant", "Parsed 450 events. Detected rising pressure slope at tick 82.", importance=0.7)
    mgr.add_message("tool", "TRACE DUMP: [PSI] some_avg10=24.5, full_avg10=8.2, swap_free=12MB, slab_reclaimable=180MB" * 25, item_type=ItemType.TOOL_RESULT, importance=0.3)
    mgr.add_message("user", "What is the recommended proactive policy?", importance=0.9)
    mgr.add_message("assistant", "Recommend proactive compression of low-priority background buffers to avoid synchronous direct reclaim stall.", importance=0.85)

    res = mgr.optimize_context()
    print("\n=======================================================")
    print("  CALM LLM Context Optimization Telemetry")
    print("=======================================================")
    print(f"Original Raw Tokens      : {res.original_tokens} tokens")
    print(f"Optimized Prompt Tokens  : {res.optimized_tokens} tokens")
    print(f"Token Reduction Savings  : {res.token_savings_pct:.1f}%")
    print(f"Estimated TTFT Latency   : {res.estimated_ttft_ms_baseline:.1f}ms -> {res.estimated_ttft_ms_optimized:.1f}ms")
    print(f"TTFT Prefill Speedup     : {res.ttft_speedup_factor:.2f}x faster")
    print(f"Estimated Cost Savings   : ${res.cost_savings_usd_per_1k_calls:.4f} per 1,000 queries\n")


def cmd_trim(args: argparse.Namespace) -> None:
    """Trims working set of a specific PID or all background apps."""
    adapter = RealOSTelemetryAdapter()
    if args.pid:
        res = adapter.trim_process_working_set(args.pid)
        print("\n=======================================================")
        print(f"  CALM Real OS Working Set Trim: PID {args.pid}")
        print("=======================================================")
        if res.get("success"):
            print(f"Process Name   : {res.get('name')}")
            print(f"Initial RSS    : {res.get('before_rss_mb')} MB")
            print(f"Post-Trim RSS  : {res.get('after_rss_mb')} MB")
            print(f"RAM Reclaimed  : {res.get('reclaimed_mb')} MB ({res.get('reclaimed_pct')}%)")
            print("Status         : Working set pages flushed to standby list successfully.\n")
        else:
            print(f"Failed: {res.get('reason') or res.get('error')}\n")
    else:
        res = adapter.trim_all_background_processes(min_rss_mb=args.min_rss)
        print("\n=======================================================")
        print("  CALM Bulk Background Working Set Trim")
        print("=======================================================")
        print(f"Processes Trimmed : {res['trimmed_process_count']}")
        print(f"Total Reclaimed   : {res['total_reclaimed_mb']} MB")
        for p in res["processes"]:
            print(f"  PID {p['pid']:<6} {p['name']:<20}: {p['before_rss_mb']} MB -> {p['after_rss_mb']} MB (Reclaimed {p['reclaimed_mb']} MB)")
        print("")


def cmd_daemon(args: argparse.Namespace) -> None:
    """Runs autonomous background memory pressure watchdog."""
    import time
    adapter = RealOSTelemetryAdapter()
    print("\n=======================================================")
    print(f"  CALM Real-Time Memory Pressure Daemon")
    print(f"  Watchdog Interval: {args.interval}s | Pressure Threshold: {args.threshold}%")
    print("=======================================================")
    print("Press Ctrl+C to terminate daemon.\n")

    iterations = 0
    total_lifetime_reclaimed = 0.0

    try:
        while True:
            mem = adapter.get_host_memory()
            pressure_flag = f"[{mem.pressure_level}]"
            print(f"[{time.strftime('%H:%M:%S')}] Host RAM: {mem.used_mb:,.0f}/{mem.total_mb:,.0f} MB ({mem.percent_used:.1f}%) {pressure_flag:<10}", end="")

            if mem.percent_used >= args.threshold:
                print(" ➔ Triggering proactive working set reclamation...", end="")
                res = adapter.trim_all_background_processes(min_rss_mb=50.0)
                reclaimed = res.get("total_reclaimed_mb", 0.0)
                total_lifetime_reclaimed += reclaimed
                print(f" [Freed {reclaimed:.1f} MB across {res.get('trimmed_process_count', 0)} procs]")
            else:
                print(" [Normal Headroom]")

            iterations += 1
            if args.iterations and iterations >= args.iterations:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n[DAEMON] Terminated. Lifetime physical RAM reclaimed: {total_lifetime_reclaimed:.1f} MB.")


def cmd_serve(args: argparse.Namespace) -> None:
    """Launches the REST API server and React console."""
    import server
    port = args.port
    print(f"🚀 Starting CALM V2 Console on http://localhost:{port}")
    server.app.run(host="0.0.0.0", port=port, debug=False)


def main() -> None:
    parser = argparse.ArgumentParser(prog="calm", description="CALM V2: Context-Aware Lifecycle Memory CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Run a single comparative simulation")
    p_sim.add_argument("--workload", default="predictable", choices=[w.value for w in WorkloadType])
    p_sim.add_argument("--budget", type=int, default=2500, help="RAM budget in MB")
    p_sim.add_argument("--events", type=int, default=350, help="Number of ticks")
    p_sim.add_argument("--seed", type=int, default=42, help="Random seed")
    p_sim.add_argument("--aggression", default="Less Aggressive")
    p_sim.add_argument("--mode", default="mobile", choices=["mobile", "agent"])
    p_sim.set_defaults(func=cmd_simulate)

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run multi-seed benchmark across all 7 baselines")
    p_bench.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    p_bench.add_argument("--workloads", nargs="+", default=["all"])
    p_bench.add_argument("--events", type=int, default=350)
    p_bench.set_defaults(func=cmd_benchmark)

    # ablation
    p_abl = subparsers.add_parser("ablation", help="Run component ablation study")
    p_abl.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    p_abl.add_argument("--events", type=int, default=350)
    p_abl.set_defaults(func=cmd_ablation)

    # real-os
    p_os = subparsers.add_parser("real-os", help="Monitor live host memory and running processes")
    p_os.add_argument("--limit", type=int, default=10, help="Number of top processes to display")
    p_os.set_defaults(func=cmd_real_os)

    # optimize-llm
    p_llm = subparsers.add_parser("optimize-llm", help="Test real prompt token reduction & TTFT speedup")
    p_llm.add_argument("--budget", type=int, default=1500)
    p_llm.add_argument("--window", type=int, default=2)
    p_llm.set_defaults(func=cmd_llm)

    # trim
    p_trim = subparsers.add_parser("trim", help="Execute real OS working set trimming on PID or all background apps")
    p_trim.add_argument("--pid", type=int, help="Target process PID (omit to trim all background apps)")
    p_trim.add_argument("--min-rss", type=float, default=50.0, help="Minimum RSS in MB to target for bulk trim")
    p_trim.set_defaults(func=cmd_trim)

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run autonomous background memory pressure watchdog")
    p_daemon.add_argument("--interval", type=float, default=2.0, help="Watchdog check interval in seconds")
    p_daemon.add_argument("--threshold", type=float, default=75.0, help="Host RAM pressure threshold %% to trigger trim")
    p_daemon.add_argument("--iterations", type=int, default=None, help="Stop after N iterations (default runs forever)")
    p_daemon.set_defaults(func=cmd_daemon)

    # serve
    p_srv = subparsers.add_parser("serve", help="Launch Flask REST API & React console")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
