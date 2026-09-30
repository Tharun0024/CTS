import type { Priority } from '../../types/authorization';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function PriorityBadge({ priority, className }: { priority: Priority, className?: string }) {
  let bgColor = 'bg-slate-100';
  let textColor = 'text-slate-700';

  if (priority === 'HIGH') {
    bgColor = 'bg-red-100';
    textColor = 'text-red-700';
  } else if (priority === 'MEDIUM') {
    bgColor = 'bg-amber-100';
    textColor = 'text-amber-700';
  } else if (priority === 'LOW') {
    bgColor = 'bg-slate-100';
    textColor = 'text-slate-700';
  }

  return (
    <span className={twMerge(clsx('px-2.5 py-1 rounded-full text-xs font-medium border border-black/5', bgColor, textColor, className))}>
      {priority}
    </span>
  );
}
