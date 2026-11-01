import React from 'react';
import { Shield, RefreshCw, Radio, UserCheck, Layers } from 'lucide-react';

export default function Topbar({ 
  analyst, 
  setAnalyst, 
  onRefresh, 
  isRefreshing, 
  health,
  activeTab,
  setActiveTab,
  queueCount = 0
}) {
  const tabs = [
    { id: 'queue', label: 'Review Queue', badge: queueCount },
    { id: 'audit', label: 'Audit Trail' },
    { id: 'analytics', label: 'Triage Telemetry' },
    { id: 'sandbox', label: 'Live Test Sandbox' },
  ];

  return (
    <header className="border-b border-white/10 bg-[#0B101D]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Brand & Live Pulse */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-xl text-indigo-400">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight text-white font-sans">
                  PHISHTRAP
                </span>
                <span className="text-[10px] tracking-widest font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-1.5 py-0.5 rounded">
                  SOC v1.0
                </span>
              </div>
              <div className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 pulse-live shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                <span>Multi-Agent Stream Active</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center bg-[#070A12] p-1 rounded-xl border border-white/5 space-x-1">
            {tabs.map((t) => {
              const active = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    active
                      ? 'bg-gradient-to-r from-indigo-500/20 to-cyan-500/20 text-white border border-indigo-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                  }`}
                >
                  <span>{t.label}</span>
                  {t.badge !== undefined && t.badge > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
                      {t.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* SecOps Metadata & Controls */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 bg-[#0E1527] border border-white/10 px-3 py-1.5 rounded-lg text-xs">
              <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-400">Analyst:</span>
              <input
                type="text"
                value={analyst}
                onChange={(e) => setAnalyst(e.target.value)}
                className="bg-transparent text-slate-200 font-mono text-xs focus:outline-none w-28 border-b border-white/20 focus:border-indigo-400"
                placeholder="analyst_handle"
              />
            </div>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0E1527] hover:bg-slate-800 border border-white/10 text-xs font-medium text-slate-300 transition"
              title="Refresh Queue & Metrics"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
              <span className="hidden sm:inline">Sync</span>
            </button>
          </div>

        </div>

        {/* Mobile Nav Row */}
        <div className="flex md:hidden overflow-x-auto py-2 border-t border-white/5 gap-2 scrollbar-none">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold ${
                activeTab === t.id
                  ? 'bg-indigo-500/20 text-white border border-indigo-500/40'
                  : 'text-slate-400'
              }`}
            >
              <span>{t.label}</span>
              {t.badge !== undefined && t.badge > 0 && (
                <span className="text-[10px] px-1 rounded-full bg-amber-500/20 text-amber-300">
                  {t.badge}
                </span>
              )}
            </button>
          ))}
        </div>

      </div>
    </header>
  );
}

