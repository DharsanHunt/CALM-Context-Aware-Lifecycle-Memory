import React from 'react';
import { StateChip } from '../components/StateChip';

export function LifecycleMonitor({ simData }) {
  if (!simData) return null;

  const calmMetrics = simData.metrics?.CALM || {};
  const lruMetrics = simData.metrics?.LRU || {};
  const trace = simData.traces?.CALM || [];
  const stateDist = calmMetrics.state_distribution || {};
  const lruDist = lruMetrics.state_distribution || {};

  return (
    <div className="space-y-6">
      {/* Visual Flow Diagram */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-4">4-Tier Predictive Lifecycle Flow</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-center">
            <div className="text-sm font-bold text-emerald-800">ACTIVE</div>
            <div className="text-xs text-emerald-600 mt-1">Foreground Execution</div>
            <div className="text-[11px] font-mono text-emerald-500 mt-2">Latency: 0.05s</div>
          </div>
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 text-center">
            <div className="text-sm font-bold text-blue-800">CACHED</div>
            <div className="text-xs text-blue-600 mt-1">Uncompressed Resident</div>
            <div className="text-[11px] font-mono text-blue-500 mt-2">Latency: 0.40s</div>
          </div>
          <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-center">
            <div className="text-sm font-bold text-amber-800">COMPRESSED</div>
            <div className="text-xs text-amber-600 mt-1">In-RAM zRAM (~35%)</div>
            <div className="text-[11px] font-mono text-amber-500 mt-2">Latency: 1.10s</div>
          </div>
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-center">
            <div className="text-sm font-bold text-rose-800">ARCHIVED</div>
            <div className="text-xs text-rose-600 mt-1">Cold Backing Store (0 MB)</div>
            <div className="text-[11px] font-mono text-rose-500 mt-2">Latency: 2.40s</div>
          </div>
        </div>
      </div>

      {/* State Distribution Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">CALM V2 State Residency Distribution</h3>
          <div className="space-y-3">
            {['ACTIVE', 'CACHED', 'COMPRESSED', 'ARCHIVED'].map((st) => {
              const pct = stateDist[st] || 0;
              const barColor =
                st === 'ACTIVE'
                  ? 'bg-emerald-500'
                  : st === 'CACHED'
                  ? 'bg-blue-500'
                  : st === 'COMPRESSED'
                  ? 'bg-amber-500'
                  : 'bg-rose-500';
              return (
                <div key={st}>
                  <div className="flex justify-between text-xs font-medium mb-1">
                    <span className="text-slate-700">{st}</span>
                    <span className="font-mono text-slate-500">{pct.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">LRU Baseline Residency Distribution</h3>
          <div className="space-y-3">
            {['ACTIVE', 'CACHED', 'COMPRESSED', 'ARCHIVED'].map((st) => {
              const pct = lruDist[st] || 0;
              return (
                <div key={st}>
                  <div className="flex justify-between text-xs font-medium mb-1">
                    <span className="text-slate-700">{st}</span>
                    <span className="font-mono text-slate-500">{pct.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-400" style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Item State Progression Matrix */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-800">Event-by-Event State Progression (First 40 Ticks)</h3>
          <span className="text-xs text-slate-400 font-mono">Real-time trace</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2 px-3 font-mono">Tick</th>
                <th className="py-2 px-3">Access Request</th>
                <th className="py-2 px-3">Pre-Launch Hit</th>
                <th className="py-2 px-3">Chrome</th>
                <th className="py-2 px-3">YouTube</th>
                <th className="py-2 px-3">Spotify</th>
                <th className="py-2 px-3">Gemini</th>
                <th className="py-2 px-3">WhatsApp</th>
                <th className="py-2 px-3 font-mono">RAM (MB)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {trace.slice(0, 40).map((step) => (
                <tr key={step.tick} className="hover:bg-slate-50">
                  <td className="py-2 px-3 font-mono font-medium text-slate-400">{step.tick}</td>
                  <td className="py-2 px-3 font-semibold text-slate-900">{step.requested_item}</td>
                  <td className="py-2 px-3">
                    {step.is_cache_hit ? (
                      <span className="text-emerald-600 font-semibold">✓ HIT</span>
                    ) : (
                      <span className="text-rose-500 font-medium">✗ MISS</span>
                    )}
                  </td>
                  {['Chrome', 'YouTube', 'Spotify', 'Gemini', 'WhatsApp'].map((app) => (
                    <td key={app} className="py-2 px-3">
                      <StateChip state={step.post_states?.[app] || 'ARCHIVED'} />
                    </td>
                  ))}
                  <td className="py-2 px-3 font-mono text-slate-600">{step.total_ram}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
