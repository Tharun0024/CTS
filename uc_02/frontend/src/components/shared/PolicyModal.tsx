import { useState, useEffect } from 'react';
import { X, Shield, FileText, Check, AlertTriangle, Clock, Calendar } from 'lucide-react';
import { getPolicyDetails } from '../../services/claimsApi';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface PolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  policyId: string;
  claim: ClaimDetails;
}

interface Criterion {
  criterion_id: string;
  criterion_name: string;
  text: string;
  documentation_requirements: string[];
}

interface PolicyDetails {
  policy_id: string;
  policy_title: string;
  payer: string;
  clinical_domain?: string;
  procedure_codes: string[];
  diagnosis_codes: string[];
  criteria: Criterion[];
  exclusions: string[];
  limitations: string[];
  contraindications: string[];
  source_reference?: string;
  policy_status?: string;
  effective_date?: string;
  revision_date?: string;
}

export function PolicyModal({ isOpen, onClose, policyId, claim }: PolicyModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<PolicyDetails | null>(null);

  useEffect(() => {
    if (!isOpen || !policyId) return;

    setLoading(true);
    setError(null);
    getPolicyDetails(policyId)
      .then((data) => {
        setPolicy(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load policy details:', err);
        setError('Failed to load policy details from the corpus.');
        setLoading(false);
      });
  }, [isOpen, policyId]);

  if (!isOpen) return null;

  const isAetna = (policy?.payer || claim.policy?.payer || '').toLowerCase().includes('aetna');
  const accentColor = isAetna ? 'text-rose-600 bg-rose-50 border-rose-100' : 'text-blue-600 bg-blue-50 border-blue-100';
  const buttonAccent = isAetna ? 'hover:bg-rose-50 text-rose-600 border-rose-200' : 'hover:bg-blue-50 text-blue-600 border-blue-200';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="relative w-full max-w-4xl max-h-[85vh] bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-100 flex flex-col overflow-hidden animate-scale-up"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-100 bg-slate-50/50">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className={clsx('text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full border', accentColor)}>
                {policy?.payer || claim.policy?.payer || 'Payer'}
              </span>
              <span className="text-xs font-mono font-bold text-slate-400">
                {policyId}
              </span>
            </div>
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight">
              {policy?.policy_title || claim.policy?.policy_name || 'Policy Details'}
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <div className={clsx('w-8 h-8 rounded-full border-2 border-t-transparent animate-spin', isAetna ? 'border-rose-600' : 'border-blue-600')} />
              <p className="text-xs text-slate-500 font-medium">Retrieving policy from RAG database...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-12 text-center max-w-md mx-auto space-y-3">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center text-red-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <p className="text-sm font-bold text-slate-800">{error}</p>
              <p className="text-xs text-slate-500">The requested policy ID may not exist in the local normalized corpus.</p>
            </div>
          )}

          {!loading && !error && policy && (
            <div className="space-y-6">
              {/* Claim Context Info Card */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Requested Procedure</span>
                  <p className="text-xs font-bold text-slate-800 mt-0.5">
                    {claim.claim.procedure} ({claim.claim.procedure_code})
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Clinical Domain</span>
                  <p className="text-xs font-bold text-slate-800 mt-0.5">
                    {policy.clinical_domain || 'Orthopedics'}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Policy Status</span>
                  <p className="text-xs font-bold text-emerald-600 mt-0.5 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" />
                    {policy.policy_status || 'Active'}
                  </p>
                </div>
              </div>

              {/* Policy Criteria */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  Policy Criteria
                </h3>
                <div className="space-y-3">
                  {policy.criteria.map((crit) => (
                    <div key={crit.criterion_id} className="border border-slate-100 rounded-xl p-4 bg-white shadow-sm space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-extrabold text-slate-800">
                          {crit.criterion_id}: {crit.criterion_name}
                        </span>
                        {claim.decision?.criteria_results?.[crit.criterion_id] !== undefined && (
                          <span className={clsx(
                            'text-[10px] font-bold px-2 py-0.5 rounded-md border flex items-center gap-1',
                            claim.decision.criteria_results[crit.criterion_id]
                              ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
                              : 'text-rose-700 bg-rose-50 border-rose-100'
                          )}>
                            {claim.decision.criteria_results[crit.criterion_id] ? (
                              <>
                                <Check className="w-3 h-3" /> Met
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="w-3 h-3" /> Not Met / Missing
                              </>
                            )}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-650 leading-relaxed font-medium">
                        {crit.text}
                      </p>
                      {crit.documentation_requirements && crit.documentation_requirements.length > 0 && (
                        <div className="pt-2.5 border-t border-slate-50">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Required Evidence</span>
                          <ul className="mt-1.5 space-y-1.5">
                            {crit.documentation_requirements.map((req, idx) => (
                              <li key={idx} className="text-xs font-semibold text-slate-700 flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-350 mt-1.5 flex-shrink-0" />
                                {req}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Exclusions & Limitations */}
              {(policy.exclusions.length > 0 || policy.limitations.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {policy.exclusions.length > 0 && (
                    <div className="bg-rose-50/50 border border-rose-100 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-black text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                        Coverage Exclusions
                      </h4>
                      <ul className="space-y-1.5">
                        {policy.exclusions.map((exc, idx) => (
                          <li key={idx} className="text-xs text-rose-750 font-semibold leading-relaxed flex items-start gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-rose-400 mt-2 flex-shrink-0" />
                            {exc}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {policy.limitations.length > 0 && (
                    <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-black text-slate-750 uppercase tracking-wider flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        Policy Limitations
                      </h4>
                      <ul className="space-y-1.5">
                        {policy.limitations.map((lim, idx) => (
                          <li key={idx} className="text-xs text-slate-650 font-semibold leading-relaxed flex items-start gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
                            {lim}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-4 text-[11px] font-bold text-slate-400">
            {policy?.effective_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Effective: {policy.effective_date}
              </span>
            )}
            {policy?.revision_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Revised: {policy.revision_date}
              </span>
            )}
          </div>
          <button 
            type="button"
            onClick={onClose}
            className={clsx('px-4 py-2 text-xs font-bold border rounded-lg shadow-sm transition-all', buttonAccent)}
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
}
