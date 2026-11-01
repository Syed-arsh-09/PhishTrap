import React, { useState, useEffect } from 'react';
import { X, ShieldAlert, CheckCircle, Tag, AlertTriangle } from 'lucide-react';
import { submitOverride } from '../api';

export default function OverrideModal({ isOpen, onClose, message, analyst, onSuccess }) {
  const [action, setAction] = useState('RELEASE');
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setReason('');
      setErrorMsg(null);
      setAction('RELEASE');
    }
  }, [isOpen]);

  if (!isOpen || !message) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!reason || reason.trim().length < 5) {
      setErrorMsg('A valid justification of at least 5 characters is mandatory for audit compliance.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await submitOverride(message.id, {
        reviewerId: analyst || 'analyst_unknown',
        action: action,
        reason: reason.trim()
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Override failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const actionOptions = [
    {
      id: 'RELEASE',
      label: 'Release to Inbox',
      sub: 'False positive mitigation',
      icon: CheckCircle,
      activeClass: 'border-emerald-500 bg-emerald-500/10 text-emerald-300'
    },
    {
      id: 'CONFIRM_PHISH',
      label: 'Confirm Phish & Block',
      sub: 'Verified true threat',
      icon: ShieldAlert,
      activeClass: 'border-red-500 bg-red-500/10 text-red-300'
    },
    {
      id: 'RELABEL',
      label: 'Relabel for Retraining',
      sub: 'Active learning dataset feedback',
      icon: Tag,
      activeClass: 'border-purple-500 bg-purple-500/10 text-purple-300'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-[#0D1424] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#0A0F1A]">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Security Analyst Override</span>
            </h3>
            <div className="text-xs text-slate-400 font-mono mt-0.5">
              Message Target: <span className="text-indigo-400 font-semibold">{message.id}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          
          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-2 font-medium">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Action Selector */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Select Decision Override Action
            </label>
            <div className="grid grid-cols-1 gap-2.5">
              {actionOptions.map((opt) => {
                const Icon = opt.icon;
                const isSelected = action === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setAction(opt.id)}
                    className={`flex items-center gap-3 p-3 rounded-xl border text-left transition ${
                      isSelected
                        ? opt.activeClass
                        : 'border-white/5 bg-[#070A12] text-slate-400 hover:border-white/10'
                    }`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <div>
                      <div className="text-xs font-semibold">{opt.label}</div>
                      <div className="text-[11px] text-slate-500">{opt.sub}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Reviewer Handle & Rationale */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Audited Justification (Mandatory)
              </label>
              <span className={`text-[10px] font-mono ${reason.trim().length >= 5 ? 'text-emerald-400' : 'text-slate-500'}`}>
                {reason.trim().length} / 5 min chars
              </span>
            </div>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Verified sender domain SPF/DKIM records pass; out-of-band phone call confirmed legitimate invoice attachment."
              className="w-full bg-[#070A12] border border-white/10 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition resize-none font-sans"
            />
          </div>

          <div className="text-[11px] text-slate-500 bg-white/5 p-2.5 rounded-lg border border-white/5 flex items-center justify-between font-mono">
            <span>Signing Analyst: <strong>{analyst || 'analyst_unknown'}</strong></span>
            <span>Policy: FAIL-CLOSED</span>
          </div>

          {/* Modal Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-white/10 text-xs font-semibold text-slate-400 hover:text-white hover:bg-white/5 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition flex items-center gap-2"
            >
              {isSubmitting ? 'Committing...' : 'Commit to Audit Log'}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}

