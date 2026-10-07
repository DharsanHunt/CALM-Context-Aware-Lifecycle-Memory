"""
calm.benchmark.plotter — High-Resolution Publication Plot Generator.
Generates publication-quality charts (PNG & PDF) for research whitepapers, READMEs, and portfolios.
"""

import os
import json
from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


class BenchmarkPlotter:
    """Generates high-resolution figures for baseline comparisons, ablations, and memory trajectories."""

    @staticmethod
    def generate_all_figures(output_dir: str = "results/figures") -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []

        summary_file = os.path.join("results", "processed", "summary.json")
        ablation_file = os.path.join("results", "processed", "ablation_summary.json")

        if os.path.exists(summary_file):
            with open(summary_file, "r") as f:
                summary_data = json.load(f)
            p1 = BenchmarkPlotter.plot_baseline_comparison(summary_data, output_dir)
            generated_files.append(p1)

        if os.path.exists(ablation_file):
            with open(ablation_file, "r") as f:
                ablation_data = json.load(f)
            p2 = BenchmarkPlotter.plot_ablation_study(ablation_data, output_dir)
            generated_files.append(p2)

        return generated_files

    @staticmethod
    def plot_baseline_comparison(summary_data: Dict[str, Any], output_dir: str) -> str:
        """Generates 2-panel figure: Hit Rate & Latency across 7 baselines (Predictable workload)."""
        pred_data = summary_data.get("predictable", {})
        if not pred_data:
            first_w = list(summary_data.keys())[0]
            pred_data = summary_data[first_w]

        strategies = list(pred_data.keys())
        hit_means = [pred_data[s]["cache_hit_rate"]["mean"] for s in strategies]
        hit_stds = [pred_data[s]["cache_hit_rate"]["std"] for s in strategies]
        lat_means = [pred_data[s]["avg_launch_latency"]["mean"] for s in strategies]
        lat_stds = [pred_data[s]["avg_launch_latency"]["std"] for s in strategies]

        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)

        # Panel 1: Hit Rate
        colors_hit = ["#2563EB" if s == "CALM" else "#94A3B8" for s in strategies]
        bars1 = ax1.bar(strategies, hit_means, yerr=hit_stds, color=colors_hit, capsize=4, edgecolor="#1E293B", linewidth=0.8)
        ax1.set_ylabel("Cache Hit Rate (%)", fontsize=11, fontweight="bold")
        ax1.set_title("(A) Cache Hit Rate across 7 Baselines", fontsize=12, fontweight="bold", pad=10)
        ax1.set_ylim(0, 100)
        ax1.set_xticks(range(len(strategies)))
        ax1.set_xticklabels(strategies, rotation=35, ha="right", fontsize=9)
        for b, v in zip(bars1, hit_means):
            ax1.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:.1f}%", ha="center", fontsize=8, fontweight="bold")

        # Panel 2: Latency
        colors_lat = ["#16A34A" if s == "CALM" else "#F59E0B" for s in strategies]
        bars2 = ax2.bar(strategies, lat_means, yerr=lat_stds, color=colors_lat, capsize=4, edgecolor="#1E293B", linewidth=0.8)
        ax2.set_ylabel("Average Launch Latency (s)", fontsize=11, fontweight="bold")
        ax2.set_title("(B) Launch Latency across 7 Baselines", fontsize=12, fontweight="bold", pad=10)
        ax2.set_xticks(range(len(strategies)))
        ax2.set_xticklabels(strategies, rotation=35, ha="right", fontsize=9)
        for b, v in zip(bars2, lat_means):
            ax2.text(b.get_x() + b.get_width() / 2, v + 0.04, f"{v:.3f}s", ha="center", fontsize=8, fontweight="bold")

        plt.tight_layout()
        out_path = os.path.join(output_dir, "baseline_comparison.png")
        plt.savefig(out_path, dpi=300)
        plt.close()
        return out_path

    @staticmethod
    def plot_ablation_study(ablation_data: Dict[str, Any], output_dir: str) -> str:
        """Generates horizontal bar chart for component ablation analysis."""
        variants = list(ablation_data.keys())
        hr_means = [ablation_data[v]["hit_rate_mean"] for v in variants]
        hr_stds = [ablation_data[v]["hit_rate_std"] for v in variants]

        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
        colors = ["#2563EB" if v == "CALM Full" else "#64748B" for v in variants]
        bars = ax.barh(variants, hr_means, xerr=hr_stds, color=colors, capsize=4, edgecolor="#1E293B", linewidth=0.8)
        ax.set_xlabel("Cache Hit Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title("Component Ablation Study: Impact of Subsystems (Mean ± Std, 5 Seeds)", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlim(0, 100)

        for b, v in zip(bars, hr_means):
            ax.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.2f}%", va="center", fontsize=9, fontweight="bold")

        plt.tight_layout()
        out_path = os.path.join(output_dir, "ablation_study.png")
        plt.savefig(out_path, dpi=300)
        plt.close()
        return out_path
