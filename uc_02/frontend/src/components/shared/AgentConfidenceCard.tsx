import { Shield } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface AgentConfidenceCardProps {
  claim: ClaimDetails;
}

/**
 * Phase 4: consistent display of the persisted Agent 1 confidence metrics
 * (confidence_score / confidence_level / confidence_factors) on both
 * dashboards. Read-only view of the authoritative decision record —
 * informational only, never changes the decision.
 */
export function AgentConfidenceCard({ claim }: AgentConfidenceCardProps) {
  const decision = claim.decision;
  if (!decision || decision.confidence_score == null) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3.5 shadow-sm animate-fade-in-up space-y-2">
      <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-slate-500" />
          Agent 1 Decision Confidence
        </span>
        <span className="text-[9px] font-semibold text-slate-400 normal-case tracking-normal">
          Informational only
        </span>
      </h3>
      <div className="flex items-center gap-3">
        <span className="text-xl font-black text-slate-800">
          {Math.round(decision.confidence_score * 100)}%
        </span>
        <span className={clsx(
          'text-[9px] font-extrabold px-2.5 py-0.5 rounded border uppercase tracking-wider',
          decision.confidence_level === 'HIGH'
            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
            : decision.confidence_level === 'MEDIUM'
              ? 'bg-amber-50 text-amber-700 border-amber-200'
              : 'bg-rose-50 text-rose-700 border-rose-200'
        )}>
          {decision.confidence_level || 'N/A'}
        </span>
        <span className="font-mono text-[10px] text-slate-500">
          score {decision.confidence_score.toFixed(2)}
        </span>
      </div>
      {(decision.confidence_factors ?? []).length > 0 && (
        <ul className="text-xs text-slate-600 font-semibold list-disc pl-4 space-y-0.5 leading-relaxed">
          {(decision.confidence_factors ?? []).map((factor, idx) => (
            <li key={idx}>{factor}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
