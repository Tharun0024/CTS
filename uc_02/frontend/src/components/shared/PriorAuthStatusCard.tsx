import { ShieldCheck, ShieldAlert } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface PriorAuthStatusCardProps {
  claim: ClaimDetails;
  portal?: 'hospital' | 'insurance';
}

/**
 * Phase 4: displays the existing deterministic prior-auth pre-check result
 * (Phase 1) exactly as recorded on the authoritative claim record. Display
 * only — routing semantics are untouched: NOT REQUIRED still follows the
 * normal Agent 1 decision path and is never treated as auto-approved.
 */
export function PriorAuthStatusCard({ claim, portal = 'hospital' }: PriorAuthStatusCardProps) {
  const precheck = claim.prior_auth_precheck;
  if (!precheck) return null;

  const required = !!precheck.requires_prior_auth;
  const isHospital = portal === 'hospital';
  const accentText = isHospital ? 'text-emerald-700' : 'text-indigo-700';

  return (
    <div className={clsx(
      'rounded-lg border p-3.5 shadow-sm animate-fade-in-up',
      required ? 'bg-sky-50 border-sky-200' : 'bg-slate-50 border-slate-200'
    )}>
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
          {required
            ? <ShieldAlert className="w-3.5 h-3.5 text-sky-600" />
            : <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />}
          Prior Authorization: {required ? 'REQUIRED' : 'NOT REQUIRED'}
        </h3>
        <span className={clsx(
          'text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded border',
          required ? 'bg-sky-100 text-sky-700 border-sky-200' : 'bg-slate-100 text-slate-600 border-slate-200'
        )}>
          Deterministic pre-check
        </span>
      </div>

      <dl className="space-y-1.5 text-xs">
        {precheck.matched_rule && (
          <div className="flex justify-between items-baseline gap-3">
            <dt className="text-[10px] text-slate-400 uppercase tracking-wider flex-shrink-0">Matched Rule</dt>
            <dd className="font-mono font-bold text-slate-700 text-right">{precheck.matched_rule}</dd>
          </div>
        )}
        {precheck.policy_reference && (
          <div className="flex justify-between items-baseline gap-3">
            <dt className="text-[10px] text-slate-400 uppercase tracking-wider flex-shrink-0">Policy Reference</dt>
            <dd className="font-mono font-bold text-slate-700 text-right">{precheck.policy_reference}</dd>
          </div>
        )}
        {precheck.reason && (
          <div>
            <dt className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Reason</dt>
            <dd className="font-medium text-slate-700 leading-relaxed">{precheck.reason}</dd>
          </div>
        )}
      </dl>

      <p className={clsx('text-[10px] font-semibold mt-2', accentText)}>
        {required
          ? 'Prior authorization applies — claim follows the standard Agent 1 evaluation workflow.'
          : 'No prior authorization required by rule — claim still follows the standard Agent 1 decision path (not auto-approved).'}
      </p>
    </div>
  );
}
