import { useState, useEffect } from 'react';
import { Loader2, TrendingUp, RotateCcw, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { getResubmissionAnalysis } from '../../services/resubmissionApi';
import { resubmitClaim, getClaimsStore, saveClaimsStore } from '../../services/claimsApi';
import type { ResubmissionAnalysis as ResubAnalysis } from '../../types/resubmission';
import { clsx } from 'clsx';

interface ResubmissionAnalysisProps {
  claimId: string; onResubmitted?: () => void;
  portal?: 'hospital' | 'insurance';
}

export function ResubmissionAnalysis({ claimId, onResubmitted }: ResubmissionAnalysisProps) {
  const [data, setData]         = useState<ResubAnalysis | null>(null);
  const [loading, setLoading]   = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [error, setError]       = useState('');

  useEffect(() => {
    let ok = true;
    getResubmissionAnalysis(claimId)
      .then(d => { if (ok) { setData(d); setLoading(false); } })
      .catch(() => { if (ok) { setError('Failed to load analysis.'); setLoading(false); } });
    return () => { ok = false; };
  }, [claimId]);

  const handleResubmit = async () => {
    setSubmitting(true);
    try { await resubmitClaim(claimId); setSubmitted(true); onResubmitted?.(); }
    catch { setError('Resubmission failed. Please try again.'); }
    finally { setSubmitting(false); }
  };

  const handleEscalateToHuman = async () => {
    setSubmitting(true);
    try {
      const store = getClaimsStore();
      const idx = store.findIndex(c => c.claim_id === claimId);
      if (idx !== -1) {
        store[idx] = {
          ...store[idx],
          status: 'HUMAN_REVIEW',
          updated_at: new Date().toISOString(),
          timeline: [
            ...(store[idx].timeline ?? []),
            {
              timestamp: new Date().toISOString(),
              event: 'HUMAN_REVIEW',
              message: 'Claim escalated to Human Review by provider.'
            }
          ]
        };
        saveClaimsStore(store);
      }
      setSubmitted(true);
      onResubmitted?.();
    } catch {
      setError('Escalation failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="glass-panel rounded-2xl p-5 flex items-center gap-3 shadow-sm">
      <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
      <p className="text-[13px] text-slate-500 font-medium">Loading resubmission analysis…</p>
    </div>
  );
  if (!data) return null;

  const pct      = Math.round(data.resubmission_probability * 100);
  const isGreen  = data.recommendation === 'RESUBMIT';
  const isRed    = data.recommendation === "DON'T RESUBMIT";
  const barColor = isGreen ? 'from-emerald-400 to-emerald-600' : isRed ? 'from-red-400 to-red-600' : 'from-amber-400 to-amber-600';
  const pctColor = isGreen ? 'text-emerald-700' : isRed ? 'text-red-700' : 'text-amber-700';
  const badgeCls = isGreen ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : isRed ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200';

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-sm animate-fade-in-up">
      <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/60 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
          <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
        </div>
        <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">Resubmission Analysis</h3>
      </div>

      <div className="p-5 space-y-5">
        {/* Probability */}
        <div>
          <div className="flex justify-between items-end mb-2">
            <span className="text-[12px] font-bold text-slate-500">Success Probability</span>
            <span className={clsx('text-3xl font-black', pctColor)}>{pct}<span className="text-xl">%</span></span>
          </div>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden shadow-inner">
            <div className={clsx('h-full rounded-full bg-gradient-to-r transition-all duration-700', barColor)} style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Recommendation */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Recommendation</span>
          <span className={clsx('text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider border', badgeCls)}>
            {data.recommendation}
          </span>
          <span className="text-[11px] text-slate-400 font-medium">({Math.round(data.confidence * 100)}% confidence)</span>
        </div>

        {/* Policy Checks */}
        {data.policy_checks && (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries({
              'Rejection corrected':  data.policy_checks.rejection_reason_corrected,
              'Documents present':    data.policy_checks.required_documents_present,
              'Within window':        data.policy_checks.within_submission_window,
              'Attempts limit OK':    !data.policy_checks.max_attempts_exceeded,
            }).map(([label, ok]) => (
              <div key={label} className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-xl border text-[11px] font-semibold',
                ok ? 'bg-emerald-50 text-emerald-800 border-emerald-100' : 'bg-red-50 text-red-700 border-red-100'
              )}>
                {ok
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                  : <AlertTriangle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
                {label}
              </div>
            ))}
          </div>
        )}

        {/* Key Factors */}
        <div className="bg-slate-50/80 rounded-xl border border-slate-100 p-4">
          <p className="text-[10px] font-extrabold text-slate-500 uppercase tracking-widest mb-2.5">Key Factors</p>
          <ul className="space-y-2">
            {data.factors.map((f, i) => (
              <li key={i} className="flex items-start gap-2 text-[12px] text-slate-700 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Error */}
        {error && <p className="text-[12px] text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg font-semibold">{error}</p>}

        {/* Actions */}
        {submitted ? (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-[13px] font-extrabold">
            <CheckCircle2 className="w-4 h-4" /> Claim successfully resubmitted
          </div>
        ) : (
          <div className="flex gap-3 pt-2 border-t border-slate-100">
            {data.eligible && (
              <button
                onClick={handleResubmit}
                disabled={submitting}
                className="flex-1 inline-flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 active:scale-95 disabled:opacity-60 text-white text-[13px] font-extrabold rounded-xl shadow-md shadow-emerald-100 transition-all"
              >
                {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Resubmitting…</> : <><RotateCcw className="w-4 h-4" /> Resubmit Claim</>}
              </button>
            )}
            {!isRed && (
              <button
                onClick={handleEscalateToHuman}
                disabled={submitting}
                className="flex items-center justify-center gap-2 px-5 py-3 border border-slate-200 hover:border-amber-300 hover:bg-amber-50 hover:text-amber-800 text-slate-600 text-[12px] font-bold rounded-xl transition-all disabled:opacity-60"
              >
                <AlertTriangle className="w-4 h-4" /> Human Review
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
