import React from 'react';
import { cn } from './Button';

const variantClasses = {
  default: 'bg-slate-100 text-slate-700 border-slate-200/80 ring-slate-900/5',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200/80 ring-emerald-500/10',
  warning: 'bg-amber-50 text-amber-700 border-amber-200/80 ring-amber-500/10',
  error:   'bg-rose-50 text-rose-700 border-rose-200/80 ring-rose-500/10',
  info:    'bg-blue-50 text-blue-700 border-blue-200/80 ring-blue-500/10',
};

export function Badge({
  className,
  variant = 'default',
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: keyof typeof variantClasses;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide transition-colors ring-1 ring-inset leading-none whitespace-nowrap',
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
