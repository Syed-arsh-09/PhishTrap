import React from 'react';

export default function ScoreBar({ score, showLabel = true }) {
  const safeScore = Math.max(0, Math.min(1, Number(score) || 0));
  const percent = Math.round(safeScore * 100);

  let barGradient = 'from-emerald-500 to-cyan-500';
  let textClass = 'text-emerald-400';
  let category = 'BENIGN';

  if (safeScore >= 0.85) {
    barGradient = 'from-amber-500 to-red-500';
    textClass = 'text-red-400';
    category = 'HIGH RISK';
  } else if (safeScore >= 0.05) {
    barGradient = 'from-blue-500 to-amber-500';
    textClass = 'text-amber-400';
    category = 'AMBIGUOUS';
  }

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between text-xs mb-1.5 font-mono">
          <span className="text-slate-400">
            Score: <strong className={`font-semibold text-sm ${textClass}`}>{safeScore.toFixed(4)}</strong>
          </span>
          <span className={`text-[11px] font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-800/80 ${textClass}`}>
            {category}
          </span>
        </div>
      )}
      <div className="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden border border-white/5">
        <div
          className={`h-full bg-gradient-to-r ${barGradient} transition-all duration-300 rounded-full`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

