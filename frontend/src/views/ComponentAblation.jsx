import React, { useEffect, useState } from 'react';
import { fetchAblationSummary } from '../api';

export function ComponentAblation() {
  const [ablationData, setAblationData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAblationSummary()
      .then((data) => {
        setAblationData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading ablation study statistics...</div>;
  }

  if (!ablationData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 text-center text-slate-600">
        Run <code className="bg-slate-100 px-2 py-1 rounded text-xs">python -m calm.benchmark.runner --ablation</code> to generate statistical ablation summaries.
      </div>
    );
  }

  const variants = Object.keys(ablationData);

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-1">Component Ablation Analysis</h3>
        <p className="text-xs text-slate-400 mb-4">
          Empirical evaluation demonstrating the isolated performance contribution of each CALM mechanism across 5 random seeds.
        </p>

        {/* Visual Ablation Bars */}
        <div className="space-y-3.5 mb-6">
          {variants.map((v) => {
            const stats = ablationData[v];
            const isFull = v === 'CALM Full';
            return (
              <div key={v}>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className={isFull ? 'font-bold text-blue-700' : 'text-slate-700'}>{v}</span>
                  <span className="font-mono text-slate-600 font-semibold">
                    {stats.hit_rate_mean.toFixed(2)}% ± {stats.hit_rate_std.toFixed(2)}
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-100 rounded overflow-hidden">
                  <div
                    className={`h-full rounded ${isFull ? 'bg-blue-600' : 'bg-slate-400'}`}
                    style={{ width: `${stats.hit_rate_mean}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Ablation Data Table */}
        <div className="overflow-x-auto border-t border-slate-100 pt-4">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-sans">Ablation Variant</th>
                <th className="py-2.5 px-3">Hit Rate (%)</th>
                <th className="py-2.5 px-3">Avg Latency</th>
                <th className="py-2.5 px-3">Thrashing</th>
                <th className="py-2.5 px-3">Memory-Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {variants.map((v) => {
                const s = ablationData[v];
                const isFull = v === 'CALM Full';
                return (
                  <tr key={v} className={isFull ? 'bg-blue-50/40 font-semibold' : 'hover:bg-slate-50'}>
                    <td className="py-2 px-3 font-sans font-medium text-slate-900">{v}</td>
                    <td className="py-2 px-3 text-blue-600">{s.hit_rate_mean.toFixed(2)}% ± {s.hit_rate_std.toFixed(2)}</td>
                    <td className="py-2 px-3 text-emerald-600">{s.latency_mean.toFixed(4)}s</td>
                    <td className="py-2 px-3 text-rose-600">{s.thrashing_mean.toFixed(1)}</td>
                    <td className="py-2 px-3">{s.memory_time_mean.toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
