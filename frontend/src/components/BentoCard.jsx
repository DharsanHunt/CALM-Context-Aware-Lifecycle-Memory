import React from 'react';

export function BentoCard({ title, value, delta, deltaType = 'positive', subtitle }) {
  const deltaColor =
    deltaType === 'positive'
      ? 'text-emerald-600'
      : deltaType === 'negative'
      ? 'text-rose-600'
      : 'text-slate-500';

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm hover:shadow transition-shadow">
      <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
        {title}
      </div>
      <div className="text-3xl font-bold text-slate-900 tracking-tight">{value}</div>
      {delta && <div className={`text-xs font-medium mt-1.5 ${deltaColor}`}>{delta}</div>}
      {subtitle && <div className="text-xs text-slate-400 mt-1">{subtitle}</div>}
    </div>
  );
}
