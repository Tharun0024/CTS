import { clsx } from 'clsx';
import type { ClaimStatus } from '../../types/claim';

interface StatusBadgeProps {
  status: ClaimStatus;
  className?: string;
}

const STATUS_CONFIG: Record<string, { label: string; cls: string; dot: string }> = {
  ACCEPTED:          { label: 'Accepted',          cls: 'bg-emerald-50 text-emerald-700 border-emerald-200',   dot: 'bg-emerald-500' },
  REJECTED:          { label: 'Rejected',          cls: 'bg-red-50 text-red-700 border-red-200',               dot: 'bg-red-500' },
  MORE_INFO:         { label: 'More Info',         cls: 'bg-amber-50 text-amber-700 border-amber-200',         dot: 'bg-amber-500' },
  HUMAN_REVIEW:      { label: 'Human Review',      cls: 'bg-blue-50 text-blue-700 border-blue-200',            dot: 'bg-blue-500' },
  PROCESSING:        { label: 'Processing',        cls: 'bg-violet-50 text-violet-700 border-violet-200',      dot: 'bg-violet-500 animate-pulse' },
  UNDER_REVIEW:      { label: 'Under Review',      cls: 'bg-violet-50 text-violet-700 border-violet-200',      dot: 'bg-violet-500 animate-pulse' },
  RESUBMISSION_CHECK:{ label: 'Resubmission',      cls: 'bg-indigo-50 text-indigo-700 border-indigo-200',      dot: 'bg-indigo-500 animate-pulse' },
  SUBMITTED:         { label: 'Submitted',         cls: 'bg-slate-50 text-slate-600 border-slate-200',         dot: 'bg-slate-400' },
  SUBMITTED_AGAIN:   { label: 'Resubmitted',       cls: 'bg-sky-50 text-sky-700 border-sky-200',               dot: 'bg-sky-500' },
  DRAFT:             { label: 'Draft',             cls: 'bg-slate-50 text-slate-500 border-slate-200',         dot: 'bg-slate-300' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? { label: status.replace(/_/g, ' '), cls: 'bg-slate-50 text-slate-600 border-slate-200', dot: 'bg-slate-400' };
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider border', cfg.cls, className)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', cfg.dot)} />
      {cfg.label}
    </span>
  );
}
