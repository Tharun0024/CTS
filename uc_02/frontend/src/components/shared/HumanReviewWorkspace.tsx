import { AlertTriangle, Shield, CheckCircle, XCircle, FileText, UserCheck } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface HumanReviewWorkspaceProps {
  claim: ClaimDetails;
  portal?: 'hospital' | 'insurance';
}

export function HumanReviewWorkspace({ claim, portal = 'hospital' }: HumanReviewWorkspaceProps) {
  const decision = claim.decision;
  const isAgent2 = !!claim.agent2_invoked;
  const isHospital = portal === 'hospital';
  const themeCls = isHospital ? 'border-emerald-250 bg-emerald-50/20' : 'border-indigo-250 bg-indigo-50/20';
  const iconColor = isHospital ? 'text-emerald-600' : 'text-indigo-600';

  // Determine why automation stopped & recommended action based on reason_code
  const reasonCode = decision?.reason_code || claim.human_review_reasons?.[0] || 'UNCERTAIN_CONCLUSIVENESS';
  
  let stoppedWhy = 'Automation stopped because the clinical criteria could not be definitively validated with the available evidence.';
  let recommendedAction = 'Review the clinical documents, verify the diagnostic criteria, and manually determine prior authorization status.';

  if (reasonCode === 'SENSITIVE_DATA_BLOCKED') {
    stoppedWhy = 'Automation stopped because sensitive clinical data release consent was declined or blocked.';
    recommendedAction = 'Contact the provider to obtain manual authorization or release consent for the requested clinical documents.';
  } else if (reasonCode === 'PIPELINE_FAIL_CLOSED') {
    stoppedWhy = 'Automation stopped because the RAG decision pipeline failed closed on error.';
    recommendedAction = 'Inspect system logs for pipeline execution failures and trigger a re-evaluation once resolved.';
  } else if (reasonCode === 'NO_MATCHING_POLICY') {
    stoppedWhy = 'Automation stopped because no compatible active policy was found for the requested procedure.';
    recommendedAction = 'Verify if the policy ID on the claim is correct and corresponds to an active coverage rule.';
  } else if (claim.missing_information && claim.missing_information.length > 0) {
    stoppedWhy = 'Automation stopped because key required evidence items are missing and need provider resubmission.';
    recommendedAction = 'Verify if the provider has uploaded the missing documentation and re-trigger evaluation.';
  }

  // Check if provider declined
  const declinedDecision = (claim.provider_decisions ?? []).find(d => d.decision === 'DECLINE');
  if (declinedDecision) {
    stoppedWhy = 'Automation stopped because the provider declined consent to release recovered clinical evidence to the insurer.';
    recommendedAction = 'Contact the provider to resolve the consent release block or manually obtain paper/PDF documentation.';
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Workspace Cockpit Header */}
      <div className={clsx('border rounded-2xl p-4 flex items-start gap-3.5 shadow-sm', themeCls)}>
        <div className="mt-0.5">
          <AlertTriangle className={clsx('w-5 h-5', iconColor)} />
        </div>
        <div className="flex-1 space-y-1">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
            {isAgent2 ? 'Agent 2 Consent & Recovery Hold' : 'Agent 1 Clinical Reentry Hold'}
            <span className="text-[10px] font-bold bg-slate-100 border border-slate-200 text-slate-600 px-2 py-0.2 rounded">
              {reasonCode.replace(/_/g, ' ')}
            </span>
          </h4>
          <p className="text-xs text-slate-700 font-semibold leading-relaxed">
            <span className="font-extrabold text-slate-900">Why Stopped:</span> {stoppedWhy}
          </p>
          <p className="text-xs text-slate-700 font-semibold leading-relaxed">
            <span className="font-extrabold text-slate-900">Next Step:</span> {recommendedAction}
          </p>
        </div>
      </div>

      {/* Structured Status Deck */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Agent 1 Recommendation Metadata */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-slate-500" />
            Decision Engine Metadata
          </h4>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Recommendation</dt>
              <dd className="font-extrabold text-blue-600 uppercase">HUMAN REVIEW</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Reason Code</dt>
              <dd className="font-mono font-bold text-slate-800">{reasonCode}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Referenced Evidence</dt>
              <dd className="font-semibold text-slate-700">
                {decision?.referenced_evidence_ids && decision.referenced_evidence_ids.length > 0
                  ? decision.referenced_evidence_ids.join(', ')
                  : 'None referenced'}
              </dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-slate-500 font-bold mb-1">Missing/Uncertain Information</dt>
              <dd className="font-semibold text-amber-800 bg-amber-50 border border-amber-100 rounded-lg p-2 leading-relaxed">
                {claim.missing_information && claim.missing_information.length > 0
                  ? claim.missing_information.join('; ')
                  : 'None outstanding'}
              </dd>
            </div>
          </dl>
        </div>

        {/* Policy Context Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            Policy & Treatment Context
          </h4>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Payer</dt>
              <dd className="font-extrabold text-slate-800">{claim.policy.payer}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Policy ID</dt>
              <dd className="font-mono font-bold text-slate-800">{claim.policy.policy_id}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Procedure Code</dt>
              <dd className="font-mono font-bold text-slate-800">{claim.claim.procedure_code}</dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-slate-500 font-bold mb-0.5">Procedure Description</dt>
              <dd className="font-semibold text-slate-850 truncate">{claim.claim.procedure}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Agent 2 Recovery Details Panel */}
      {isAgent2 && (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-brand-600" />
              Agent 2 Clinical Crawler Results
            </h4>
            <span className="text-[10px] font-black uppercase tracking-widest bg-blue-100 text-blue-700 border border-blue-200 px-2.5 py-0.5 rounded-lg">
              Invoked
            </span>
          </div>

          <div className="p-4 space-y-4 text-xs">
            {/* Request Summary */}
            {claim.evidence_request && (
              <div className="bg-slate-50 border border-slate-150 rounded-xl p-3.5 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Evidence Requested</span>
                  <p className="font-semibold text-slate-800 mt-0.5">{claim.evidence_request.requested_evidence}</p>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Triggering Reason</span>
                  <p className="font-semibold text-slate-800 mt-0.5">{claim.evidence_request.reason}</p>
                </div>
              </div>
            )}

            {/* Found / Missing Recovery Items */}
            <div className="space-y-2">
              <span className="text-[10px] font-black text-slate-450 uppercase tracking-wider block">Recovery Analysis Ledger</span>
              <div className="border border-slate-150 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase border-b border-slate-150">
                    <tr>
                      <th className="px-3.5 py-2">Evidence Key</th>
                      <th className="px-3.5 py-2">Query Text</th>
                      <th className="px-3.5 py-2 text-right">Crawler Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {((claim.recovery_result?.item_results as any[]) || []).map((item, idx) => {
                      const isFound = item.state === 'FOUND';
                      return (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="px-3.5 py-2.5 font-bold text-slate-850">{item.evidence_key}</td>
                          <td className="px-3.5 py-2.5 text-slate-600 leading-normal">{item.request_text}</td>
                          <td className="px-3.5 py-2.5 text-right">
                            <span className={clsx(
                              'text-[9px] font-extrabold px-2.5 py-0.5 rounded border uppercase tracking-wider',
                              isFound
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-250'
                                : 'bg-red-50 text-red-700 border-red-250'
                            )}>
                              {item.state}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {(!claim.recovery_result?.item_results || claim.recovery_result.item_results.length === 0) && (
                      <tr>
                        <td colSpan={3} className="px-3.5 py-6 text-center text-slate-400 font-semibold">
                          No crawler item results found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Consent Status Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
              <div>
                <span className="text-[9px] font-bold text-slate-450 uppercase tracking-wider">Release Consent status</span>
                <p className={clsx(
                  'text-xs font-black mt-1 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border',
                  declinedDecision
                    ? 'bg-red-50 text-red-700 border-red-200'
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                )}>
                  {declinedDecision ? (
                    <>
                      <XCircle className="w-3.5 h-3.5" /> Release Declined (Consent Blocked)
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-3.5 h-3.5" /> Release Approved
                    </>
                  )}
                </p>
              </div>

              {declinedDecision && declinedDecision.reason && (
                <div>
                  <span className="text-[9px] font-bold text-slate-455 uppercase tracking-wider">Provider Decline Reason</span>
                  <p className="font-semibold text-slate-700 mt-1 italic">
                    "{declinedDecision.reason}"
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
