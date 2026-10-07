"""
calm.benchmark.report — Formatter for benchmark results, statistical comparisons, and markdown tables.
"""

from typing import Dict, Any, List
import pandas as pd


class BenchmarkReporter:
    """Formats benchmark summaries and generates markdown and terminal reports."""

    @staticmethod
    def format_summary_table(summary_dict: Dict[str, Any], metric: str = "cache_hit_rate") -> pd.DataFrame:
        """
        Creates a DataFrame comparing strategies across workloads for a given metric.
        """
        workloads = list(summary_dict.keys())
        if not workloads:
            return pd.DataFrame()

        strategies = list(summary_dict[workloads[0]].keys())
        rows = []

        for w in workloads:
            row = {"Workload": w.replace("_", " ").title()}
            for s in strategies:
                val_data = summary_dict[w].get(s, {}).get(metric, {})
                mean_val = val_data.get("mean", 0.0)
                std_val = val_data.get("std", 0.0)
                row[s] = f"{mean_val:.2f} ± {std_val:.2f}"
            rows.append(row)

        return pd.DataFrame(rows)

    @staticmethod
    def format_ablation_table(ablation_dict: Dict[str, Any]) -> pd.DataFrame:
        """Formats ablation results as a clean comparison DataFrame."""
        rows = []
        for variant, stats in ablation_dict.items():
            rows.append({
                "Ablation Variant": variant,
                "Hit Rate (%)": f"{stats['hit_rate_mean']:.2f}% ± {stats['hit_rate_std']:.2f}",
                "Avg Latency (s)": f"{stats['latency_mean']:.4f}s ± {stats['latency_std']:.4f}",
                "Thrashing Events": f"{stats['thrashing_mean']:.1f}",
                "Memory-Time (MB·ticks)": f"{stats['memory_time_mean']:,.0f}",
            })
        return pd.DataFrame(rows)

    @staticmethod
    def format_comparison_table(metrics_list: List[Any]) -> str:
        """Formats a list of RunResultMetrics into a clean ASCII table."""
        header = f"{'Strategy':<18} {'Hit Rate (%)':<14} {'Avg Latency (s)':<16} {'P95 Lat (s)':<14} {'Avg RAM (MB)':<14} {'Thrashing':<10}"
        sep = "-" * len(header)
        lines = [header, sep]
        for m in metrics_list:
            lines.append(
                f"{m.strategy_name:<18} "
                f"{m.cache_hit_rate_pct:<14.1f} "
                f"{m.avg_launch_latency_sec:<16.4f} "
                f"{m.p95_launch_latency_sec:<14.4f} "
                f"{m.avg_ram_mb:<14.0f} "
                f"{m.thrashing_count:<10}"
            )
        return "\n".join(lines)

