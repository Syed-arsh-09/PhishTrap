import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import ScoreBar from './ScoreBar';
import { Play, Sparkles, AlertCircle, Layers } from 'lucide-react';
import { ingestEmail } from '../api';

const presets = [
  {
    name: 'Credential Harvester (High Risk)',
    subject: 'URGENT: Your account access has been suspended',
    sender: 'security@paypal-verification.pages.dev',
    body: 'Your account has been locked due to unauthorized logins. Please verify your credentials immediately to avoid termination: http://paypal-verification-update.secure-login-account.pages.dev/banking/signin.php?token=9281'
  },
  {
    name: 'Ambiguous Vendor Invoice (Review Band)',
    subject: 'Action Required: Statement from Vendor #8841',
    sender: 'billing@accounting-docs.co',
    body: 'Please review the updated service invoice attached here: https://portal.billing-docs.co/invoices/client/9821/review'
  },
  {
    name: 'Legitimate Internal Memo (Low Risk)',
    subject: 'Engineering Architecture Sync & Style Guide',
    sender: 'alex@internal-tools.org',
    body: 'Team, please review the latest updates on the documentation wiki before our planning call: https://wikipedia.org/wiki/Phishing'
  }
];

export default function SandboxTab({ onEmailIngested }) {
  const [subject, setSubject] = useState(presets[0].subject);
  const [sender, setSender] = useState(presets[0].sender);
  const [body, setBody] = useState(presets[0].body);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const applyPreset = (p) => {
    setSubject(p.subject);
    setSender(p.sender);
    setBody(p.body);
    setResult(null);
    setErrorMsg(null);
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!subject || !sender || !body) {
      setErrorMsg('All fields (Subject, Sender, Body) are required.');
      return;
    }

    try {
      setIsProcessing(true);
      setErrorMsg(null);
      const res = await ingestEmail({
        subject: subject.trim(),
        sender: sender.trim(),
        body: body.trim()
      });
      setResult(res);
      onEmailIngested?.();
    } catch (err) {
      setErrorMsg(err.message || 'Ingestion failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Presets */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Interactive Multi-Agent Stream Sandbox</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Dispatch any email through the 6-agent deterministic pipeline in real-time. Watch the URL extractor, feature generator, ML scorer, and triage policies execute.
          </p>
        </div>

        <div>
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Select Test Preset
          </div>
          <div className="flex flex-wrap gap-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => applyPreset(p)}
                className="text-xs px-3 py-1.5 rounded-xl border border-white/10 bg-[#070A12] hover:bg-[#121B30] hover:border-indigo-500/40 text-slate-300 font-medium transition"
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Input Form vs Output Result */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Form (6 cols) */}
        <form onSubmit={handleIngest} className="lg:col-span-6 bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
          <div className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Test Email Payload Configuration
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Sender Address</label>
            <input
              type="text"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Email Body (With URLs)</label>
            <textarea
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none font-sans"
            />
          </div>

          <button
            type="submit"
            disabled={isProcessing}
            className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
          >
            <Play className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
            <span>{isProcessing ? 'Executing 6-Agent Pipeline...' : 'Run Pipeline Ingestion'}</span>
          </button>
        </form>

        {/* Right Output Dossier (6 cols) */}
        <div className="lg:col-span-6">
          {!result ? (
            <div className="h-full min-h-[360px] flex flex-col items-center justify-center p-8 text-center text-slate-500 bg-[#0D1424]/40 border border-white/5 rounded-2xl">
              <Layers className="w-10 h-10 stroke-[1.25] text-slate-600 mb-2" />
              <div className="text-xs font-semibold text-slate-300">Awaiting Pipeline Execution</div>
              <p className="text-[11px] text-slate-500 max-w-xs mt-1">
                Click "Run Pipeline Ingestion" to evaluate the test message and view agent-by-agent outputs.
              </p>
            </div>
          ) : (
            <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div>
                  <span className="font-mono text-xs font-bold text-indigo-400">{result.id}</span>
                  <div className="text-[11px] text-slate-400 font-mono">Assigned UUID</div>
                </div>
                <StatusBadge status={result.automated_decision} />
              </div>

              <div>
                <div className="text-xs text-slate-400 font-medium mb-1">Max Risk Score:</div>
                <ScoreBar score={result.max_score} />
              </div>

              {/* Step-by-Step Agent Log */}
              <div className="bg-[#070A12] border border-white/5 rounded-xl p-3.5 space-y-2 font-mono text-[11px]">
                <div className="text-slate-400 font-bold uppercase tracking-wider font-sans mb-1 text-[10px]">
                  Agent Pipeline Execution Sequence
                </div>
                <div className="text-slate-300">
                  1. <strong className="text-cyan-400">ParserAgent</strong>: {result.urls?.length || 0} URL(s) extracted
                </div>
                <div className="text-slate-300">
                  2. <strong className="text-indigo-400">FeatureAgent</strong>: Extracted 26 lexical signals
                </div>
                <div className="text-slate-300">
                  3. <strong className="text-purple-400">ClassifierAgent</strong>: Max score {result.max_score?.toFixed(4)}
                </div>
                <div className="text-slate-300">
                  4. <strong className="text-amber-400">TriageAgent</strong>: Decision &rarr; {result.automated_decision}
                </div>
                <div className="text-slate-300">
                  5. <strong className="text-emerald-400">ActionAgent</strong>: Persisted to SQLite WAL
                </div>
                <div className="text-slate-300">
                  6. <strong className="text-blue-400">AuditAgent</strong>: Audit trail logged
                </div>
              </div>

              {/* Extracted URLs List */}
              {result.urls && result.urls.length > 0 && (
                <div>
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Defanged URL Payloads
                  </div>
                  <div className="space-y-2">
                    {result.urls.map((u, idx) => (
                      <div key={idx} className="bg-[#070A12] p-2.5 rounded-xl border border-white/5 text-xs font-mono">
                        <div className="text-cyan-300 break-all">{u.defanged_url}</div>
                        <div className="text-[11px] text-slate-500 mt-1">Score: {u.score?.toFixed(4)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

      </div>

    </div>
  );
}

