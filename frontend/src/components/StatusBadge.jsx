import React from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, MailCheck, ShieldX, Tag } from 'lucide-react';

const statusConfig = {
  QUARANTINE: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    label: 'QUARANTINE',
    icon: ShieldAlert
  },
  HUMAN_REVIEW: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    label: 'HUMAN REVIEW',
    icon: AlertTriangle
  },
  ALLOW: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    label: 'ALLOW',
    icon: CheckCircle2
  },
  RELEASED: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    label: 'RELEASED',
    icon: MailCheck
  },
  CONFIRMED_PHISH: {
    bg: 'bg-red-600/20',
    border: 'border-red-600/50',
    text: 'text-red-300 font-bold',
    label: 'CONFIRMED PHISH',
    icon: ShieldX
  },
  RELABELED: {
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    text: 'text-purple-400',
    label: 'RELABELED',
    icon: Tag
  }
};

export default function StatusBadge({ status, size = 'sm' }) {
  const norm = (status || '').toUpperCase().trim();
  const cfg = statusConfig[norm] || {
    bg: 'bg-slate-700/30',
    border: 'border-slate-600/30',
    text: 'text-slate-300',
    label: norm || 'UNKNOWN',
    icon: CheckCircle2
  };

  const Icon = cfg.icon;
  const sizeClasses = size === 'xs' 
    ? 'text-[10px] px-2 py-0.5 gap-1' 
    : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span className={`inline-flex items-center font-semibold rounded-md border tracking-wider ${cfg.bg} ${cfg.border} ${cfg.text} ${sizeClasses}`}>
      <Icon className={size === 'xs' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span>{cfg.label}</span>
    </span>
  );
}

