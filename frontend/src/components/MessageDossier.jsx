import React from 'react';
import StatusBadge from './StatusBadge';
import ScoreBar from './ScoreBar';
import { Mail, Globe, Shield, Calendar, User, History } from 'lucide-react';

export default function MessageDossier({ message, onOpenOverride }) {
  if (!message) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 text-center text-slate-500 bg-[#0A0F1D]/50 rounded-2xl border border-white/5">
        <Mail className="w-12 h-12 stroke-[1.25] text-slate-600 mb-3" />
        <h3 className="text-base font-semibold text-slate-300">No Email Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Select an ambiguous message from the triage queue on the left to examine defanged URLs, analyze ML feature contributions, and execute an override.
        </p>
      </div>
    );
  }

  const urls = message.urls || [];
  const overrides = message.overrides || [];

  return (
    <div className="space-y-6">
      
      {/* Dossier Header Card */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-32 bg-indigo-500/5 blur-3xl pointer-events-none" />

        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-md border border-indigo-500/20">
              {message.id}
            </span>
            <StatusBadge status={message.current_status} />
          </div>

          <button
            onClick={onOpenOverride}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-lg shadow-indigo-600/25 active:scale-95"
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Analyst Override</span>
          </button>
        </div>

        {/* Message Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs">
          <div>
            <div className="text-slate-400 font-medium mb-1 flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-slate-500" />
              <span>Subject:</span>
            </div>
            <div className="font-semibold text-slate-100 text-sm">
              {message.subject || '(No Subject)'}
            </div>
          </div>

          <div>
            <div className="text-slate-400 font-medium mb-1 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-slate-500" />
              <span>Sender Address:</span>
            </div>
            <div className="font-mono text-cyan-400 bg-cyan-950/30 px-2 py-0.5 rounded border border-cyan-500/20 inline-block">
              {message.sender}
            </div>
          </div>

          <div>
            <div className="text-slate-400 font-medium mb-1 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <span>Timestamp:</span>
            </div>
            <div className="text-slate-300 font-mono text-[11px]">
              {message.received_at}
            </div>
          </div>

          <div>
            <div className="text-slate-400 font-medium mb-1">Automated Decision:</div>
            <div className="text-slate-300 font-mono text-[11px]">
              {message.automated_decision} by <span className="text-indigo-400">{message.decided_by}</span>
            </div>
          </div>
        </div>

        {/* Aggregate Risk Score */}
        <div className="mt-5 pt-4 border-t border-white/5">
          <div className="text-xs font-semibold text-slate-400 mb-2">Max Threat Probability Over URLs:</div>
          <ScoreBar score={message.max_score} />
        </div>
      </div>

      {/* Message Body Preview */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
          Raw Message Body
        </h4>
        <div className="bg-[#070A12] border border-white/5 rounded-xl p-4 font-sans text-xs text-slate-300 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
          {message.body || '(Empty body)'}
        </div>
      </div>

      {/* Extracted & Defanged URLs Section */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Extracted & Defanged URLs ({urls.length})
            </h4>
          </div>
          <span className="text-[11px] text-amber-400/90 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
            Defanged (Non-Clickable)
          </span>
        </div>

        {urls.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500 bg-[#070A12] rounded-xl border border-white/5">
            No active hyperlinks detected in this email.
          </div>
        ) : (
          <div className="space-y-3">
            {urls.map((u, idx) => (
              <div
                key={idx}
                className="bg-[#070B16] border border-white/5 rounded-xl p-4 hover:border-white/10 transition"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1.5 flex-grow">
                    <div className="text-[11px] font-mono text-slate-400">
                      Domain: <span className="text-slate-200 font-semibold">{u.registered_domain}</span>
                    </div>
                    <div className="font-mono text-xs text-cyan-300 bg-slate-950/60 p-2 rounded-lg border border-cyan-500/20 break-all select-all">
                      {u.defanged_url}
                    </div>
                  </div>
                  <div className="sm:w-44 flex-shrink-0">
                    <ScoreBar score={u.score} />
                  </div>
                </div>

                {/* Top Features */}
                {u.top_features && u.top_features.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/5 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] text-slate-500 font-medium mr-1">Signals:</span>
                    {u.top_features.slice(0, 6).map((feat, fIdx) => (
                      <span
                        key={fIdx}
                        className="font-mono text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                      >
                        {feat.feature}: {typeof feat.value === 'number' ? feat.value.toFixed(2) : feat.value}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Previous Override History */}
      {overrides.length > 0 && (
        <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-4 h-4 text-slate-400" />
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Previous Overrides on this Email
            </h4>
          </div>
          <div className="space-y-2">
            {overrides.map((ov, oIdx) => (
              <div
                key={oIdx}
                className="bg-[#070A12] border border-white/5 rounded-xl p-3 text-xs"
              >
                <div className="flex justify-between items-center text-slate-400 font-mono text-[11px]">
                  <span className="text-indigo-400 font-semibold">{ov.reviewer_id}</span>
                  <span>{ov.timestamp}</span>
                </div>
                <div className="my-1.5 font-medium text-slate-200">
                  <span className="text-slate-400">{ov.previous_status}</span> &rarr;{' '}
                  <span className="text-cyan-400 font-bold">{ov.new_status}</span>
                </div>
                <div className="text-slate-400 italic bg-white/5 p-2 rounded border border-white/5">
                  "{ov.reason}"
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

