import React from 'react';

export function MemoryManagement({ simData, config }) {
  if (!simData) return null;

  const trace = simData.traces?.CALM || [];
  const lruTrace = simData.traces?.LRU || [];
  const ramLimit = config.ram_limit_mb || 2500;
  const currRam = trace[trace.length - 1]?.total_ram || 0;
  const utilPct = ramLimit > 0 ? (currRam / ramLimit) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Budget Card & Pressure Gauge */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-4 bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Memory Allocation Status</div>
            <div className="text-3xl font-bold text-slate-900">{utilPct.toFixed(1)}%</div>
            <p className="text-xs text-slate-400 mt-1 mb-4">Current resident memory utilization</p>

            <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden mb-5">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  utilPct > 90 ? 'bg-rose-500' : utilPct > 75 ? 'bg-amber-500' : 'bg-blue-600'
                }`}
                style={{ width: `${Math.min(100, utilPct)}%` }}
              ></div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 border-t border-slate-100 pt-4 font-mono text-xs text-center">
            <div>
              <div className="text-slate-400 text-[10px] uppercase">Resident</div>
              <div className="font-bold text-slate-800 mt-0.5">{currRam.toLocaleString()} MB</div>
            </div>
            <div>
              <div className="text-slate-400 text-[10px] uppercase">Headroom</div>
              <div className="font-bold text-slate-800 mt-0.5">{Math.max(0, ramLimit - currRam).toLocaleString()} MB</div>
            </div>
            <div>
              <div className="text-slate-400 text-[10px] uppercase">Budget</div>
              <div className="font-bold text-blue-600 mt-0.5">{ramLimit.toLocaleString()} MB</div>
            </div>
          </div>
        </div>

        {/* Compression & Pressure Analysis */}
        <div className="md:col-span-8 bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Proactive Pressure Trend Detection</h3>
          <p className="text-xs text-slate-400 mb-4">
            CALM detects rising memory pressure slopes and proactively compresses non-essential cached memory before critical exhaustion.
          </p>

          <div className="grid grid-cols-3 gap-3 font-mono text-xs">
            <div className="p-3 rounded border border-slate-100 bg-slate-50">
              <div className="text-[10px] text-slate-400 uppercase font-sans">Pressure Levels</div>
              <div className="font-bold text-slate-800 mt-1">LOW &lt; 55%</div>
              <div className="font-bold text-slate-800">MODERATE 55-75%</div>
              <div className="font-bold text-rose-600">CRITICAL &gt; 95%</div>
            </div>
            <div className="p-3 rounded border border-slate-100 bg-slate-50">
              <div className="text-[10px] text-slate-400 uppercase font-sans">Compressed RAM Factor</div>
              <div className="text-xl font-bold text-amber-600 mt-1">{((config.storage?.compressed_ram_factor || 0.35) * 100).toFixed(0)}%</div>
              <div className="text-[11px] text-slate-400 font-sans mt-0.5">Footprint in COMPRESSED state</div>
            </div>
            <div className="p-3 rounded border border-slate-100 bg-slate-50">
              <div className="text-[10px] text-slate-400 uppercase font-sans">Total Memory Reclaimed</div>
              <div className="text-xl font-bold text-emerald-600 mt-1">
                {(simData.metrics?.CALM?.total_reclaimed_mb || 0).toLocaleString()} MB
              </div>
              <div className="text-[11px] text-slate-400 font-sans mt-0.5">Released via proactive demotion</div>
            </div>
          </div>
        </div>
      </div>

      {/* Memory Consumption Timeline Table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Memory Allocation Trace (Sample Ticks)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2 px-3 font-sans">Tick</th>
                <th className="py-2 px-3 font-sans">Requested</th>
                <th className="py-2 px-3">CALM RAM</th>
                <th className="py-2 px-3">LRU RAM</th>
                <th className="py-2 px-3 font-sans">Reclaimed</th>
                <th className="py-2 px-3 font-sans">Budget Limit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {trace.slice(0, 30).map((step, idx) => (
                <tr key={step.tick} className="hover:bg-slate-50">
                  <td className="py-1.5 px-3 font-medium text-slate-400">{step.tick}</td>
                  <td className="py-1.5 px-3 font-sans font-medium text-slate-900">{step.requested_item}</td>
                  <td className="py-1.5 px-3 text-blue-600 font-bold">{step.total_ram} MB</td>
                  <td className="py-1.5 px-3 text-slate-500">{lruTrace[idx]?.total_ram || 0} MB</td>
                  <td className="py-1.5 px-3 text-emerald-600">{step.reclaimed_mb > 0 ? `+${step.reclaimed_mb} MB` : '—'}</td>
                  <td className="py-1.5 px-3 text-slate-400">{ramLimit} MB</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
