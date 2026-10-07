import React, { useState } from 'react';
import { StateChip } from '../components/StateChip';

const SCENARIOS = [
  {
    id: 'cyclic',
    workloadType: 'bursty',
    title: 'Cyclic Thrashing Workload (Social/Feed Loop)',
    description:
      'Suboptimal reactive LRU evicts items immediately prior to recurrent access (burst of 10 items in tight loop = 100% nested evictions)...',
    reductionBadge: '+98.2% Thrashing Cut',
    inefficientCost: '18,450',
    optimizedCost: '3,210',
    reductionPct: '82.6%',
    savedLabel: '15,240 ms latency saved',
    inefficientSub: 'Thrashing cycles / reactive OOM drop',
    optimizedSub: 'Zero disk I/O / Markov pre-warm',
    inefficientTrace: `/* REACTIVE LRU: Destructive Cyclic Eviction */
[T+088] Access "instagram"   -> Resident RAM: 820 MB
[T+089] Access "camera"      -> Limit exceeded: 2,640 MB / 2,500 MB
[LMK] Evicted: "youtube" (Cold-kill, unsaved state lost)
[LMK] Evicted: "slack"   (Cold-kill, serialized to swap)
[T+090] Access "youtube"     -> CACHE MISS! Cold Storage Reload!
--> Severe Thrashing: Full cold boot (2,340 ms)
--> Major Page Faults: 1,480 faults, UI blocked 1.84 sec
--> NAND Flash Degradation: 380 MB write cycle triggered`,
    optimizedTrace: `/* CALM V2: Predictive Working Set Synthesis */
[T+088] Access "instagram"   -> Priority score: 0.942 (HOT)
[PREDICTOR] Next predicted app: "youtube" (P=0.91, Conf=0.95)
[PROACTIVE] Tier "youtube" -> COMPRESSED (35% footprint, 112 MB)
[PROACTIVE] Evict lowest utility item "slack" to disk early
[T+090] Access "youtube"     -> CACHE HIT (Compressed Tier)!
--> Fast In-RAM Restore: Decompress in-RAM (142 ms vs 2,340 ms)
--> Thrashing eliminated: Working set preserved in budget
--> Total Latency Cut: -93.9% instant launch responsiveness`,
  },
  {
    id: 'bursty',
    workloadType: 'context_switching',
    title: 'Bursty Multi-Modal Context Working Set',
    description:
      'Rapid switching between camera, maps, and feed overflows resident RAM, causing reactive OOM kill cycles and UI freeze...',
    reductionBadge: '+86.5% Latency Drop',
    inefficientCost: '16,200',
    optimizedCost: '2,980',
    reductionPct: '81.6%',
    savedLabel: '13,220 ms latency saved',
    inefficientSub: 'Reactive LMK spikes / UI jank',
    optimizedSub: 'Compressed working set / zRAM hits',
    inefficientTrace: `/* REACTIVE LRU: Multi-Modal Memory Overflow */
[T+142] Launch "camera"      -> Working set spikes +650 MB
[T+143] Launch "maps"        -> PSI stall: 64% memory pressure!
[LMK] Critical Kill: "music_player" & "browser" purged
[T+144] Resume "browser"     -> CACHE MISS! Heavy JIT recompilation
--> Cold Start Latency: 3,120 ms
--> Garbage Collection pause: 280 ms frame freeze
--> Storage Bus Saturation: 45 MB/s disk queue stall`,
    optimizedTrace: `/* CALM V2: Context-Aware Working Set Management */
[T+142] Launch "camera"      -> Anticipate multi-modal burst
[PREDICTOR] Temporal window predicts: "browser" will resume in 3 ticks
[PROACTIVE] Graceful zRAM Tiering: Compress "browser" & "music"
[T+144] Resume "browser"     -> CACHE HIT (In-Memory Unpack)!
--> Instant Resume: 195 ms (Zero UI stutter, 60 FPS maintained)
--> Zero LMK Kills: PSI memory stall kept below 5%
--> Predictor Accuracy: Top-1 hit confirmed (Certainty: 94.2%)`,
  },
  {
    id: 'predictable',
    workloadType: 'predictable',
    title: 'Multi-App Switching with Compressed Tiering',
    description:
      'Retaining cold apps in full uncompressed state forces aggressive LMK kills. Proactive 35% zRAM tiering protects hot pages before context switch...',
    reductionBadge: '+71.5% Cost Reduction',
    inefficientCost: '14,900',
    optimizedCost: '4,250',
    reductionPct: '71.5%',
    savedLabel: '10,650 ms latency saved',
    inefficientSub: 'Full scans / reactive thrashing cycles',
    optimizedSub: 'Index range seeks / pre-warmed working set',
    inefficientTrace: `/* REACTIVE LRU: Suboptimal Resident Memory Bloat */
[T+210] App Switch "slack"   -> Full uncompressed 420 MB in RAM
[T+211] App Switch "docs"    -> Uncompressed 380 MB in RAM
[T+212] Total RAM: 2,750 MB  -> Exceeds 2,500 MB limit!
[LMK] Emergency Trim: Killing background process tree
[T+213] Re-open "slack"      -> CACHE MISS! Cold process re-init
--> Cold Launch: 1,890 ms
--> State Deserialization: IPC overhead 210 ms`,
    optimizedTrace: `/* CALM V2: Proactive 4-Tier Memory Hierarchy */
[T+210] App Switch "slack"   -> Classified CACHED (Priority: 0.62)
[T+211] App Switch "docs"    -> Active set pressure detected
[PROACTIVE] Compact "slack"  -> COMPRESSED tier (147 MB, saved 273 MB)
[T+212] Total RAM: 1,940 MB  -> Safely 560 MB below ceiling
[T+213] Re-open "slack"      -> CACHE HIT (In-Memory Restore)
--> Warm Launch: 110 ms (-94.2% faster)
--> Zero Process Restarts: Clean lifecycle preservation`,
  },
];

export function Overview({ simData, workload, setWorkload, onSimulate, isSimulating }) {
  const [selectedScenarioId, setSelectedScenarioId] = useState('predictable');

  const activeScenario =
    SCENARIOS.find((s) => s.id === selectedScenarioId) || SCENARIOS[2];

  const handleSelectScenario = (scenario) => {
    setSelectedScenarioId(scenario.id);
    if (setWorkload && scenario.workloadType !== workload) {
      setWorkload(scenario.workloadType);
    }
  };

  const calm = simData?.metrics?.CALM;
  const lru = simData?.metrics?.LRU;
  const trace = simData?.traces?.CALM || [];
  const finalStep = trace[trace.length - 1] || {};

  // Dynamic real simulation metrics if available
  const lruLatMs = lru?.avg_launch_latency_sec
    ? Math.round(lru.avg_launch_latency_sec * 10000).toLocaleString()
    : activeScenario.inefficientCost;
  const calmLatMs = calm?.avg_launch_latency_sec
    ? Math.round(calm.avg_launch_latency_sec * 10000).toLocaleString()
    : activeScenario.optimizedCost;
  const reductionPct =
    lru?.avg_launch_latency_sec && calm?.avg_launch_latency_sec
      ? (
          ((lru.avg_launch_latency_sec - calm.avg_launch_latency_sec) /
            lru.avg_launch_latency_sec) *
          100
        ).toFixed(1) + '%'
      : activeScenario.reductionPct;

  return (
    <div className="space-y-6">
      {/* ── Feature 1 Hero Card (matching reference screenshot) ─────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 md:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200/80 tracking-wide uppercase">
                FEATURE 1: PROACTIVE WORKING SET
              </span>
              <span className="text-xs font-medium text-slate-400">
                Lifecycle Transition Synthesis
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight">
              AI Working Set &amp; Cache Thrashing Elimination Engine
            </h2>
            <p className="text-sm text-slate-500 max-w-3xl leading-relaxed mt-2">
              Applies variable-order Markov transitions and cost-utility heuristics to transform naive reactive LRU allocations
              (costly cold-starts, OOM thrashing spikes, disk I/O page faults) into proactive canonical working sets before memory pressure events occur.
            </p>
          </div>

          <div className="flex-shrink-0">
            <button
              onClick={onSimulate}
              disabled={isSimulating}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 active:bg-black text-white text-xs font-semibold shadow-sm hover:shadow transition disabled:opacity-50 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">play_arrow</span>
              <span>{isSimulating ? 'Profiling Engine...' : 'Load Rewritten Workload & Optimize'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Scenario Pattern Selector (3 cards grid) ───────────────────────── */}
      <div>
        <div className="mb-3">
          <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
            SELECT SUBOPTIMAL WORKLOAD PATTERN TO REWRITE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SCENARIOS.map((scenario) => {
            const isSelected = selectedScenarioId === scenario.id;
            return (
              <div
                key={scenario.id}
                onClick={() => handleSelectScenario(scenario)}
                className={`p-5 rounded-xl cursor-pointer transition relative bg-white ${
                  isSelected
                    ? 'border-2 border-slate-900 shadow-sm ring-1 ring-slate-900/5'
                    : 'border border-slate-200/90 hover:border-slate-300 shadow-xs'
                }`}
              >
                <h4 className="font-bold text-slate-900 text-sm mb-1.5 leading-snug">
                  {scenario.title}
                </h4>
                <p className="text-xs text-slate-500 leading-relaxed mb-4">
                  {scenario.description}
                </p>
                <div>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {scenario.reductionBadge}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 3 Metric Bento Cards (Red / Green / Blue) ───────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Inefficient Cost (Red) */}
        <div className="bg-white border border-rose-200/70 rounded-xl p-5 shadow-xs">
          <span className="text-[11px] font-mono font-bold tracking-wider text-rose-600 uppercase block mb-1">
            ORIGINAL INEFFICIENT COST (LRU BASELINE)
          </span>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-bold font-sans text-rose-600 tracking-tight">
              {lruLatMs}
            </span>
            <span className="text-xs text-slate-400 font-medium">ms launch penalty</span>
          </div>
          <span className="text-xs text-slate-500">
            {activeScenario.inefficientSub}
          </span>
        </div>

        {/* Card 2: CALM-Optimized Cost (Green) */}
        <div className="bg-white border border-emerald-200/70 rounded-xl p-5 shadow-xs">
          <span className="text-[11px] font-mono font-bold tracking-wider text-emerald-600 uppercase block mb-1">
            CALM-OPTIMIZED COST
          </span>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-bold font-sans text-emerald-600 tracking-tight">
              {calmLatMs}
            </span>
            <span className="text-xs text-slate-400 font-medium">ms launch penalty</span>
          </div>
          <span className="text-xs text-slate-500">
            {activeScenario.optimizedSub}
          </span>
        </div>

        {/* Card 3: Demonstrated Cost Reduction (Blue) */}
        <div className="bg-white border border-blue-200/70 rounded-xl p-5 shadow-xs">
          <span className="text-[11px] font-mono font-bold tracking-wider text-blue-600 uppercase block mb-1">
            DEMONSTRATED COST REDUCTION
          </span>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-bold font-sans text-blue-600 tracking-tight">
              {reductionPct}
            </span>
            <span className="text-xs text-slate-400 font-medium">savings</span>
          </div>
          <span className="text-xs text-slate-500">
            {activeScenario.savedLabel}
          </span>
        </div>
      </div>

      {/* ── Dual Side-by-Side Trace Comparison Panels ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel: Original Suboptimal Allocation */}
        <div className="bg-white border border-rose-200/90 rounded-2xl p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-rose-100">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-rose-500 text-[18px]">
                warning
              </span>
              <h3 className="text-sm font-bold text-slate-900">
                Original Suboptimal Allocation (Reactive LRU)
              </h3>
            </div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
              Inefficient / Thrashing
            </span>
          </div>

          <div className="bg-slate-50/80 border border-slate-200/70 rounded-xl p-4 font-mono text-xs text-slate-800 leading-relaxed overflow-x-auto flex-1">
            <pre className="font-mono whitespace-pre">{activeScenario.inefficientTrace}</pre>
          </div>
        </div>

        {/* Right Panel: CALM Proactive Allocation */}
        <div className="bg-white border border-emerald-300 rounded-2xl p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-emerald-100">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-emerald-600 text-[18px]">
                check_circle
              </span>
              <h3 className="text-sm font-bold text-slate-900">
                CALM Proactive Working Set Orchestration
              </h3>
            </div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Canonical Form / Optimized
            </span>
          </div>

          <div className="bg-emerald-50/20 border border-emerald-200/60 rounded-xl p-4 font-mono text-xs text-slate-800 leading-relaxed overflow-x-auto flex-1">
            <pre className="font-mono whitespace-pre">{activeScenario.optimizedTrace}</pre>
          </div>
        </div>
      </div>

      {/* ── Technical Systems Benchmark Matrix & Engine State Snapshot ──────── */}
      {simData && simData.metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
          {/* Strategy Matrix (8 cols) */}
          <div className="lg:col-span-8 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Strategy Performance Matrix (Unseen Evaluation Stream)
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Benchmarked against 7 canonical memory replacement algorithms
                </p>
              </div>
              <span className="text-xs text-slate-400 font-mono bg-slate-100 px-2 py-0.5 rounded">
                N = {simData.eval_len} Events
              </span>
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
                    <th className="py-2.5 px-3">Thrashing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {Object.keys(simData.metrics).map((strategyName) => {
                    const m = simData.metrics[strategyName];
                    const isCalm = strategyName === 'CALM';
                    return (
                      <tr
                        key={strategyName}
                        className={
                          isCalm
                            ? 'bg-blue-50/60 font-semibold text-blue-900'
                            : 'hover:bg-slate-50 text-slate-700'
                        }
                      >
                        <td className="py-2 px-3 font-sans font-medium text-slate-900">
                          {strategyName}{' '}
                          {isCalm && (
                            <span className="ml-1 text-[10px] bg-blue-600 text-white px-1.5 py-0.5 rounded font-bold">
                              V2 PROACTIVE
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3 font-bold">
                          {m.cache_hit_rate_pct.toFixed(1)}%
                        </td>
                        <td className="py-2 px-3">
                          {m.avg_launch_latency_sec.toFixed(4)}s
                        </td>
                        <td className="py-2 px-3">
                          {m.p95_launch_latency_sec.toFixed(4)}s
                        </td>
                        <td className="py-2 px-3">
                          {m.avg_ram_mb.toLocaleString()} MB
                        </td>
                        <td className="py-2 px-3">
                          {m.thrashing_count === 0 ? (
                            <span className="text-emerald-600 font-bold">0 (None)</span>
                          ) : (
                            <span className="text-rose-600">{m.thrashing_count}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Engine State Snapshot (4 cols) */}
          <div className="lg:col-span-4 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
            <div className="pb-3 mb-4 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                Final Working Set Snapshot
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Proactive tiers across tracked processes
              </p>
            </div>

            <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
              {finalStep.post_states &&
                Object.entries(finalStep.post_states).map(([item, state]) => {
                  const priority = finalStep.priority_scores?.[item] || 0;
                  return (
                    <div
                      key={item}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/60"
                    >
                      <div>
                        <div className="text-xs font-semibold text-slate-800">{item}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          Utility: {priority.toFixed(3)}
                        </div>
                      </div>
                      <StateChip state={state} />
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
