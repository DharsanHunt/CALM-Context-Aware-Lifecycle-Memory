import React from 'react';

export function BenchmarkSuite({ simData }) {
  if (!simData || !simData.metrics) return null;

  const strategies = Object.keys(simData.metrics);

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-1">7-Baseline Comparative Benchmark</h3>
        <p className="text-xs text-slate-400 mb-4">
          Strictly evaluated on unseen test sequence under identical memory limits and identical initial states.
        </p>

        {/* Visual Comparison Bars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Hit Rate Comparison */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">Cache Hit Rate (%)</h4>
            <div className="space-y-3">
              {strategies.map((s) => {
                const hit = simData.metrics[s].cache_hit_rate_pct;
                const isCalm = s === 'CALM';
                return (
                  <div key={s}>
                    <div className="flex justify-between text-xs font-medium mb-1">
                      <span className={isCalm ? 'font-bold text-blue-700' : 'text-slate-600'}>{s}</span>
                      <span className="font-mono font-semibold">{hit.toFixed(1)}%</span>
                    </div>
                    <div className="h-3 w-full bg-slate-100 rounded overflow-hidden">
                      <div
                        className={`h-full rounded ${isCalm ? 'bg-blue-600' : 'bg-slate-400'}`}
                        style={{ width: `${hit}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Launch Latency Comparison */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">Launch Latency (seconds)</h4>
            <div className="space-y-3">
              {strategies.map((s) => {
                const lat = simData.metrics[s].avg_launch_latency_sec;
                const isCalm = s === 'CALM';
                const latPct = Math.min(100, (lat / 2.5) * 100);
                return (
                  <div key={s}>
                    <div className="flex justify-between text-xs font-medium mb-1">
                      <span className={isCalm ? 'font-bold text-emerald-700' : 'text-slate-600'}>{s}</span>
                      <span className="font-mono font-semibold">{lat.toFixed(3)}s</span>
                    </div>
                    <div className="h-3 w-full bg-slate-100 rounded overflow-hidden">
                      <div
                        className={`h-full rounded ${isCalm ? 'bg-emerald-500' : 'bg-amber-400'}`}
                        style={{ width: `${latPct}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Summary Table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Detailed Metrics Summary</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2 px-3 font-sans">Strategy</th>
                <th className="py-2 px-3">Hit Rate</th>
                <th className="py-2 px-3">Avg Latency</th>
                <th className="py-2 px-3">P95 Latency</th>
                <th className="py-2 px-3">Avg RAM</th>
                <th className="py-2 px-3">Peak RAM</th>
                <th className="py-2 px-3">Thrashing</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {strategies.map((s) => {
                const m = simData.metrics[s];
                const isCalm = s === 'CALM';
                return (
                  <tr key={s} className={isCalm ? 'bg-blue-50/40 font-semibold' : 'hover:bg-slate-50'}>
                    <td className="py-2 px-3 font-sans font-medium text-slate-900">{s}</td>
                    <td className="py-2 px-3 text-blue-600">{m.cache_hit_rate_pct.toFixed(1)}%</td>
                    <td className="py-2 px-3 text-emerald-600">{m.avg_launch_latency_sec.toFixed(4)}s</td>
                    <td className="py-2 px-3">{m.p95_launch_latency_sec.toFixed(4)}s</td>
                    <td className="py-2 px-3">{m.avg_ram_mb.toLocaleString()} MB</td>
                    <td className="py-2 px-3">{m.peak_ram_mb.toLocaleString()} MB</td>
                    <td className="py-2 px-3 text-rose-600">{m.thrashing_count}</td>
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
