import React, { useState } from 'react';
import { BentoCard } from '../components/BentoCard';

export function Prediction({ simData }) {
  if (!simData) return null;

  const [selectedApp, setSelectedApp] = useState('Chrome');
  const matrix = simData.transition_matrix || {};
  const predMetrics = simData.pred_metrics || {};
  const lookaheads = simData.lookaheads || {};
  const apps = ['Chrome', 'YouTube', 'Spotify', 'Gemini', 'WhatsApp'];

  const currentDist = matrix[selectedApp] || {};
  const currentPaths = lookaheads[selectedApp] || [];

  return (
    <div className="space-y-6">
      {/* Prediction Accuracy Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <BentoCard
          title="Top-1 Accuracy"
          value={`${predMetrics.top_1_accuracy?.toFixed(1)}%`}
          delta="Single-candidate match"
          deltaType="positive"
        />
        <BentoCard
          title="Top-3 Accuracy"
          value={`${predMetrics.top_3_accuracy?.toFixed(1)}%`}
          delta="Top-3 candidate match"
          deltaType="positive"
        />
        <BentoCard
          title="Mean Certainty"
          value={`${((predMetrics.mean_confidence || 0) * 100).toFixed(1)}%`}
          delta="Information-theoretic confidence"
          deltaType="neutral"
        />
        <BentoCard
          title="Brier Calibration Error"
          value={predMetrics.brier_score?.toFixed(4)}
          delta="Mean squared probability error"
          deltaType="neutral"
        />
      </div>

      {/* Learned Transition Matrix Heatmap */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex justify-between items-center mb-4 pb-2 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Learned Transition Probability Matrix: P(Next | Current)</h3>
            <p className="text-xs text-slate-400">Strictly trained on 70% historical split with Laplace smoothing (zero future leakage)</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-sans">From \ To</th>
                {apps.map((app) => (
                  <th key={app} className="py-2.5 px-3 font-sans text-center">{app}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {apps.map((src) => (
                <tr key={src} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{src}</td>
                  {apps.map((dst) => {
                    const prob = matrix[src]?.[dst] || 0;
                    const bgIntensity = Math.min(prob * 1.2, 0.8);
                    return (
                      <td
                        key={dst}
                        className="py-2.5 px-3 text-center"
                        style={{
                          backgroundColor: prob > 0.3 ? `rgba(37, 99, 235, ${bgIntensity})` : 'transparent',
                          color: prob > 0.4 ? '#ffffff' : '#1e293b',
                          fontWeight: prob > 0.3 ? '600' : 'normal',
                        }}
                      >
                        {(prob * 100).toFixed(1)}%
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interactive Lookahead Simulator */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-6 bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-800">Single-Step Distribution: P(Next | {selectedApp})</h3>
            <select
              value={selectedApp}
              onChange={(e) => setSelectedApp(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded px-2.5 py-1 font-medium text-slate-700 outline-none"
            >
              {apps.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>

          <div className="space-y-3">
            {Object.entries(currentDist).map(([dst, p]) => (
              <div key={dst}>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-700">{dst}</span>
                  <span className="font-mono text-blue-600 font-semibold">{(p * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 rounded-full" style={{ width: `${p * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="md:col-span-6 bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-800 mb-2">Multi-Step Lookahead Paths (P(A → B → C))</h3>
            <p className="text-xs text-slate-400 mb-4">Top-ranked sequential paths starting from {selectedApp}</p>

            <div className="space-y-2.5">
              {currentPaths.map((path, idx) => (
                <div key={idx} className="p-3 rounded border border-slate-100 bg-slate-50/80 font-mono text-xs flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-800">{selectedApp}</span>
                    <span className="text-slate-400 mx-1.5">➔</span>
                    <span className="font-semibold text-blue-700">{path[0]?.[0]}</span>
                    <span className="text-slate-400 text-[10px] ml-1">({(path[0]?.[1] * 100).toFixed(1)}%)</span>
                    <span className="text-slate-400 mx-1.5">➔</span>
                    <span className="font-semibold text-purple-700">{path[1]?.[0]}</span>
                  </div>
                  <div className="font-bold text-slate-700 text-[11px]">
                    cum: {(path[1]?.[1] * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3 bg-blue-50/60 border border-blue-100 rounded mt-4 text-xs text-blue-800">
            💡 <b>Confidence Gating:</b> When certainty exceeds threshold (&gt;0.70), CALM prewarms top candidates directly to <b>CACHED</b> or <b>COMPRESSED</b> state.
          </div>
        </div>
      </div>
    </div>
  );
}
