/**
 * API client interacting with CALM V2 FastAPI backend.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchPresets() {
  const res = await fetch(`${API_BASE}/config/presets`);
  return res.json();
}

export async function runSimulation(payload) {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Simulation failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchBenchmarkSummary() {
  const res = await fetch(`${API_BASE}/benchmarks/summary`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchAblationSummary() {
  const res = await fetch(`${API_BASE}/benchmarks/ablation`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchAgentChunks() {
  const res = await fetch(`${API_BASE}/agent/chunks`);
  return res.json();
}

export async function accessAgentChunk(chunkId) {
  const res = await fetch(`${API_BASE}/agent/access`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chunk_id: chunkId }),
  });
  return res.json();
}
