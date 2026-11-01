import React, { useState, useEffect, useCallback } from 'react';
import Topbar from './components/Topbar';
import ReviewQueueTab from './components/ReviewQueueTab';
import AuditTrailTab from './components/AuditTrailTab';
import AnalyticsTab from './components/AnalyticsTab';
import SandboxTab from './components/SandboxTab';
import { fetchHealth, fetchQueue, fetchAuditLog, fetchMetrics, fetchMessage } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('queue');
  const [analyst, setAnalyst] = useState('analyst_arsh');
  const [health, setHealth] = useState(null);
  const [queue, setQueue] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [auditEntries, setAuditEntries] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [hData, qData, aData, mData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchQueue(100).catch(() => []),
        fetchAuditLog(100).catch(() => ({ entries: [] })),
        fetchMetrics().catch(() => null)
      ]);

      setHealth(hData);
      setQueue(qData);
      setAuditEntries(aData.entries || []);
      setMetrics(mData);

      // Auto-select first queue message if none selected or if previous selected is no longer in queue
      if (qData && qData.length > 0) {
        setSelectedMessage((prev) => {
          if (!prev) return qData[0];
          const exists = qData.find((m) => m.id === prev.id);
          return exists || qData[0];
        });
      } else {
        setSelectedMessage(null);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handler when an item is selected from the queue
  const handleSelectMessage = async (item) => {
    try {
      const fullMsg = await fetchMessage(item.id);
      setSelectedMessage(fullMsg);
    } catch {
      setSelectedMessage(item);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A12] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      
      {/* Top Navbar */}
      <Topbar
        analyst={analyst}
        setAnalyst={setAnalyst}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
        health={health}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        queueCount={queue.length}
      />

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'queue' && (
          <ReviewQueueTab
            queue={queue}
            selectedMessage={selectedMessage}
            onSelectMessage={handleSelectMessage}
            analyst={analyst}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTrailTab auditEntries={auditEntries} />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsTab metrics={metrics} />
        )}

        {activeTab === 'sandbox' && (
          <SandboxTab onEmailIngested={loadData} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 text-center text-xs text-slate-500 font-mono">
        PhishTrap SecOps Console &bull; Human-in-the-Loop Real-Time Phishing Mitigation &bull; INT-395 Project
      </footer>

    </div>
  );
}

