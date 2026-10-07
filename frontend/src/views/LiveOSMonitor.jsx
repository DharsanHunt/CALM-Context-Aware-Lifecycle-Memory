import React, { useEffect, useState } from 'react';
import { fetchRealOSStatus, trimRealOSProcess, trimAllRealOSProcesses } from '../api';
import { BentoCard } from '../components/BentoCard';

export function LiveOSMonitor() {
  const [osData, setOsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trimmingPid, setTrimmingPid] = useState(null);
  const [trimResult, setTrimResult] = useState(null);
  const [isBulkTrimming, setIsBulkTrimming] = useState(false);

  const loadData = async () => {
    try {
      const data = await fetchRealOSStatus();
      setOsData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleTrim = async (pid) => {
    setTrimmingPid(pid);
    setTrimResult(null);
    try {
      const res = await trimRealOSProcess(pid);
      setTrimResult(res);
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setTrimmingPid(null);
    }
  };

  const handleBulkTrim = async () => {
    setIsBulkTrimming(true);
    setTrimResult(null);
    try {
      const res = await trimAllRealOSProcesses(50.0);
      setTrimResult({
        success: true,
        action: 'BulkEmptyWorkingSet',
        reclaimed_mb: res.total_reclaimed_mb,
        count: res.trimmed_process_count,
      });
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setIsBulkTrimming(false);
    }
  };

  if (loading || !osData) {
    return <div className="p-8 text-center text-slate-500">Connecting to Host OS Memory Subsystem...</div>;
  }

  const mem = osData.memory || {};
  const procs = osData.processes || [];

  const pressureColors = {
    LOW: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    MODERATE: 'text-blue-600 bg-blue-50 border-blue-200',
    HIGH: 'text-amber-600 bg-amber-50 border-amber-200',
    CRITICAL: 'text-rose-600 bg-rose-50 border-rose-200',
  };

  return (
    <div className="space-y-6">
      {/* Host Physical Memory Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <BentoCard
          title="Physical RAM Used"
          value={`${(mem.used_mb / 1024).toFixed(2)} GB`}
          delta={`${mem.percent_used?.toFixed(1)}% of ${(mem.total_mb / 1024).toFixed(1)} GB`}
          deltaType={mem.percent_used > 85 ? 'negative' : 'neutral'}
        />
        <BentoCard
          title="Available Physical RAM"
          value={`${(mem.available_mb / 1024).toFixed(2)} GB`}
          delta="Free Standby + Zeroed Pages"
          deltaType="positive"
        />
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col justify-between">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Host Memory Pressure
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded text-sm font-bold border ${
                pressureColors[mem.pressure_level] || 'text-slate-700 bg-slate-100'
              }`}
            >
              {mem.pressure_level}
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-2">Live Kernel Pressure Signal</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col justify-between">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Proactive Working Set Trim
          </div>
          <button
            onClick={handleBulkTrim}
            disabled={isBulkTrimming}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-2 px-3 rounded shadow-sm transition disabled:opacity-50"
          >
            {isBulkTrimming ? 'Flushing Pages...' : '⚡ Bulk Reclaim Background RAM'}
          </button>
          <div className="text-[11px] text-slate-400 mt-1">Calls Win32 EmptyWorkingSet</div>
        </div>
      </div>

      {/* Action Banner Feedback */}
      {trimResult && (
        <div
          className={`p-4 rounded-lg border text-xs font-mono flex items-center justify-between ${
            trimResult.success ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {trimResult.action === 'BulkEmptyWorkingSet' ? (
            <div>
              <b>[BULK TRIM SUCCESS]</b> Reclaimed <b>{trimResult.reclaimed_mb} MB</b> of physical RAM across{' '}
              <b>{trimResult.count}</b> background processes! Pages flushed to OS standby list.
            </div>
          ) : trimResult.success ? (
            <div>
              <b>[PROCESS TRIM SUCCESS]</b> PID {trimResult.pid} ({trimResult.name}): Working set reduced from{' '}
              {trimResult.before_rss_mb} MB ➔ {trimResult.after_rss_mb} MB (<b>{trimResult.reclaimed_mb} MB</b> reclaimed /{' '}
              {trimResult.reclaimed_pct}%).
            </div>
          ) : (
            <div>
              <b>[TRIM FAILED]</b> PID {trimResult.pid}: {trimResult.reason}
            </div>
          )}
          <button onClick={() => setTrimResult(null)} className="text-slate-400 hover:text-slate-600 ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Live Running Processes Table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex justify-between items-center mb-4 pb-2 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Live Host Process Memory & Page Fault Telemetry</h3>
            <p className="text-xs text-slate-400">
              Real-time monitoring of host applications with virtual memory working sets and dynamic NT priority classes.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 px-3 py-1.5 rounded font-medium transition"
          >
            ↻ Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-sans">PID</th>
                <th className="py-2.5 px-3 font-sans">Process Name</th>
                <th className="py-2.5 px-3">RSS (MB)</th>
                <th className="py-2.5 px-3">Working Set</th>
                <th className="py-2.5 px-3">Peak WS</th>
                <th className="py-2.5 px-3">Private</th>
                <th className="py-2.5 px-3">Page Faults</th>
                <th className="py-2.5 px-3 font-sans">Priority</th>
                <th className="py-2.5 px-3">CPU %</th>
                <th className="py-2.5 px-3 font-sans text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {procs.map((p) => {
                const isTrimming = trimmingPid === p.pid;
                return (
                  <tr key={p.pid} className="hover:bg-slate-50">
                    <td className="py-2 px-3 text-slate-500">{p.pid}</td>
                    <td className="py-2 px-3 font-sans font-medium text-slate-900">{p.name}</td>
                    <td className="py-2 px-3 text-blue-600 font-bold">{p.rss_mb} MB</td>
                    <td className="py-2 px-3 text-slate-700">{p.wset_mb} MB</td>
                    <td className="py-2 px-3 text-slate-400">{p.peak_wset_mb} MB</td>
                    <td className="py-2 px-3 text-slate-500">{p.private_mb} MB</td>
                    <td className="py-2 px-3 text-slate-600">{p.page_faults.toLocaleString()}</td>
                    <td className="py-2 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-700 font-sans font-semibold">
                        {p.priority_class}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-500">{p.cpu_percent}%</td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => handleTrim(p.pid)}
                        disabled={isTrimming}
                        className="bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 px-2.5 py-1 rounded text-[11px] font-sans font-medium transition border border-slate-200"
                      >
                        {isTrimming ? 'Trimming...' : 'Trim WS'}
                      </button>
                    </td>
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
