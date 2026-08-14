import { useState } from 'react';
import { Loader2, CheckCircle2, XCircle, AlertTriangle, Users, Info } from 'lucide-react';
import { submitDecision } from '../../services/insuranceApi';
import type { DecisionStatus, DecisionPayload } from '../../types/claim';
import { clsx } from 'clsx';

interface DecisionPanelProps {
  claimId: string;
  onDecisionMade?: (decision: DecisionStatus) => void;
}

type Step = 'choose' | 'detail' | 'done';

const DECISIONS: { value: DecisionStatus; label: string; subLabel: string; icon: React.ElementType; color: string; bg: string; border: string }[] = [
  { value: 'ACCEPT',          label: 'Accept',       subLabel: 'Approve Claim',       icon: CheckCircle2, color: 'text-green-600',  bg: 'hover:bg-green-50/40',  border: 'border-green-200 data-[selected=true]:bg-green-50/50 data-[selected=true]:border-green-500' },
  { value: 'REJECT',          label: 'Reject',       subLabel: 'Deny Claim',          icon: XCircle,      color: 'text-red-600',    bg: 'hover:bg-red-50/40',    border: 'border-red-200 data-[selected=true]:bg-red-50/50 data-[selected=true]:border-red-500' },
  { value: 'MORE_INFORMATION',label: 'More Info',    subLabel: 'Request Information', icon: AlertTriangle,color: 'text-amber-600',  bg: 'hover:bg-amber-50/40',  border: 'border-amber-200 data-[selected=true]:bg-amber-50/50 data-[selected=true]:border-amber-500' },
  { value: 'HUMAN_REVIEW',    label: 'Human Review', subLabel: 'Send for Review',     icon: Users,        color: 'text-blue-600',   bg: 'hover:bg-blue-50/40',   border: 'border-blue-200 data-[selected=true]:bg-blue-50/50 data-[selected=true]:border-blue-500' },
];

const REASON_CODES: Record<string, string[]> = {
  REJECT:          ['INSUFFICIENT_DOCUMENTATION', 'CRITERIA_NOT_MET', 'NOT_COVERED', 'DUPLICATE_CLAIM', 'EXPERIMENTAL_PROCEDURE'],
  MORE_INFORMATION:['MISSING_DOCUMENTS', 'INCOMPLETE_CLINICAL_INFO', 'ADDITIONAL_EVALUATION_NEEDED'],
  HUMAN_REVIEW:    ['CLINICAL_COMPLEXITY', 'CONFLICTING_EVIDENCE', 'HIGH_COST_PROCEDURE', 'APPEALS_PROCESS'],
};

export function DecisionPanel({ claimId, onDecisionMade }: DecisionPanelProps) {
  const [step, setStep]         = useState<Step>('choose');
  const [selected, setSelected] = useState<DecisionStatus | null>(null);
  const [reasonCode, setReasonCode] = useState('');
  const [comments, setComments]     = useState('');
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [result, setResult]         = useState<DecisionStatus | null>(null);

  const handleChoose = (d: DecisionStatus) => {
    setSelected(d);
    setStep('detail');
  };

  const handleSubmit = async () => {
    if (!selected) return;
    if (selected !== 'ACCEPT' && !reasonCode) {
      setError('Please select a reason code.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const payload: DecisionPayload = {
        decision: selected,
        reason_code: reasonCode || 'CRITERIA_MET',
        comments,
      };
      await submitDecision(claimId, payload);
      setResult(selected);
      setStep('done');
      onDecisionMade?.(selected);
    } catch {
      setError('Failed to submit decision. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const selectedDef = DECISIONS.find(d => d.value === selected);

  if (step === 'done' && result) {
    const def = DECISIONS.find(d => d.value === result);
    const Icon = def?.icon ?? CheckCircle2;
    return (
      <div className={clsx('rounded-lg border-2 p-4 text-center animate-fade-in-up', def?.border ?? '')}>
        <Icon className={clsx('w-8 h-8 mx-auto mb-2', def?.color)} />
        <p className="text-xs font-bold text-slate-900">Decision Submitted</p>
        <p className={clsx('text-xs font-semibold mt-0.5', def?.color)}>{def?.label}</p>
        {comments && <p className="text-[11px] text-slate-500 mt-1.5 italic">"{comments}"</p>}
        <button
          onClick={() => { setStep('choose'); setSelected(null); setReasonCode(''); setComments(''); setResult(null); }}
          className="mt-3 text-[11px] text-brand-600 hover:underline"
        >
          Submit another decision
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm animate-fade-in-up">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/55 flex items-center gap-1.5">
        <Users className="w-3.5 h-3.5 text-brand-600" />
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">Decision Panel</h3>
      </div>

      <div className="p-3.5 space-y-3.5">
        {/* Step 1: Choose 2x2 Grid */}
        <div className="grid grid-cols-2 gap-2.5">
          {DECISIONS.map(d => {
            const Icon = d.icon;
            const isSelected = selected === d.value;
            return (
              <button
                key={d.value}
                onClick={() => handleChoose(d.value)}
                data-selected={isSelected}
                className={clsx(
                  'flex flex-col items-center text-center gap-1 p-2.5 rounded-lg border-2 text-xs font-bold hover-card-trigger transition-all duration-150',
                  d.border,
                  d.bg,
                  isSelected ? 'shadow-sm ring-2 ring-offset-1 translate-y-[-1px]' : 'border-slate-100 bg-slate-50/30'
                )}
                style={{ transform: isSelected ? 'translateY(-1px)' : undefined }}
              >
                <Icon className={clsx('w-5 h-5', d.color)} />
                <span className="text-slate-800 text-[11px] font-bold block mt-0.5 leading-none">{d.label}</span>
                <span className="text-[9px] text-slate-400 font-medium block mt-0.5 leading-none">{d.subLabel}</span>
              </button>
            );
          })}
        </div>

        {/* Small Disclaimer */}
        <div className="flex items-start gap-1.5 p-2 bg-slate-50 border border-slate-100 rounded text-[10px] text-slate-500">
          <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
          <p className="leading-normal font-medium">Please review all policy criteria and documents before taking action.</p>
        </div>

        {/* Step 2: Reason & comments */}
        {step === 'detail' && selected && (
          <div className="space-y-3 border-t border-slate-100 pt-3 animate-fade-in-up">
            {selected !== 'ACCEPT' && REASON_CODES[selected] && (
              <div>
                <label className="block text-[11px] font-bold text-slate-500 mb-1">
                  Reason Code <span className="text-red-500">*</span>
                </label>
                <select
                  value={reasonCode}
                  onChange={e => setReasonCode(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition-all"
                >
                  <option value="">Select reason…</option>
                  {REASON_CODES[selected]!.map(r => (
                    <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-bold text-slate-500 mb-1">Comments (optional)</label>
              <textarea
                value={comments}
                onChange={e => setComments(e.target.value)}
                rows={2.5}
                placeholder={selected === 'ACCEPT'
                  ? 'Add any notes for the record…'
                  : 'Explain the decision in detail…'}
                className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none resize-none transition-all"
              />
            </div>

            {error && (
              <p className="text-[11px] text-red-600 bg-red-50 border border-red-100 px-2.5 py-1.5 rounded-lg">{error}</p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => { setStep('choose'); setSelected(null); setReasonCode(''); setComments(''); }}
                className="flex-1 py-1.5 text-xs font-bold text-slate-500 border-2 border-slate-350 hover:border-slate-400 bg-white hover:bg-slate-50 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className={clsx(
                  'flex-1 py-1.5 text-xs font-bold text-white rounded-lg transition-all inline-flex items-center justify-center gap-1 disabled:opacity-60 border-2',
                  selectedDef?.value === 'ACCEPT' ? 'bg-green-600 hover:bg-green-700 border-green-700' :
                  selectedDef?.value === 'REJECT' ? 'bg-red-600 hover:bg-red-700 border-red-700' :
                  selectedDef?.value === 'MORE_INFORMATION' ? 'bg-amber-600 hover:bg-amber-700 border-amber-700' :
                  'bg-brand-600 hover:bg-brand-700 border-brand-700'
                )}
              >
                {loading ? <><Loader2 className="w-3 h-3 animate-spin" /> Submitting…</> : `Confirm`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
