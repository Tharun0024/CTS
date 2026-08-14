import React from 'react';
import { cn } from './Button';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  options: { label: string; value: string }[];
  placeholder?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, hint, options, placeholder, id, ...props }, ref) => {
    const selectId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5"
          >
            {label}
            {props.required && <span className="text-rose-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            className={cn(
              // Base layout
              'flex w-full appearance-none rounded-xl border border-slate-200 bg-white',
              'px-3 py-2 pr-9 text-[13px] font-medium text-slate-900',
              // Focus
              'focus:outline-none focus:border-hospital-500 focus:ring-3 focus:ring-hospital-500/10',
              // Transitions
              'transition-all duration-150',
              // Disabled
              'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-slate-50',
              // Error
              error && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/10',
              className
            )}
            {...props}
          >
            {placeholder && (
              <option value="" disabled hidden>
                {placeholder}
              </option>
            )}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2.5">
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" strokeWidth={2.5} />
          </div>
        </div>
        {error && (
          <p className="mt-1.5 text-[11px] font-medium text-rose-600 flex items-center gap-1">
            <span>⚠</span> {error}
          </p>
        )}
        {hint && !error && (
          <p className="mt-1.5 text-[11px] text-slate-400 font-medium">{hint}</p>
        )}
      </div>
    );
  }
);
Select.displayName = 'Select';
