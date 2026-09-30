import React from 'react';
import { cn } from './Button';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, icon, iconRight, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5"
          >
            {label}
            {props.required && <span className="text-rose-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              // Base
              'flex w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-[13px] font-medium text-slate-900',
              'placeholder:text-slate-400 placeholder:font-normal',
              // Transition & focus
              'transition-all duration-150',
              'focus:outline-none focus:border-hospital-500 focus:ring-3 focus:ring-hospital-500/10',
              // Disabled
              'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-slate-50',
              // Icon padding
              icon && 'pl-9',
              iconRight && 'pr-9',
              // Error
              error && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/10',
              className
            )}
            {...props}
          />
          {iconRight && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400">
              {iconRight}
            </div>
          )}
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
Input.displayName = 'Input';
