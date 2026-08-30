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
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Side Navigation Bar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onSimulate={handleSimulate}
        isSimulating={isSimulating}
      />

      {/* Main Content Area */}
      <div className="flex-1 ml-56 flex flex-col min-h-screen">
        <Header
          activeTabTitle={tabTitles[activeTab] || 'CALM Console'}
          workload={workload}
          setWorkload={setWorkload}
          ramLimit={ramLimit}
          setRamLimit={setRamLimit}
          aggression={aggression}
          setAggression={setAggression}
          mode={mode}
          setMode={setMode}
        />

        <main className="flex-1 mt-16 p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'overview' && <Overview simData={simData} />}
          {activeTab === 'lifecycle' && <LifecycleMonitor simData={simData} />}
          {activeTab === 'prediction' && <Prediction simData={simData} />}
          {activeTab === 'memory' && <MemoryManagement simData={simData} config={simData?.config || {}} />}
          {activeTab === 'benchmarks' && <BenchmarkSuite simData={simData} />}
          {activeTab === 'ablation' && <ComponentAblation />}
          {activeTab === 'agent' && <AgentMemory />}
        </main>
      </div>
    </div>
  );
}
