import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import ScoreBar from './ScoreBar';
import MessageDossier from './MessageDossier';
import OverrideModal from './OverrideModal';
import { Search, Inbox, ShieldCheck, Filter } from 'lucide-react';

export default function ReviewQueueTab({
  queue = [],
  selectedMessage,
  onSelectMessage,
  analyst,
  onRefresh
}) {
  const [search, setSearch] = useState('');
  const [isOverrideOpen, setIsOverrideOpen] = useState(false);

  const filteredQueue = queue.filter((item) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      item.id?.toLowerCase().includes(s) ||
      item.sender?.toLowerCase().includes(s) ||
      item.subject?.toLowerCase().includes(s)
    );
  });

  return (
    <div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Triage Queue List (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Search & Counter Bar */}
          <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-4 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Inbox className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Analyst Queue ({queue.length})
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/5">
                Band: [0.05, 0.85)
              </span>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by sender, subject, or message ID..."
                className="w-full bg-[#070A12] border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>
          </div>

          {/* List Items */}
          <div className="space-y-2.5 max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
            {filteredQueue.length === 0 ? (
              <div className="p-8 text-center bg-[#0D1424]/40 border border-white/5 rounded-2xl text-slate-500 text-xs">
                <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-emerald-500/60" />
                No pending messages match filter.
              </div>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = selectedMessage?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => onSelectMessage(item)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden ${
                      isSelected
                        ? 'bg-[#141E34] border-indigo-500/60 shadow-lg shadow-indigo-500/10'
                        : 'bg-[#0D1424] border-white/5 hover:border-white/15 hover:bg-[#10182C]'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500" />
                    )}

                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-mono text-xs font-bold text-slate-300">
                        {item.id}
                      </span>
                      <StatusBadge status={item.current_status} size="xs" />
                    </div>

                    <div className="font-semibold text-xs text-slate-100 line-clamp-1 mb-1">
                      {item.subject || '(No Subject)'}
                    </div>

                    <div className="text-[11px] text-slate-400 font-mono line-clamp-1 mb-2.5">
                      {item.sender}
                    </div>

                    <ScoreBar score={item.max_score} showLabel={true} />
                  </div>
                );
              })
            )}
          </div>

        </div>

        {/* Right Column: Detailed Message Dossier & Override Console (7 cols) */}
        <div className="lg:col-span-7">
          <MessageDossier
            message={selectedMessage}
            onOpenOverride={() => setIsOverrideOpen(true)}
          />
        </div>

      </div>

      {/* Override Modal */}
      <OverrideModal
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        message={selectedMessage}
        analyst={analyst}
        onSuccess={onRefresh}
      />
    </div>
  );
}

