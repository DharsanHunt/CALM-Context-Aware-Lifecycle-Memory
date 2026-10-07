import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Overview } from './views/Overview';
import { LifecycleMonitor } from './views/LifecycleMonitor';
import { Prediction } from './views/Prediction';
import { MemoryManagement } from './views/MemoryManagement';
import { BenchmarkSuite } from './views/BenchmarkSuite';
import { ComponentAblation } from './views/ComponentAblation';
import { AgentMemory } from './views/AgentMemory';
import { LiveOSMonitor } from './views/LiveOSMonitor';
import { runSimulation } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [mode, setMode] = useState('mobile');
  const [workload, setWorkload] = useState('predictable');
  const [aggression, setAggression] = useState('Less Aggressive');
  const [ramLimit, setRamLimit] = useState(2500);
  const [compressedFactor, setCompressedFactor] = useState(0.35);
  const [seed, setSeed] = useState(42);

  const [simData, setSimData] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      const data = await runSimulation({
        workload_type: workload,
        num_events: 350,
        seed: seed,
        ram_limit_mb: ramLimit,
        compressed_factor: compressedFactor,
        aggression: aggression,
        mode: mode,
      });
      setSimData(data);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  // Run on mount or when key presets change
  useEffect(() => {
    if (aggression === 'No Aggression') setRamLimit(6000);
    else if (aggression === 'Less Aggressive') setRamLimit(3500);
    else if (aggression === 'Aggressive') setRamLimit(2000);
    else if (aggression === 'Critical') setRamLimit(1200);
  }, [aggression]);

  useEffect(() => {
    handleSimulate();
  }, [workload, ramLimit, aggression, mode]);

  const tabTitles = {
    overview: 'System Overview',
    lifecycle: 'Lifecycle Monitor',
    prediction: 'Prediction & Confidence',
    memory: 'Memory Management',
    benchmarks: 'Benchmark Suite',
    ablation: 'Component Ablation',
    agent: 'AI Agent Memory (Mode B)',
    real_os: 'Host Operating System Monitor',
  };

  return (
    <div className="min-h-screen bg-[#F8F9FB] text-slate-800 antialiased selection:bg-purple-100 selection:text-purple-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          workload={workload}
          setWorkload={setWorkload}
          ramLimit={ramLimit}
          setRamLimit={setRamLimit}
          aggression={aggression}
          setAggression={setAggression}
          mode={mode}
          setMode={setMode}
          onSimulate={handleSimulate}
          isSimulating={isSimulating}
        />

        <main className="mt-6">
          {activeTab === 'overview' && (
            <Overview
              simData={simData}
              workload={workload}
              setWorkload={setWorkload}
              onSimulate={handleSimulate}
              isSimulating={isSimulating}
            />
          )}
          {activeTab === 'lifecycle' && <LifecycleMonitor simData={simData} />}
          {activeTab === 'prediction' && <Prediction simData={simData} />}
          {activeTab === 'memory' && <MemoryManagement simData={simData} config={simData?.config || {}} />}
          {activeTab === 'benchmarks' && <BenchmarkSuite simData={simData} />}
          {activeTab === 'ablation' && <ComponentAblation />}
          {activeTab === 'agent' && <AgentMemory />}
          {activeTab === 'real_os' && <LiveOSMonitor />}
        </main>
      </div>
    </div>
  );
}
