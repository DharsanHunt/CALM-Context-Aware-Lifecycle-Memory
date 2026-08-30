import React from 'react';

export function Header({
  activeTabTitle,
  workload,
  setWorkload,
  ramLimit,
  setRamLimit,
  aggression,
  setAggression,
  mode,
  setMode,
}) {
  return (
    <header className="h-16 fixed top-0 right-0 left-56 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-40">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-slate-800">{activeTabTitle}</h2>
      </div>

      {/* Control Bar Controls */}
      <div className="flex items-center gap-3 text-xs">
        {/* Mode Toggle */}
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="mobile">📱 Mobile App Mode</option>
          <option value="agent">🤖 AI Agent Mode</option>
        </select>

        {/* Workload Selector */}
        <select
          value={workload}
          onChange={(e) => setWorkload(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="predictable">Workload: Predictable</option>
          <option value="random">Workload: Random</option>
          <option value="bursty">Workload: Bursty</option>
          <option value="productivity">Workload: Productivity</option>
          <option value="social_media">Workload: Social Media</option>
          <option value="context_switching">Workload: Context Switching</option>
          <option value="adversarial">Workload: Adversarial</option>
        </select>

        {/* Aggression Preset */}
        <select
          value={aggression}
          onChange={(e) => setAggression(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="No Aggression">No Aggression (6000 MB)</option>
          <option value="Less Aggressive">Less Aggressive (3500 MB)</option>
          <option value="Aggressive">Aggressive (2000 MB)</option>
          <option value="Critical">Critical (1200 MB)</option>
        </select>

        {/* RAM Limit Badge */}
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-3 py-1.5 rounded font-mono font-semibold">
          Budget: {ramLimit.toLocaleString()} MB
        </div>
      </div>
    </header>
  );
}
