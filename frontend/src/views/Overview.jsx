import React from 'react';
import { BentoCard } from '../components/BentoCard';
import { StateChip } from '../components/StateChip';

export function Overview({ simData }) {
  if (!simData || !simData.metrics) {
    return <div className="p-8 text-center text-slate-500">Loading simulation telemetry...</div>;
  }

  const calm = simData.metrics.CALM;
  const lru = simData.metrics.LRU;
  const trace = simData.traces?.CALM || [];
  const finalStep = trace[trace.length - 1] || {};

  const hitDelta = calm.cache_hit_rate_pct - lru.cache_hit_rate_pct;
  const latImp =
    lru.avg_launch_latency_sec > 0
      ? ((lru.avg_launch_latency_sec - calm.avg_launch_latency_sec) / lru.avg_launch_latency_sec) * 100
      : 0;
  const thrashDelta = lru.thrashing_count - calm.thrashing_count;

  return (
    <div className="space-y-6">
      {/* KPI Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <BentoCard
          title="Cache Hit Rate"
          value={`${calm.cache_hit_rate_pct.toFixed(1)}%`}
          delta={`+${hitDelta.toFixed(1)}% vs LRU`}
          deltaType={hitDelta >= 0 ? 'positive' : 'negative'}
        />
        <BentoCard
          title="Avg Launch Latency"
          value={`${calm.avg_launch_latency_sec.toFixed(3)}s`}
          delta={`-${latImp.toFixed(1)}% vs LRU`}
          deltaType="positive"
        />
        <BentoCard
          title="Thrashing Events"
          value={calm.thrashing_count}
          delta={`-${thrashDelta} fewer evictions vs LRU`}
          deltaType="positive"
        />
        <BentoCard
          title="Top-3 Prediction Acc"
          value={`${simData.pred_metrics?.top_3_accuracy.toFixed(1)}%`}
          delta={`Certainty: ${(simData.pred_metrics?.mean_confidence * 100).toFixed(1)}%`}
          deltaType="neutral"
        />
      </div>

      {/* Main Grid: Strategy Comparison Table & Final Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Strategy Table (8 cols) */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-800">Strategy Performance Matrix (Unseen Evaluation Stream)</h3>
            <span className="text-xs text-slate-400 font-mono">N = {simData.eval_len} Events</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Strategy</th>
                  <th className="py-2.5 px-3">Hit Rate</th>
                  <th className="py-2.5 px-3">Avg Latency</th>
                  <th className="py-2.5 px-3">P95 Latency</th>
                  <th className="py-2.5 px-3">Avg RAM</th>
                  <th className="py-2.5 px-3">Memory-Time</th>
                  <th className="py-2.5 px-3">Thrashing</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {Object.keys(simData.metrics).map((strategyName) => {
                  const m = simData.metrics[strategyName];
                  const isCalm = strategyName === 'CALM';
                  return (
                    <tr key={strategyName} className={isCalm ? 'bg-blue-50/50 font-semibold text-blue-900' : 'hover:bg-slate-50'}>
                      <td className="py-2 px-3 font-sans font-medium text-slate-900">
                        {strategyName} {isCalm && <span className="ml-1 text-[10px] bg-blue-600 text-white px-1.5 py-0.5 rounded">V2</span>}
                      </td>
                      <td className="py-2 px-3">{m.cache_hit_rate_pct.toFixed(1)}%</td>
                      <td className="py-2 px-3">{m.avg_launch_latency_sec.toFixed(4)}s</td>
                      <td className="py-2 px-3">{m.p95_launch_latency_sec.toFixed(4)}s</td>
                      <td className="py-2 px-3">{m.avg_ram_mb.toLocaleString()} MB</td>
                      <td className="py-2 px-3">{m.memory_time_mb_ticks.toLocaleString()}</td>
                      <td className="py-2 px-3">{m.thrashing_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Memory State Snapshot (4 cols) */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="pb-3 mb-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-800">Final Engine State Snapshot</h3>
            <p className="text-xs text-slate-400 mt-0.5">Live state across all tracked memory items</p>
          </div>

          <div className="space-y-3">
            {finalStep.post_states &&
              Object.entries(finalStep.post_states).map(([item, state]) => {
                const priority = finalStep.priority_scores?.[item] || 0;
                return (
                  <div key={item} className="flex items-center justify-between p-2.5 rounded border border-slate-100 bg-slate-50/60">
                    <div>
                      <div className="text-sm font-medium text-slate-900">{item}</div>
                      <div className="text-[11px] text-slate-400 font-mono">Priority: {priority.toFixed(3)}</div>
                    </div>
                    <StateChip state={state} />
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}
