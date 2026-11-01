import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import { Search, History, UserCheck, Calendar, ArrowRight, Shield } from 'lucide-react';

export default function AuditTrailTab({ auditEntries = [] }) {
  const [search, setSearch] = useState('');

  const filteredEntries = auditEntries.filter((e) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      e.message_id?.toLowerCase().includes(s) ||
      e.reviewer_id?.toLowerCase().includes(s) ||
      e.reason?.toLowerCase().includes(s) ||
      e.subject?.toLowerCase().includes(s)
    );
  });

  return (
    <div className="space-y-6">
      
      {/* Header & Filter Card */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-bold text-white">Immutable SOC Audit Trail</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographically logged regulatory compliance trail for all Human-in-the-Loop decision overrides.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-full md:w-72">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by message, reviewer, or reason..."
              className="w-full bg-[#070A12] border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>
          <span className="text-xs font-mono font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-3 py-2 rounded-xl whitespace-nowrap">
            {filteredEntries.length} Records
          </span>
        </div>
      </div>

      {/* Audit Timeline List */}
      <div className="space-y-3">
        {filteredEntries.length === 0 ? (
          <div className="bg-[#0D1424]/40 border border-white/5 rounded-2xl p-12 text-center text-slate-500 text-xs">
            <Shield className="w-10 h-10 mx-auto mb-2 text-slate-600" />
            No audit records match the current filter.
          </div>
        ) : (
          filteredEntries.map((entry) => (
            <div
              key={entry.id}
              className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-3 hover:border-white/20 transition"
            >
              {/* Top Row: IDs, Transition, Reviewer, Timestamp */}
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    {entry.message_id}
                  </span>
                  <span className="text-slate-400 font-medium">|</span>
                  <span className="text-slate-200 font-semibold">{entry.subject || '(Subject Unavailable)'}</span>
                </div>

                <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                  <div className="flex items-center gap-1">
                    <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-slate-300 font-semibold">{entry.reviewer_id}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>{entry.timestamp}</span>
                  </div>
                </div>
              </div>

              {/* Status Transition Row */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 font-medium">Transition:</span>
                <StatusBadge status={entry.previous_status} size="xs" />
                <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                <StatusBadge status={entry.new_status} size="xs" />
              </div>

              {/* Justification Box */}
              <div className="bg-[#070A12] border border-white/5 rounded-xl p-3.5 text-xs text-slate-300 font-sans border-l-2 border-l-indigo-500">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Analyst Rationale
                </span>
                "{entry.reason}"
              </div>
            </div>
          ))
        )}
      </div>

    </div>
  );
}

