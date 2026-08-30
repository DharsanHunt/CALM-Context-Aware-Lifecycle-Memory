"""
calm.benchmark.runner — Reproducible multi-seed, multi-workload benchmark execution orchestrator.
Executes 7 baselines + ablation studies across multiple random seeds with zero future data leakage.
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional
import numpy as np

from calm.utils.config import CALMConfig, DEFAULT_APPS
from calm.telemetry.workload import WorkloadGenerator, WorkloadType, WorkloadSequence, temporal_split
from calm.prediction.markov import MarkovPredictor
from calm.prediction.evaluation import PredictionEvaluator
from calm.benchmark.baselines import create_strategy, STRATEGY_NAMES, BaseStrategy
from calm.benchmark.metrics import BenchmarkMetricsCalculator, RunResultMetrics


class BenchmarkRunner:
    """
    Orchestrates end-to-end benchmark evaluation across workloads, baselines, and seeds.
    """

    def __init__(
        self,
        config: Optional[CALMConfig] = None,
        results_dir: str = "results",
    ):
        self.config = config or CALMConfig()
        self.results_dir = results_dir
        self.raw_dir = os.path.join(results_dir, "raw")
        self.processed_dir = os.path.join(results_dir, "processed")
        self.figures_dir = os.path.join(results_dir, "figures")

        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.figures_dir, exist_ok=True)

    def run_single_experiment(
        self,
        strategy_name: str,
        workload_seq: WorkloadSequence,
        seed: int,
        save_raw: bool = True,
        # Ablation overrides for CALM
        ablation_kwargs: Optional[Dict[str, bool]] = None,
    ) -> RunResultMetrics:
        """
        Executes a single (strategy, workload, seed) experiment under strict temporal split.
        Predictor is trained strictly on the train split (70%) and evaluated on test split (30%).
        """
        train_seq, val_seq, test_seq = temporal_split(workload_seq, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
        eval_events = val_seq.events + test_seq.events  # 30% unseen evaluation sequence
        all_items = workload_seq.items

        # 1. Train predictor on historical training sequence strictly
        predictor = MarkovPredictor(smoothing_alpha=self.config.prediction.smoothing_alpha)
        train_items = [e.item_id for e in train_seq.events]
        predictor.fit(train_items, all_items=all_items)

        # 2. Evaluate prediction metrics on unseen sequence
        eval_items = [e.item_id for e in eval_events]
        pred_metrics = PredictionEvaluator.evaluate(predictor, eval_items, top_k=self.config.prediction.top_k)

        # 3. Instantiate strategy
        strategy = create_strategy(strategy_name, self.config, all_items, seed=seed)

        # If ablation overrides are provided and strategy is CALM
        if strategy_name == "CALM" and ablation_kwargs and hasattr(strategy, "manager"):
            step_results = []
            for event in eval_events:
                req_item = event.item_id
                pred_res = predictor.predict(req_item, top_k=self.config.prediction.top_k)
                step_res = strategy.manager.step(
                    requested_item=req_item,
                    prediction_result=pred_res,
                    **ablation_kwargs,
                )
                step_results.append(step_res)
        else:
            step_results = []
            for event in eval_events:
                req_item = event.item_id
                pred_res = predictor.predict(req_item, top_k=self.config.prediction.top_k)
                step_res = strategy.step(requested_item=req_item, prediction_result=pred_res)
                step_results.append(step_res)

        # 4. Calculate comprehensive metrics
        metrics = BenchmarkMetricsCalculator.calculate(
            strategy_name=strategy_name,
            workload_name=workload_seq.workload_type.value,
            seed=seed,
            step_results=step_results,
            ram_limit_mb=self.config.ram_limit_mb,
            prediction_metrics=pred_metrics,
        )

        # 5. Save raw trace if requested
        if save_raw:
            workload_raw_dir = os.path.join(self.raw_dir, workload_seq.workload_type.value, str(seed))
            os.makedirs(workload_raw_dir, exist_ok=True)
            raw_path = os.path.join(workload_raw_dir, f"{strategy_name}.json")
            with open(raw_path, "w") as f:
                json.dump({
                    "metrics": metrics.to_dict(),
                    "trace_length": len(step_results),
                    "pred_metrics": pred_metrics,
                }, f, indent=2)

        return metrics

    def run_benchmark_suite(
        self,
        workload_types: Optional[List[WorkloadType]] = None,
        strategies: Optional[List[str]] = None,
        seeds: Optional[List[int]] = None,
        num_events: int = 400,
    ) -> Dict[str, Any]:
        """
        Executes full matrix: workloads x strategies x seeds.
        Returns aggregated summary statistics (mean, std, min, max).
        """
        w_types = workload_types or list(WorkloadType)
        strats = strategies or STRATEGY_NAMES
        seed_list = seeds or [42, 43, 44, 45, 46]

        all_results: List[RunResultMetrics] = []

        for w_type in w_types:
            for seed in seed_list:
                workload_seq = WorkloadGenerator.generate(
                    workload_type=w_type,
                    num_events=num_events,
                    seed=seed,
                    apps=DEFAULT_APPS,
                    app_ram=self.config.app_ram,
                )
                for strat in strats:
                    res = self.run_single_experiment(
                        strategy_name=strat,
                        workload_seq=workload_seq,
                        seed=seed,
                        save_raw=True,
                    )
                    all_results.append(res)

        # Aggregate statistics
        summary = self._aggregate_results(all_results)
        summary_path = os.path.join(self.processed_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def run_ablation_study(
        self,
        workload_type: WorkloadType = WorkloadType.PREDICTABLE,
        seeds: Optional[List[int]] = None,
        num_events: int = 400,
    ) -> Dict[str, Any]:
        """
        Executes ablation study across the 7 component variants.
        """
        seed_list = seeds or [42, 43, 44, 45, 46]

        ablation_variants = {
            "CALM Full": {
                "enable_prediction": True,
                "enable_burst": True,
                "enable_hysteresis": True,
                "enable_pressure_trend": True,
                "enable_compression": True,
                "enable_context": True,
            },
            "w/o Prediction": {
                "enable_prediction": False,
                "enable_burst": True,
                "enable_hysteresis": True,
                "enable_pressure_trend": True,
                "enable_compression": True,
                "enable_context": True,
            },
            "w/o Burst Protection": {
                "enable_prediction": True,
                "enable_burst": False,
                "enable_hysteresis": True,
                "enable_pressure_trend": True,
                "enable_compression": True,
                "enable_context": True,
            },
            "w/o Hysteresis": {
                "enable_prediction": True,
                "enable_burst": True,
                "enable_hysteresis": False,
                "enable_pressure_trend": True,
                "enable_compression": True,
                "enable_context": True,
            },
            "w/o Pressure Trend": {
                "enable_prediction": True,
                "enable_burst": True,
                "enable_hysteresis": True,
                "enable_pressure_trend": False,
                "enable_compression": True,
                "enable_context": True,
            },
            "w/o Compression": {
                "enable_prediction": True,
                "enable_burst": True,
                "enable_hysteresis": True,
                "enable_pressure_trend": True,
                "enable_compression": False,
                "enable_context": True,
            },
            "w/o Context Importance": {
                "enable_prediction": True,
                "enable_burst": True,
                "enable_hysteresis": True,
                "enable_pressure_trend": True,
                "enable_compression": True,
                "enable_context": False,
            },
        }

        ablation_results: Dict[str, List[RunResultMetrics]] = {v: [] for v in ablation_variants}

        for seed in seed_list:
            workload_seq = WorkloadGenerator.generate(
                workload_type=workload_type,
                num_events=num_events,
                seed=seed,
            )
            for variant_name, kwargs in ablation_variants.items():
                metrics = self.run_single_experiment(
                    strategy_name="CALM",
                    workload_seq=workload_seq,
                    seed=seed,
                    save_raw=False,
                    ablation_kwargs=kwargs,
                )
                metrics.strategy_name = variant_name
                ablation_results[variant_name].append(metrics)

        # Aggregate ablation statistics
        ablation_summary: Dict[str, Any] = {}
        for variant, metric_list in ablation_results.items():
            hit_rates = [m.cache_hit_rate_pct for m in metric_list]
            latencies = [m.avg_launch_latency_sec for m in metric_list]
            thrashes = [m.thrashing_count for m in metric_list]
            mem_times = [m.memory_time_mb_ticks for m in metric_list]

            ablation_summary[variant] = {
                "hit_rate_mean": round(float(np.mean(hit_rates)), 2),
                "hit_rate_std": round(float(np.std(hit_rates)), 2),
                "latency_mean": round(float(np.mean(latencies)), 4),
                "latency_std": round(float(np.std(latencies)), 4),
                "thrashing_mean": round(float(np.mean(thrashes)), 1),
                "memory_time_mean": round(float(np.mean(mem_times)), 1),
            }

        ablation_path = os.path.join(self.processed_dir, "ablation_summary.json")
        with open(ablation_path, "w") as f:
            json.dump(ablation_summary, f, indent=2)

        return ablation_summary

    def _aggregate_results(self, results: List[RunResultMetrics]) -> Dict[str, Any]:
        """Groups and calculates mean, std, min, max across multiple seeds."""
        grouped: Dict[str, Dict[str, List[RunResultMetrics]]] = {}
        for r in results:
            grouped.setdefault(r.workload_name, {}).setdefault(r.strategy_name, []).append(r)

        summary: Dict[str, Any] = {}
        for w_name, strat_dict in grouped.items():
            summary[w_name] = {}
            for s_name, run_list in strat_dict.items():
                hit_rates = [r.cache_hit_rate_pct for r in run_list]
                latencies = [r.avg_launch_latency_sec for r in run_list]
                thrashes = [r.thrashing_count for r in run_list]
                rams = [r.avg_ram_mb for r in run_list]
                peaks = [r.peak_ram_mb for r in run_list]
                mem_times = [r.memory_time_mb_ticks for r in run_list]

                summary[w_name][s_name] = {
                    "cache_hit_rate": {
                        "mean": round(float(np.mean(hit_rates)), 2),
                        "std": round(float(np.std(hit_rates)), 2),
                        "min": round(float(np.min(hit_rates)), 2),
                        "max": round(float(np.max(hit_rates)), 2),
                    },
                    "avg_launch_latency": {
                        "mean": round(float(np.mean(latencies)), 4),
                        "std": round(float(np.std(latencies)), 4),
                        "min": round(float(np.min(latencies)), 4),
                        "max": round(float(np.max(latencies)), 4),
                    },
                    "thrashing_count": {
                        "mean": round(float(np.mean(thrashes)), 2),
                        "std": round(float(np.std(thrashes)), 2),
                    },
                    "avg_ram_mb": {
                        "mean": round(float(np.mean(rams)), 1),
                        "std": round(float(np.std(rams)), 1),
                    },
                    "peak_ram_mb": {
                        "mean": round(float(np.mean(peaks)), 1),
                        "max": round(float(np.max(peaks)), 1),
                    },
                    "memory_time_mb_ticks": {
                        "mean": round(float(np.mean(mem_times)), 1),
                    },
                }

        return summary


def main():
    parser = argparse.ArgumentParser(description="CALM V2 Benchmark Runner")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46], help="Random seeds")
    parser.add_argument("--workloads", nargs="+", type=str, default=["all"], help="Workload names or 'all'")
    parser.add_argument("--ablation", action="store_true", help="Run ablation study")
    args = parser.parse_args()

    runner = BenchmarkRunner()

    if args.ablation:
        print("Running CALM V2 Ablation Study...")
        abl_res = runner.run_ablation_study(seeds=args.seeds)
        print(json.dumps(abl_res, indent=2))
        return

    w_types = list(WorkloadType) if "all" in args.workloads else [WorkloadType(w) for w in args.workloads]
    print(f"Running CALM V2 Benchmark Suite across {len(w_types)} workloads and {len(args.seeds)} seeds...")
    summary = runner.run_benchmark_suite(workload_types=w_types, seeds=args.seeds)
    print("\nBenchmark Suite Completed successfully. Summary written to results/processed/summary.json.")


if __name__ == "__main__":
    main()
