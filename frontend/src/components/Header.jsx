import React from 'react';

const TABS = [
  { id: 'overview', label: 'Suite Overview', icon: 'auto_fix_high' },
  { id: 'real_os', label: 'Host OS Watchdog', icon: 'terminal' },
  { id: 'lifecycle', label: 'Lifecycle Monitor', icon: 'analytics' },
  { id: 'prediction', label: 'Prediction Engine', icon: 'query_stats' },
  { id: 'memory', label: 'Working Set & RAM', icon: 'memory' },
  { id: 'agent', label: 'AI Agent Context', icon: 'smart_toy' },
  { id: 'benchmarks', label: '7-Baseline Suite', icon: 'speed' },
  { id: 'ablation', label: 'Ablation', icon: 'science' },
];

export function Header({
  activeTab,
  setActiveTab,
  workload,
  setWorkload,
  ramLimit,
  setRamLimit,
  aggression,
  setAggression,
  mode,
  setMode,
  onSimulate,
  isSimulating,
}) {
  return (
    <header className="w-full bg-transparent pt-6 pb-4 mb-2">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-200/80">
        {/* Left Branding & Editorial Title */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200 tracking-wide uppercase">
              ✨ Context-Aware Lifecycle Memory
            </span>
            <span className="text-xs font-medium text-slate-400">
              SOSP / OSDI Systems Research Suite
            </span>
          </div>

          <h1 className="font-serif text-3xl md:text-4xl font-bold text-slate-900 tracking-tight">
            Lifecycle Optimization Suite
          </h1>

          <p className="text-sm text-slate-500 max-w-2xl leading-relaxed mt-1">
            Predictive lifecycle orchestration engine designed to anticipate memory pressure, eliminate cache thrashing,
            proactively trim OS working sets, and optimize AI context tokens.
          </p>
        </div>

        {/* Right Top Capsule Navigation Switcher (matching screenshot) */}
        <div className="flex flex-col items-start lg:items-end gap-2.5">
          <div className="bg-slate-100/90 border border-slate-200/80 p-1 rounded-2xl flex flex-wrap items-center gap-1 shadow-sm">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-white text-slate-900 font-semibold shadow-sm border border-slate-200/80'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                  }`}
                >
                  <span className="material-symbols-outlined text-[16px] text-purple-600">{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Secondary Control Ribbon */}
          <div className="flex items-center gap-2.5 text-xs">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 font-medium hover:border-slate-300 outline-none shadow-xs"
            >
              <option value="mobile">📱 Mobile App Mode</option>
              <option value="agent">🤖 AI Agent Mode</option>
            </select>

            <select
              value={aggression}
              onChange={(e) => setAggression(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 font-medium hover:border-slate-300 outline-none shadow-xs"
            >
              <option value="No Aggression">Preset: No Aggression (6000 MB)</option>
              <option value="Less Aggressive">Preset: Less Aggressive (3500 MB)</option>
              <option value="Aggressive">Preset: Aggressive (2000 MB)</option>
              <option value="Critical">Preset: Critical (1200 MB)</option>
            </select>

            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-2.5 py-1 rounded-lg font-mono font-semibold text-[11px]">
              Budget: {ramLimit.toLocaleString()} MB
            </div>

            <button
              onClick={onSimulate}
              disabled={isSimulating}
              className="bg-slate-900 hover:bg-slate-800 active:bg-black text-white px-3 py-1 rounded-lg font-semibold text-xs shadow-xs transition flex items-center gap-1 disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[14px]">play_arrow</span>
              {isSimulating ? 'Profiling...' : 'Re-Profile'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
