import React, { useEffect, useState } from 'react';
import { fetchAgentChunks, accessAgentChunk } from '../api';
import { StateChip } from '../components/StateChip';

export function AgentMemory() {
  const [agentData, setAgentData] = useState(null);
  const [selectedChunk, setSelectedChunk] = useState('task_curr');
  const [accessedContent, setAccessedContent] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadChunks = () => {
    fetchAgentChunks()
      .then((data) => {
        setAgentData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadChunks();
  }, []);

  const handleAccess = async () => {
    if (!selectedChunk) return;
    try {
      const res = await accessAgentChunk(selectedChunk);
      setAccessedContent(res.content);
      loadChunks();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading || !agentData) {
    return <div className="p-8 text-center text-slate-500">Loading AI Agent Context Memory...</div>;
  }

  const chunks = agentData.chunks || [];
  const residentBytes = agentData.total_resident_bytes || 0;
  const budget = agentData.byte_budget || 1500;
  const utilPct = budget > 0 ? (residentBytes / budget) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Agent Telemetry & Sizing */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Context Memory Footprint</div>
          <div className="text-2xl font-bold text-slate-900">{residentBytes.toLocaleString()} Bytes</div>
          <div className="text-xs text-slate-400 mt-1">Prompt Budget: {budget.toLocaleString()} Bytes ({utilPct.toFixed(1)}%)</div>
          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-3">
            <div className="bg-blue-600 h-full rounded-full" style={{ width: `${Math.min(100, utilPct)}%` }}></div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Context Chunks</div>
          <div className="text-2xl font-bold text-emerald-600">
            {chunks.filter((c) => c.State === 'ACTIVE').length} / {chunks.length}
          </div>
          <div className="text-xs text-slate-400 mt-1">Directly injected in current prompt</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Real zlib Compression</div>
          <div className="text-2xl font-bold text-amber-600">
            {chunks.filter((c) => c.State === 'COMPRESSED').length} Chunks
          </div>
          <div className="text-xs text-slate-400 mt-1">Compressed in-RAM working memory</div>
        </div>
      </div>

      {/* Context Chunk Table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">AI Agent Working Context Chunks</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-sans">ID</th>
                <th className="py-2.5 px-3 font-sans">Type</th>
                <th className="py-2.5 px-3 font-sans">Title</th>
                <th className="py-2.5 px-3 font-sans">State</th>
                <th className="py-2.5 px-3">Raw</th>
                <th className="py-2.5 px-3">Comp</th>
                <th className="py-2.5 px-3">Savings</th>
                <th className="py-2.5 px-3">Resident</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {chunks.map((c) => (
                <tr key={c['Chunk ID']} className="hover:bg-slate-50">
                  <td className="py-2 px-3 font-medium text-slate-700">{c['Chunk ID']}</td>
                  <td className="py-2 px-3 font-sans text-slate-500">{c.Type}</td>
                  <td className="py-2 px-3 font-sans font-medium text-slate-900">{c.Title}</td>
                  <td className="py-2 px-3">
                    <StateChip state={c.State} />
                  </td>
                  <td className="py-2 px-3 text-slate-500">{c['Raw (B)']} B</td>
                  <td className="py-2 px-3 text-amber-600">{c['Comp (B)']} B</td>
                  <td className="py-2 px-3 text-emerald-600 font-semibold">{c.Savings}</td>
                  <td className="py-2 px-3 font-bold text-slate-800">{c['Resident (B)']} B</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Query & Injection Sandbox */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">⚡ Query & Decompress Context Chunk</h3>
        <p className="text-xs text-slate-400 mb-4">
          Select a chunk to simulate real-time query retrieval, zlib decompression, and promotion to <b>ACTIVE</b>.
        </p>

        <div className="flex gap-3 items-center">
          <select
            value={selectedChunk}
            onChange={(e) => setSelectedChunk(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded px-3 py-2 font-medium text-slate-700 outline-none flex-1"
          >
            {chunks.map((c) => (
              <option key={c['Chunk ID']} value={c['Chunk ID']}>
                [{c.State}] {c.Title} ({c['Chunk ID']})
              </option>
            ))}
          </select>
          <button
            onClick={handleAccess}
            className="bg-blue-600 text-white text-xs font-semibold px-4 py-2 rounded hover:bg-blue-700 transition shadow-sm"
          >
            Access / Inject Chunk
          </button>
        </div>

        {accessedContent && (
          <div className="mt-4 p-3 bg-slate-900 text-emerald-400 rounded text-xs font-mono overflow-x-auto">
            <div className="text-[10px] text-slate-400 uppercase font-sans mb-1">// Retrieved & Decompressed Content:</div>
            {accessedContent}
          </div>
        )}
      </div>
    </div>
  );
}
