import { useState } from 'react';
import { Loader2, CheckCircle2, XCircle, AlertTriangle, Users } from 'lucide-react';
import { submitReviewDecision } from '../../services/reviewApi';
import type { DecisionStatus, DecisionPayload } from '../../types/claim';
import { clsx } from 'clsx';

interface HumanReviewPanelProps {
  reviewId: string;
  aiRecommendation: string;
  aiConfidence: number;
  onDecisionMade?: () => void;
}

const DECISIONS: { value: DecisionStatus; label: string; icon: React.ElementType; color: string; btnCls: string }[] = [
  { value: 'ACCEPT',          label: 'APPROVE',                  icon: CheckCircle2, color: 'text-green-600', btnCls: 'bg-green-600 hover:bg-green-700' },
  { value: 'REJECT',          label: 'DENY',                     icon: XCircle,      color: 'text-red-600',   btnCls: 'bg-red-600 hover:bg-red-700' },
  { value: 'MORE_INFORMATION',label: 'REQUEST MORE INFORMATION', icon: AlertTriangle,color: 'text-amber-600', btnCls: 'bg-amber-600 hover:bg-amber-700' },
  { value: 'HUMAN_REVIEW',    label: 'ESCALATE',                 icon: Users,        color: 'text-blue-600',  btnCls: 'bg-brand-600 hover:bg-brand-700' },
];

export function HumanReviewPanel({ reviewId, aiRecommendation, aiConfidence, onDecisionMade }: HumanReviewPanelProps) {
  const [selected, setSelected] = useState<DecisionStatus | null>(null);
  const [comments, setComments] = useState('');
  const [loading, setLoading]   = useState(false);
  const [done, setDone]         = useState(false);
  const [error, setError]       = useState('');

  const handleSubmit = async () => {
    if (!selected) { setError('Please select a decision.'); return; }
    setError('');
    setLoading(true);
    try {
      const payload: DecisionPayload = { decision: selected, reason_code: 'HUMAN_DECISION', comments };
      await submitReviewDecision(reviewId, payload);
      setDone(true);
      onDecisionMade?.();
    } catch {
      setError('Failed to submit. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center animate-fade-in-up">
        <CheckCircle2 className="w-6 h-6 text-green-600 mx-auto mb-1.5" />
        <p className="text-xs font-bold text-green-900">Decision submitted</p>
        <p className="text-[11px] text-green-700 mt-0.5">This review is now marked as completed.</p>
      </div>
    );
  }

  const aiPct = Math.round(aiConfidence * 100);

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm animate-fade-in-up">
      <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50/50">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">Human Review Decision</h3>
        <p className="text-[11px] text-slate-500 mt-0.5">Override or confirm the AI recommendation</p>
      </div>

      <div className="p-3.5 space-y-3.5">
        {/* AI Recommendation */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-[11px] font-bold text-blue-700 uppercase tracking-wide mb-1">AI Recommendation</p>
          <p className="text-xs font-bold text-blue-900">{aiRecommendation.replace(/_/g, ' ')}</p>
          <div className="mt-1.5">
            <div className="flex justify-between text-[11px] mb-0.5">
              <span className="text-blue-700">Confidence</span>
              <span className="font-bold text-blue-800">{aiPct}%</span>
            </div>
            <div className="h-1 bg-blue-200 rounded-full">
              <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${aiPct}%` }} />
            </div>
          </div>
        </div>

        {/* Connector: AI Recommendation -> Human Decision */}
        <div className="flex justify-center my-1">
          <div className="bg-slate-50 border border-slate-200 rounded-full p-1.5 shadow-sm text-slate-400 flex items-center justify-center animate-bounce">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="w-3.5 h-3.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </div>
        </div>

        {/* Decision buttons */}
        <div>
          <p className="text-[11px] font-bold text-slate-500 mb-1.5">Your Decision</p>
          <div className="grid grid-cols-2 gap-2">
            {DECISIONS.map(d => {
              const Icon = d.icon;
              const isSelected = selected === d.value;
              return (
                <button
                  key={d.value}
                  onClick={() => setSelected(d.value)}
                  className={clsx(
                    'flex items-center justify-center text-center gap-1.5 p-2 rounded-lg border-2 text-[9px] font-extrabold tracking-tight hover-card-trigger transition-all duration-150',
                    isSelected
                      ? `border-current ring-2 ring-offset-1 bg-white ${d.color} translate-y-[-1px]`
                      : 'border-slate-100 text-slate-500 bg-slate-50/30 hover:border-slate-300'
                  )}
                  style={{ transform: isSelected ? 'translateY(-1px)' : undefined }}
                >
                  <Icon className={clsx('w-3.5 h-3.5', isSelected ? d.color : 'text-slate-400')} />
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Comments */}
        <div>
          <label className="block text-[11px] font-bold text-slate-500 mb-1.5">Clinical Notes</label>
          <textarea
            value={comments}
            onChange={e => setComments(e.target.value)}
            rows={3.5}
            placeholder="Document your clinical reasoning here…"
            className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none resize-none transition-all"
          />
        </div>

        {error && (
          <p className="text-[11px] text-red-600 bg-red-50 border border-red-100 px-2.5 py-1.5 rounded-lg">{error}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || !selected}
          className="w-full inline-flex items-center justify-center gap-1.5 py-2 bg-brand-600 hover:bg-brand-700 border-2 border-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition-all"
        >
          {loading
            ? <><Loader2 className="w-3 h-3 animate-spin" /> Submitting…</>
            : 'Submit Decision'
          }
        </button>
      </div>
    </div>
  );
}
