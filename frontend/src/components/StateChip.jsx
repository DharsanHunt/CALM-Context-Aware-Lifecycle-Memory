import React from 'react';

export function StateChip({ state }) {
  const styles = {
    ACTIVE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    CACHED: 'bg-blue-50 text-blue-700 border-blue-200',
    COMPRESSED: 'bg-amber-50 text-amber-700 border-amber-200',
    ARCHIVED: 'bg-rose-50 text-rose-700 border-rose-200',
  };

  const styleClass = styles[state] || 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-semibold border ${styleClass}`}>
      {state}
    </span>
  );
}
