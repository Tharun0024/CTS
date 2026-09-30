import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Loader2, CheckCircle2 } from 'lucide-react';
import { postProviderDecision } from '../../services/claimsApi';
import type { ClaimDetails } from '../../types/claim';

interface ProviderDecisionPanelProps {
  claim: ClaimDetails;
  onDecided?: () => void;
}

// Provider ACCEPT/DECLINE consent on Agent 2 recovered evidence. Shown only
// when Agent 2 actually recovered releasable evidence for this claim.
export function ProviderDecisionPanel({ claim, onDecided }: ProviderDecisionPanelProps) {
  const [submitting, setSubmitting] = useState<'ACCEPT' | 'DECLINE' | null>(null);
  const [error, setError] = useState('');

  const recoveredIds = claim.recovery_result?.recovered_evidence_ids ?? [];
  if (recoveredIds.length === 0) return null;

  const latest = (claim.provider_decisions ?? [])[0] ?? null;

  const handle = async (decision: 'ACCEPT' | 'DECLINE') => {
    setSubmitting(decision);
    setError('');
    try {
      await postProviderDecision(claim.claim_id, decision, undefined, recoveredIds);
      onDecided?.();
    } catch {
      setError('Failed to record provider decision.');
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-sm animate-fade-in-up">
      <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/60 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        </div>
        <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">
          Provider Evidence Decision
        </h3>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-[12px] text-slate-600 font-medium">
          Agent 2 recovered <span className="font-extrabold text-slate-900">{recoveredIds.length}</span> evidence
          item(s) from the patient record. Provider consent is required before release to the payer.
        </p>

        {latest ? (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-[13px] font-extrabold">
            <CheckCircle2 className="w-4 h-4" />
            Provider decision recorded: {latest.decision}
            {latest.decided_at ? ` (${new Date(latest.decided_at).toLocaleString()})` : ''}
          </div>
        ) : (
          <div className="flex gap-3">
            <button
              onClick={() => handle('ACCEPT')}
              disabled={submitting !== null}
              className="flex-1 inline-flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 active:scale-95 disabled:opacity-60 text-white text-[13px] font-extrabold rounded-xl shadow-md shadow-emerald-100 transition-all"
            >
              {submitting === 'ACCEPT'
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Recording…</>
                : <><ThumbsUp className="w-4 h-4" /> Accept &amp; Release</>}
            </button>
            <button
              onClick={() => handle('DECLINE')}
              disabled={submitting !== null}
              className="flex-1 inline-flex items-center justify-center gap-2 py-3 border border-red-200 hover:bg-red-50 hover:text-red-700 active:scale-95 disabled:opacity-60 text-red-600 text-[13px] font-extrabold rounded-xl transition-all"
            >
              {submitting === 'DECLINE'
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Recording…</>
                : <><ThumbsDown className="w-4 h-4" /> Decline</>}
            </button>
          </div>
        )}

        {error && (
          <p className="text-[12px] text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg font-semibold">{error}</p>
        )}
      </div>
    </div>
  );
}
