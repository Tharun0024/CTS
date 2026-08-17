import { useState } from 'react';
import { Loader2, CheckCircle2, ShieldAlert } from 'lucide-react';
import { resolveHumanReview } from '../../services/claimsApi';
import type { ClaimDetails } from '../../types/claim';

interface HospitalHumanResolutionPanelProps {
  claim: ClaimDetails;
  onResolved?: () => void;
}

export function HospitalHumanResolutionPanel({ claim, onResolved }: HospitalHumanResolutionPanelProps) {
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleResolve = async () => {
    setLoading(true);
    setError('');
    try {
      await resolveHumanReview(claim.claim_id, note || 'Resolved by provider manual verification and release confirmation.');
      setDone(true);
      onResolved?.();
    } catch {
      setError('Failed to submit human resolution. Please verify backend connection.');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="bg-emerald-50 border border-emerald-250 rounded-2xl px-5 py-4 flex items-center gap-3 shadow-sm animate-fade-in-up">
        <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
        <div>
          <p className="text-[13px] font-extrabold text-emerald-900">Resolution submitted successfully</p>
          <p className="text-[11px] text-emerald-700 mt-0.5 font-medium">
            The claim has re-entered the automated decision pipeline.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-sm animate-fade-in-up border-rose-100">
      <div className="px-5 py-3.5 border-b border-rose-100 bg-rose-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-600" />
          <h3 className="text-[12px] font-extrabold text-rose-900 uppercase tracking-wider">
            Hospital Review Resolution
          </h3>
        </div>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-[12px] text-slate-600 font-semibold leading-relaxed">
          Provide a clinical justification or document reference to manually resolve this review hold. The claim will re-enter normal classification.
        </p>

        <div>
          <label className="block text-[11px] font-bold text-slate-500 mb-1.5 uppercase tracking-wider">
            Resolution Note <span className="text-red-500">*</span>
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            placeholder="Type your justification note here (e.g., 'Metformin records located and released manually; conservative treatment duration satisfied')..."
            className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none resize-none transition-all"
          />
        </div>

        {error && (
          <p className="text-[12px] text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg font-semibold">
            {error}
          </p>
        )}

        <button
          onClick={handleResolve}
          disabled={loading || !note.trim()}
          className="w-full inline-flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-white text-[13px] font-extrabold rounded-xl transition-all shadow-md shadow-emerald-100"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Submitting Resolution…
            </>
          ) : (
            'Submit & Resume Automated Evaluation'
          )}
        </button>
      </div>
    </div>
  );
}
