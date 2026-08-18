import { AlertTriangle, Shield, FileText, UserCheck, EyeOff } from 'lucide-react';
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
  // Phase 3: Agent1 REJECT held for human cross-verification.
  const isHumanVerification = !!claim.human_verification_pending;
  const originalRejection = claim.original_rejection ?? null;
  const themeCls = isHospital ? 'border-emerald-250 bg-emerald-50/20' : 'border-indigo-250 bg-indigo-50/20';
  const iconColor = isHospital ? 'text-emerald-600' : 'text-indigo-600';

  // Determine why automation stopped & recommended action based on reason_code
  const reasonCode = decision?.reason_code || claim.human_review_reasons?.[0] || 'UNCERTAIN_CONCLUSIVENESS';
  
  let stoppedWhy = decision?.reason || 'Automation stopped because the clinical criteria could not be definitively validated with the available evidence.';
  let recommendedAction = 'Review the clinical documents, verify the diagnostic criteria, and manually determine prior authorization status.';

  if (reasonCode === 'SENSITIVE_DATA_BLOCKED') {
    stoppedWhy = decision?.reason || 'Automation stopped because sensitive clinical data release consent was declined or blocked.';
    recommendedAction = 'Contact the provider to obtain manual authorization or release consent for the requested clinical documents.';
  } else if (reasonCode === 'PIPELINE_FAIL_CLOSED') {
    stoppedWhy = decision?.reason || 'Automation stopped because the RAG decision pipeline failed closed on error.';
    recommendedAction = 'Inspect system logs for pipeline execution failures and trigger a re-evaluation once resolved.';
  } else if (reasonCode === 'NO_MATCHING_POLICY') {
    stoppedWhy = decision?.reason || 'Automation stopped because no compatible active policy was found for the requested procedure.';
    recommendedAction = 'Verify if the policy ID on the claim is correct and corresponds to an active coverage rule.';
  } else if (!decision?.reason && claim.missing_information && claim.missing_information.length > 0) {
    stoppedWhy = 'Automation stopped because key required evidence items are missing and need provider resubmission.';
    recommendedAction = 'Verify if the provider has uploaded the missing documentation and re-trigger evaluation.';
  }

  // Check if provider declined
  const declinedDecision = (claim.provider_decisions ?? []).find(d => d.decision === 'DECLINE');
  if (declinedDecision) {
    stoppedWhy = 'Automation stopped because the provider declined consent to release recovered clinical evidence to the insurer.';
    recommendedAction = 'Contact the provider to resolve the consent release block or manually obtain paper/PDF documentation.';
  }

  const sensitiveItems = (claim.policy_evidence || []).filter(e => e.sensitive);

  return (
    <div className="space-y-5 animate-fade-in-up">
      {/* 1. Header Stopped/Recommended Banner */}
      <div className={clsx('border rounded-2xl p-4.5 flex items-start gap-3.5 shadow-sm', themeCls)}>
        <div className="mt-0.5">
          <AlertTriangle className={clsx('w-5 h-5', iconColor)} />
        </div>
        <div className="flex-1 space-y-1">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5 flex-wrap">
            {isHumanVerification
              ? 'Human Verification Required'
              : isAgent2 ? 'Agent 2 Consent & Recovery Hold' : 'Agent 1 Clinical Reentry Hold'}
            <span className="text-[10px] font-bold bg-slate-100 border border-slate-200 text-slate-650 px-2 py-0.2 rounded font-mono">
              {reasonCode.replace(/_/g, ' ')}
            </span>
          </h4>
          <p className="text-xs text-slate-700 font-semibold leading-relaxed">
            <span className="font-extrabold text-slate-900">Why Automation Stopped:</span> {stoppedWhy}
          </p>
          <p className="text-xs text-slate-700 font-semibold leading-relaxed">
            <span className="font-extrabold text-slate-900">Recommended Action:</span> {recommendedAction}
          </p>
        </div>
      </div>

      {/* 2. Side-by-Side Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Decision Engine Metadata */}
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
              <dd className="font-semibold text-slate-755">
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

        {/* Policy & Treatment Context */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            Policy & Treatment Context
          </h4>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Payer</dt>
              <dd className="font-extrabold text-slate-850">{claim.policy?.payer || 'N/A'}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Policy ID</dt>
              <dd className="font-mono font-bold text-slate-850">{claim.policy?.policy_id || 'N/A'}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <dt className="text-slate-500 font-bold">Procedure Code</dt>
              <dd className="font-mono font-bold text-slate-850">{claim.claim?.procedure_code || 'N/A'}</dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-slate-500 font-bold mb-0.5">Procedure Description</dt>
              <dd className="font-semibold text-slate-800 leading-normal">{claim.claim?.procedure || 'N/A'}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* 3. Workflow-Specific Analysis Ledgers */}
      {!isAgent2 ? (
        /* ==================== AGENT 1 LAYOUT ==================== */
        <div className="space-y-4.5">
          {/* Phase 3: Human cross-verification of an Agent 1 REJECT */}
          {isHumanVerification && (
            <div className="bg-white border-2 border-rose-200 rounded-2xl overflow-hidden shadow-sm">
              <div className="px-4 py-3 bg-rose-50 border-b border-rose-200 flex items-center justify-between">
                <h4 className="text-xs font-black uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                  <UserCheck className="w-4 h-4 text-rose-600" />
                  Human Verification Required
                </h4>
                <span className="text-[10px] font-black uppercase tracking-widest bg-rose-100 text-rose-700 border border-rose-200 px-2 py-0.5 rounded">
                  {isHospital ? 'Hospital resolves' : 'Insurance read-only'}
                </span>
              </div>

              <div className="p-4 space-y-4">
                {/* Decision chain: prior auth -> agent 1 -> confidence -> verification -> final */}
                <div className="flex flex-wrap items-stretch gap-1.5">
                  {[
                    {
                      label: 'Prior Auth Status',
                      value: claim.prior_auth_precheck
                        ? (claim.prior_auth_precheck.requires_prior_auth ? 'REQUIRED' : 'NOT REQUIRED')
                        : 'N/A',
                      cls: 'bg-slate-50 border-slate-200 text-slate-700',
                    },
                    {
                      label: 'Agent 1 Decision',
                      value: `${originalRejection?.outcome ?? 'REJECT'}${originalRejection?.reason_code ? ` · ${originalRejection.reason_code}` : ''}`,
                      cls: 'bg-rose-50 border-rose-200 text-rose-700',
                    },
                    {
                      label: 'Confidence',
                      value: originalRejection?.confidence_score != null
                        ? `${Math.round(originalRejection.confidence_score * 100)}% ${originalRejection.confidence_level ?? ''}`.trim()
                        : 'N/A',
                      cls: 'bg-amber-50 border-amber-200 text-amber-700',
                    },
                    {
                      label: 'Human Verification',
                      value: 'REQUIRED · PENDING',
                      cls: 'bg-blue-50 border-blue-200 text-blue-700',
                    },
                    {
                      label: 'Final Decision',
                      value: 'Pending human verification',
                      cls: 'bg-slate-50 border-slate-200 text-slate-500',
                    },
                  ].map((step, idx) => (
                    <div key={step.label} className="flex items-center gap-1.5">
                      <div className={clsx('border rounded-lg px-2.5 py-1.5 min-w-[110px]', step.cls)}>
                        <span className="block text-[9px] font-black uppercase tracking-wider opacity-70">{step.label}</span>
                        <span className="block text-[11px] font-extrabold leading-snug">{step.value}</span>
                      </div>
                      {idx < 4 && <span className="text-slate-300 font-black">→</span>}
                    </div>
                  ))}
                </div>

                {/* Immutable original Agent 1 rejection */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-wider">
                      Original Agent 1 Rejection (immutable audit record)
                    </span>
                    <span className="text-[9px] font-extrabold bg-rose-100 text-rose-700 border border-rose-200 px-2 py-0.5 rounded uppercase">
                      {originalRejection?.outcome ?? 'REJECT'}
                    </span>
                  </div>
                  <p className="text-[11px] font-bold text-slate-700">
                    Reason code: <span className="font-mono">{originalRejection?.reason_code ?? 'UNKNOWN'}</span>
                  </p>
                  {(originalRejection?.confidence_factors ?? []).length > 0 && (
                    <ul className="text-[11px] text-slate-600 font-semibold list-disc pl-4 space-y-0.5">
                      {(originalRejection?.confidence_factors ?? []).map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  )}
                  <div>
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-wider block mb-1">
                      Deterministic Reasoning / Evidence Explanation
                    </span>
                    <ul className="text-[11px] text-slate-700 font-medium list-disc pl-4 space-y-1 leading-relaxed">
                      {(originalRejection?.reasoning ?? []).map((line, idx) => (
                        <li key={idx}>{line}</li>
                      ))}
                      {(originalRejection?.reasoning ?? []).length === 0 && (
                        <li>{decision?.reason || 'No deterministic reasoning recorded.'}</li>
                      )}
                    </ul>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 font-semibold">
                  The claim is <span className="font-extrabold text-slate-700">NOT rejected as terminal</span> until the
                  hospital completes human verification. {isHospital
                    ? 'Use the resolution panel below to approve or reject.'
                    : 'Waiting for hospital resolution; this portal is read-only.'}
                </p>
              </div>
            </div>
          )}

          {/* Agent 1 decision confidence (informational only) */}
          {decision && decision.confidence_score != null && (
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-2">
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-slate-500" />
                  Agent 1 Decision Confidence
                </span>
                <span className="text-[9px] font-bold text-slate-400 normal-case tracking-normal">
                  Informational only — never changes the decision
                </span>
              </h4>
              <div className="flex items-center gap-3">
                <span className="text-xl font-black text-slate-850">
                  {Math.round(decision.confidence_score * 100)}%
                </span>
                <span className={clsx(
                  'text-[9px] font-extrabold px-2.5 py-0.5 rounded border uppercase tracking-wider',
                  decision.confidence_level === 'HIGH'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-250'
                    : decision.confidence_level === 'MEDIUM'
                      ? 'bg-amber-50 text-amber-700 border-amber-250'
                      : 'bg-rose-50 text-rose-700 border-rose-250'
                )}>
                  {decision.confidence_level || 'N/A'}
                </span>
                <span className="font-mono text-[10px] text-slate-500">
                  score {decision.confidence_score.toFixed(2)}
                </span>
              </div>
              {(decision.confidence_factors || []).length > 0 && (
                <ul className="text-xs text-slate-600 font-semibold list-disc pl-4 space-y-0.5 leading-relaxed">
                  {(decision.confidence_factors || []).map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* RAG Criteria Evaluations */}
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                Clinical Criteria Evaluations
              </h4>
              <span className="text-[10px] font-black uppercase tracking-widest bg-slate-100 text-slate-600 border border-slate-200 px-2 py-0.5 rounded">
                Agent 1 RAG
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[500px]">
                <thead className="bg-slate-50/50 text-[10px] font-bold text-slate-450 uppercase border-b border-slate-150">
                  <tr>
                    <th className="px-4 py-2 w-1/4">Criterion ID</th>
                    <th className="px-4 py-2 w-2/3">Evaluation Rationale</th>
                    <th className="px-4 py-2 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(claim.decision?.criteria_evaluations || {}).map(([cid, evalItem]: [string, any]) => {
                    const isMet = evalItem.status === 'MET';
                    const assessment = claim.decision?.criterion_assessments?.[cid] || evalItem.reason || 'No specific assessment logged.';

                    const renderAssessmentText = () => {
                      if (!assessment) return 'No specific assessment logged.';
                      if (typeof assessment === 'object') {
                        if (Array.isArray(assessment.reasoning)) {
                          return (
                            <div className="space-y-1">
                              {assessment.reasoning.map((r: string, idx: number) => (
                                <p key={idx}>{r}</p>
                              ))}
                              {assessment.evidence_paths && assessment.evidence_paths.length > 0 && (
                                <p className="text-[10px] text-slate-400 font-mono mt-1">
                                  Evidence: {assessment.evidence_paths.join(', ')}
                                </p>
                              )}
                            </div>
                          );
                        }
                        if (typeof assessment.reasoning === 'string') {
                          return assessment.reasoning;
                        }
                        if (Array.isArray(assessment.reason)) {
                          return assessment.reason.join(' ');
                        }
                        if (typeof assessment.reason === 'string') {
                          return assessment.reason;
                        }
                        return JSON.stringify(assessment);
                      }
                      return String(assessment);
                    };

                    return (
                      <tr key={cid} className="hover:bg-slate-50/20">
                        <td className="px-4 py-3 font-bold text-slate-800 align-top leading-normal">
                          {cid.replace(/_/g, ' ')}
                        </td>
                        <td className="px-4 py-3 text-slate-600 leading-relaxed font-semibold font-mono text-[11px]">
                          {renderAssessmentText()}
                        </td>
                        <td className="px-4 py-3 text-right align-top">
                          <span className={clsx(
                            'text-[9px] font-extrabold px-2.5 py-0.5 rounded border uppercase tracking-wider',
                            isMet
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-250'
                              : 'bg-rose-50 text-rose-700 border-rose-250'
                          )}>
                            {evalItem.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {Object.keys(claim.decision?.criteria_evaluations || {}).length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-6 text-center text-slate-400 font-semibold">
                        No criterion evaluations returned by the decision engine.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Clinical Evidence & Provenance */}
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                Clinical Evidence & Provenance Ledger
              </h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[500px]">
                <thead className="bg-slate-50/50 text-[10px] font-bold text-slate-450 uppercase border-b border-slate-150">
                  <tr>
                    <th className="px-4 py-2 w-1/4">Key / ID</th>
                    <th className="px-4 py-2 w-2/3">Extracted Clinical Metric</th>
                    <th className="px-4 py-2">Provenance Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(claim.policy_evidence || []).map((ev, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/20">
                      <td className="px-4 py-3 align-top">
                        <span className="font-bold text-slate-800 block leading-tight">{ev.evidence_key}</span>
                        <span className="font-mono text-[9px] text-slate-400">{ev.evidence_id}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-650 leading-relaxed font-semibold">
                        {ev.content_reference}
                      </td>
                      <td className="px-4 py-3 font-mono text-[10px] text-slate-500 align-top truncate max-w-[160px]">
                        {ev.provenance}
                      </td>
                    </tr>
                  ))}
                  {(claim.policy_evidence || []).length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-6 text-center text-slate-400 font-semibold">
                        No active clinical evidence attached to this claim.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* ==================== AGENT 2 LAYOUT ==================== */
        <div className="space-y-4.5 animate-fade-in-up">
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <UserCheck className="w-4 h-4 text-indigo-650" />
                Agent 2 Clinical Crawler Results
              </h4>
              <span className="text-[10px] font-black uppercase tracking-widest bg-blue-100 text-blue-700 border border-blue-200 px-2.5 py-0.5 rounded-lg">
                Crawl Active
              </span>
            </div>

            <div className="p-4 space-y-4 text-xs">
              {/* EvidenceRequest Summary */}
              {claim.evidence_request && (
                <div className="bg-slate-50 border border-slate-150 rounded-xl p-3.5 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Evidence Requested</span>
                    <p className="font-semibold text-slate-800 mt-0.5">{claim.evidence_request.requested_evidence}</p>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Requested Reason</span>
                    <p className="font-semibold text-slate-800 mt-0.5">{claim.evidence_request.reason}</p>
                  </div>
                </div>
              )}

              {/* Crawler FOUND / MISSING analysis */}
              <div className="space-y-2">
                <span className="text-[10px] font-black text-slate-450 uppercase tracking-wider block">Recovery Analysis Ledger</span>
                <div className="border border-slate-150 rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase border-b border-slate-150">
                      <tr>
                        <th className="px-3.5 py-2">Evidence Key</th>
                        <th className="px-3.5 py-2">Query Search Text</th>
                        <th className="px-3.5 py-2 text-right">Crawler Outcome</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {((claim.recovery_result?.item_results as any[]) || []).map((item, idx) => {
                        const isFound = item.state === 'FOUND';
                        return (
                          <tr key={idx} className="hover:bg-slate-50/50">
                            <td className="px-3.5 py-2.5 font-bold text-slate-850">{item.evidence_key}</td>
                            <td className="px-3.5 py-2.5 text-slate-600 leading-normal font-semibold">{item.request_text}</td>
                            <td className="px-3.5 py-2.5 text-right">
                              <span className={clsx(
                                'text-[9px] font-extrabold px-2.5 py-0.5 rounded border uppercase tracking-wider',
                                isFound
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-250'
                                  : 'bg-rose-50 text-rose-700 border-rose-250'
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

              {/* Sensitivity Classifications */}
              {sensitiveItems.length > 0 && (
                <div className="bg-red-50/50 border border-red-200 rounded-xl p-3.5 space-y-2">
                  <span className="text-[10px] font-black text-red-700 uppercase tracking-wider flex items-center gap-1.5">
                    <EyeOff className="w-3.5 h-3.5" />
                    Sensitive Clinical Data Blocked (Release Prevented)
                  </span>
                  <div className="space-y-1.5 text-xs">
                    {sensitiveItems.map((item, idx) => (
                      <div key={idx} className="text-slate-700 font-medium leading-relaxed bg-white border border-red-100 p-2 rounded-lg">
                        <span className="font-extrabold text-red-750">{item.evidence_key}</span>: {item.sensitivity_reason || 'Sensitive data constraint blocks release to insurer.'}
                        <div className="text-[9px] text-slate-400 mt-0.5 font-mono">Evidence ID: {item.evidence_id} • Provenance: {item.provenance}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Provider Consent Status */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-slate-100">
                <div>
                  <span className="text-[9px] font-bold text-slate-450 uppercase tracking-wider">Release Consent Status</span>
                  <p className={clsx(
                    'text-xs font-black mt-1 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border',
                    declinedDecision
                      ? 'bg-red-50 text-red-700 border-red-200'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  )}>
                    {declinedDecision ? 'DECLINE (Consent Declined)' : 'ACCEPT (Consent Release Approved)'}
                  </p>
                </div>

                {declinedDecision && declinedDecision.reason && (
                  <div>
                    <span className="text-[9px] font-bold text-slate-450 uppercase tracking-wider">Decline Justification</span>
                    <p className="font-semibold text-slate-700 mt-1 italic">
                      "{declinedDecision.reason}"
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
