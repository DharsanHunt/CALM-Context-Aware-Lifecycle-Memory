import React from 'react';

const TABS = [
  { id: 'overview', label: 'Overview', icon: 'dashboard' },
  { id: 'lifecycle', label: 'Lifecycle', icon: 'analytics' },
  { id: 'prediction', label: 'Prediction', icon: 'query_stats' },
  { id: 'memory', label: 'Memory', icon: 'memory' },
  { id: 'benchmarks', label: 'Benchmarks', icon: 'speed' },
  { id: 'ablation', label: 'Ablation', icon: 'science' },
  { id: 'agent', label: 'Agent Memory', icon: 'smart_toy' },
  { id: 'real_os', label: 'Host OS Monitor', icon: 'terminal' },
];

export function Sidebar({ activeTab, setActiveTab, onSimulate, isSimulating }) {
  return (
    <nav className="w-56 h-screen fixed left-0 top-0 bg-white border-r border-slate-200 flex flex-col z-50">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-200 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
          C
        </div>
        <div>
          <h1 className="font-bold text-slate-900 leading-none text-base">CALM</h1>
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-1">Systems Console</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Sidebar Footer Controls */}
      <div className="p-3 border-t border-slate-200 space-y-2">
        <button
          onClick={onSimulate}
          disabled={isSimulating}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-md bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition shadow-sm"
        >
          <span className="material-symbols-outlined text-[16px]">play_arrow</span>
          {isSimulating ? 'Simulating...' : 'Run Simulation'}
        </button>
      </div>
    </nav>
  );
}
