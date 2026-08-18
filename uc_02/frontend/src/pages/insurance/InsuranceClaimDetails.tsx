import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ClaimHeader } from '../../components/shared/ClaimHeader';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { HumanReviewWorkspace } from '../../components/shared/HumanReviewWorkspace';
import { PriorAuthStatusCard } from '../../components/shared/PriorAuthStatusCard';
import { AgentConfidenceCard } from '../../components/shared/AgentConfidenceCard';
import { DecisionChain } from '../../components/shared/DecisionChain';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getInsuranceClaimDetails } from '../../services/insuranceApi';
import { PolicyModal } from '../../components/shared/PolicyModal';
import { decisionLabel } from '../../utils/decisionHumanizer';
import { usePolling, isTerminalStatus } from '../../services/polling';
import type { ClaimDetails, ClaimVersion } from '../../types/claim';
import { Loader2, Shield, Clock } from 'lucide-react';

export function InsuranceClaimDetails() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ClaimDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPolicyOpen, setIsPolicyOpen] = useState(false);

  const fetchClaim = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getInsuranceClaimDetails(id);
      setClaim(data);
      if (loading) setLoading(false);
    } catch {
      setError('Failed to load claim details.');
      setLoading(false);
    }
  }, [id, loading]);

  useEffect(() => { fetchClaim(); }, [id]);

  // Poll while non-terminal
  usePolling(
    () => getInsuranceClaimDetails(id!),
    (data) => setClaim(data),
    (data) => isTerminalStatus(data.status),
    5000,
    !!id && !!claim && !isTerminalStatus(claim.status)
  );

  if (loading) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <LoadingState message="Loading claim details…" fullPage />
    </div>
  );

  if (error || !claim) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ErrorState message={error || 'Claim not found.'} onRetry={fetchClaim} />
    </div>
  );

  const isProcessing = claim.status === 'PROCESSING' || claim.status === 'UNDER_REVIEW' || claim.status === 'SUBMITTED';

  // Gap 3: resubmission history driven by the real backend versions.
  const versionsForView: ClaimVersion[] = (claim.versions && claim.versions.length > 0)
    ? claim.versions
    : [{
        version: 'V1',
        attempt: 1,
        decision: claim.decision
          ? { status: claim.decision.status, reason: claim.decision.reason, reason_code: claim.decision.reason_code }
          : null,
      }];
  const versionStatusCls: Record<string, string> = {
    ACCEPT: 'text-emerald-700 bg-emerald-50 border-emerald-150',
    REJECT: 'text-red-700 bg-red-50 border-red-150',
    MORE_INFORMATION: 'text-amber-700 bg-amber-50 border-amber-150',
    HUMAN_REVIEW: 'text-blue-700 bg-blue-50 border-blue-150',
  };

  const requiredEvidencePaths = claim.decision?.criterion_assessments
    ? Object.values(claim.decision.criterion_assessments)
        .flatMap((a: any) => a.required_evidence_paths || [])
        .filter(Boolean)
    : [];

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ClaimHeader claim={claim} backPath="/insurance/claims" backLabel="Back to Incoming Claims" />

      {/* Decision Flow Chain */}
      <DecisionChain claim={claim} />

      {/* Processing banner */}
      {isProcessing && (
        <div className="mb-4 bg-brand-50 border border-brand-200 rounded-lg p-3.5 flex items-center gap-3 shadow-sm animate-fade-in-up">
          <Loader2 className="w-4 h-4 text-brand-600 animate-spin flex-shrink-0" />
          <p className="text-xs text-brand-800 font-semibold">Claim is being processed. Polling for updates…</p>
        </div>
      )}

      {/* 3-col grid: main | decision */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left: claim data */}
        <div className="xl:col-span-2 space-y-4">
          {/* Patient + Clinical */}
          <div className="grid grid-cols-1 gap-4">
            <PatientInfoCard patient={claim.patient || { patient_id: 'UNKNOWN', age: 0, gender: 'Unknown' }} />
          </div>

          {/* Phase 4: persisted Phase 1 prior-auth pre-check (identical record as the hospital portal) */}
          <PriorAuthStatusCard claim={claim} portal="insurance" />

          {/* V1 Workflow Details */}
          <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm space-y-4 animate-fade-in-up">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-brand-600" />
                V1 Workflow & Resubmission Status
              </h3>
              <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                Attempt {claim.attempt ?? 1}
              </span>
            </div>

            {claim.status === 'MORE_INFO' || claim.evidence_request ? (
              <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4.5 space-y-4">
                <div className="flex items-center justify-between border-b border-amber-200 pb-2">
                  <h4 className="text-[12px] font-black text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                    <Loader2 className="w-4 h-4 text-amber-600 animate-spin" />
                    MORE INFORMATION REQUIRED
                  </h4>
                  <span className="text-[9px] font-extrabold bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full">
                    {claim.evidence_request?.status.replace(/_/g, ' ') || 'AWAITING RESPONSE'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-3">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Requested Evidence</span>
                      <p className="font-extrabold text-slate-900 mt-0.5">{claim.evidence_request?.requested_evidence || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide font-sans">Agent 1 Reasoning</span>
                      <div className="font-medium text-slate-700 mt-0.5 space-y-1 bg-white p-2.5 rounded-lg border border-slate-100 max-h-40 overflow-y-auto font-mono text-[11px] leading-relaxed">
                        {claim.decision?.reasoning && claim.decision.reasoning.length > 0 ? (
                          claim.decision.reasoning.map((r, i) => <p key={i}>{r}</p>)
                        ) : (
                          <p>{claim.decision?.reason || 'No specific reasoning trace provided.'}</p>
                        )}
                      </div>
                    </div>
                    {claim.decision?.criterion_assessments && (
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Required Evidence Paths</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {requiredEvidencePaths.map((path, idx) => (
                            <span key={idx} className="font-mono text-[10px] bg-white text-slate-800 px-2 py-0.5 rounded border border-slate-150 shadow-sm">
                                {path}
                              </span>
                            ))}
                          {requiredEvidencePaths.length === 0 && (
                            <span className="text-slate-405 italic">None recorded.</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Agent 2 Recovery Status</span>
                      <div className="mt-0.5 p-2.5 bg-white rounded-lg border border-slate-100 text-[11px] font-medium text-slate-700 space-y-1.5 shadow-sm">
                        {claim.agent2_invoked ? (
                          <>
                            <p className="font-extrabold text-indigo-700 flex items-center gap-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                              Agent 2 Recovery Invoked
                            </p>
                            {claim.recovery_result?.recovered_evidence_ids && claim.recovery_result.recovered_evidence_ids.length > 0 ? (
                              <p>Recovered Evidence: <span className="font-mono bg-indigo-50 px-1 py-0.2 rounded border border-indigo-100">{claim.recovery_result.recovered_evidence_ids.join(', ')}</span></p>
                            ) : (
                              <p className="text-slate-400 italic">No releasable evidence recovered by Agent 2 yet.</p>
                            )}
                            {claim.recovery_result?.notes && claim.recovery_result.notes.map((note, idx) => (
                              <p key={idx} className="text-slate-500 italic text-[10px]">• {note}</p>
                            ))}
                          </>
                        ) : (
                          <p className="text-slate-400 italic">Agent 2 Recovery not invoked / not available.</p>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Provider Resubmission Status</span>
                      <div className="mt-0.5 p-2.5 bg-white rounded-lg border border-slate-100 text-[11px] font-medium text-slate-700 space-y-1.5 shadow-sm">
                        <p>Status: <span className="font-extrabold text-slate-900 uppercase">{claim.resubmission_status || claim.resubmission?.status || 'NOT REQUIRED'}</span></p>
                        {claim.provider_decisions && claim.provider_decisions.length > 0 ? (
                          <div className="border-t border-slate-100 pt-1.5 mt-1.5 space-y-1">
                            <p className="font-bold text-slate-800">Hospital Provider Decisions:</p>
                            {claim.provider_decisions.map((d, i) => (
                              <p key={i} className="text-[10px] border-b border-slate-50 pb-1 last:border-0">
                                <span className={`font-black px-1 rounded ${d.decision === 'ACCEPT' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-rose-50 text-rose-700 border border-rose-100'}`}>{d.decision}</span> on {d.decided_at ? new Date(d.decided_at).toLocaleString() : 'N/A'}
                                {d.reason && <span className="text-slate-404 italic block mt-0.5">Reason: {d.reason}</span>}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-slate-404 italic">No provider consent decisions recorded.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 border border-slate-205 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center">
                  <Clock className="w-6 h-6 text-slate-350 mb-2" />
                  <p className="text-xs font-semibold text-slate-500">No Evidence Request</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">This claim has not requested additional clinical documents.</p>
                </div>
                <div className="bg-slate-50 border border-slate-205 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center">
                  <Clock className="w-6 h-6 text-slate-350 mb-2" />
                  <p className="text-xs font-semibold text-slate-500">No Evidence Uploaded</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Awaiting provider clinical data release.</p>
                </div>
              </div>
            )}

            {/* Resubmission History — real backend versions (V1/V2) */}
            <div className="border-t border-slate-100 pt-3">
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Resubmission History</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {versionsForView.map((v, idx) => {
                  const attemptNo = v.attempt ?? idx + 1;
                  const delta = v.new_evidence_delta ?? [];
                  return (
                    <div key={`${v.version}-${attemptNo}`} className="border border-slate-150 rounded-xl p-3 bg-slate-50/50 flex flex-col justify-between text-xs">
                      <div className="flex items-center justify-between font-bold text-slate-700 mb-1">
                        <span>Attempt {attemptNo} · {v.version}</span>
                        {v.decision ? (
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold font-mono border ${versionStatusCls[v.decision.status] ?? 'text-slate-600 bg-slate-100 border-slate-200'}`}>
                            {decisionLabel(v.decision.status)}
                          </span>
                        ) : (
                          <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-slate-100 border border-slate-200 text-slate-500">PENDING</span>
                        )}
                      </div>
                      {v.decision && (
                        <p className="text-[10px] text-slate-500 mt-1 leading-snug">{v.decision.reason}</p>
                      )}
                      {delta.length > 0 && (
                        <p className="text-[10px] font-semibold text-emerald-700 mt-1">+{delta.length} new evidence item(s)</p>
                      )}
                    </div>
                  );
                })}

                {(claim.attempt ?? 1) < 2 && versionsForView.length < 2 && (
                  <div className="border border-dashed border-slate-200 rounded-xl p-3 flex items-center justify-center text-center">
                    <span className="text-[10px] font-bold text-slate-400">Attempt 2 Awaiting Response</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Policy Evidence — the core of the insurance review */}
          {(claim.policy_evidence || []).length > 0 && (
            <PolicyEvidencePanel
              evidence={claim.policy_evidence}
              policyName={claim.policy?.policy_name || 'Policy on file'}
              policyId={claim.policy?.policy_id}
              portal="insurance"
              onViewPolicy={() => setIsPolicyOpen(true)}
            />
          )}

          {(claim.status === 'HUMAN_REVIEW' || claim.workflow_state === 'HUMAN_REVIEW') && (
            <HumanReviewWorkspace claim={claim} portal="insurance" />
          )}

          {/* Missing information list */}
          {(claim.missing_information || []).length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3.5 shadow-sm animate-fade-in-up">
              <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wide mb-2.5">Missing Information</h3>
              <ul className="space-y-1">
                {claim.missing_information.map((item, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-amber-800 font-medium">
                    <span className="text-amber-500 font-bold">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* System decision (if already decided) */}
          {claim.decision && (
            <div className="bg-white rounded-lg border border-slate-200 p-3.5 shadow-sm animate-fade-in-up">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide mb-2.5">System Recommendation</h3>
              <dl className="space-y-2">
                <div className="flex justify-between items-baseline border-b border-slate-50 pb-1">
                  <dt className="text-[11px] text-slate-500">Decision</dt>
                  <dd className="text-xs font-bold text-slate-800">{decisionLabel(claim.decision.status)}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-slate-500 mb-1">Reason</dt>
                  <dd className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-100 font-medium whitespace-pre-wrap">
                    {claim.decision.reason}
                  </dd>
                </div>
                {claim.human_resolution && (
                  <div>
                    <dt className="text-[11px] text-slate-500 mb-1">Human Resolution (Hospital)</dt>
                    <dd className="text-xs text-slate-700 leading-relaxed bg-rose-50 p-2.5 rounded border border-rose-100 font-medium whitespace-pre-wrap">
                      {claim.human_resolution}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {/* Phase 4: persisted Phase 2 confidence metrics (same values as the hospital portal) */}
          <AgentConfidenceCard claim={claim} />

        </div>

        {/* Right: Decision Panel + Timeline + policy reference + documents */}
        <div className="space-y-4">
          {claim.status === 'HUMAN_REVIEW' && (
            claim.agent2_invoked ? (
              <div className="bg-amber-50 border border-amber-250 rounded-2xl p-4.5 text-center shadow-sm animate-fade-in-up">
                <Clock className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                <p className="text-xs font-black text-amber-900 uppercase tracking-wider">Provider/Hospital Resolution Pending</p>
                <p className="text-[11px] text-amber-700 mt-1.5 font-semibold leading-relaxed">
                  This claim is held for provider evidence release consent. Waiting for hospital resolution.
                </p>
              </div>
            ) : (
              <div className="bg-blue-50 border border-blue-250 rounded-2xl p-4.5 text-center shadow-sm animate-fade-in-up">
                <Clock className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                <p className="text-xs font-black text-blue-900 uppercase tracking-wider">Hospital Clinical Resolution Pending</p>
                <p className="text-[11px] text-blue-700 mt-1.5 font-semibold leading-relaxed">
                  This claim requires manual clinical review and resolution by the hospital provider.
                </p>
              </div>
            )
          )}
          {claim.timeline && (
            <ClaimTimeline events={claim.timeline} portal="insurance" />
          )}

          {/* Policy reference */}
          <div className="bg-white rounded-lg border border-slate-200 p-3.5 shadow-sm animate-fade-in-up stagger-2">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide mb-2.5">Policy Reference</h3>
            <dl className="space-y-2">
              <div className="border-b border-slate-50 pb-1 flex justify-between items-baseline">
                <dt className="text-[10px] text-slate-400 uppercase tracking-wider">Payer</dt>
                <dd className="text-xs font-bold text-slate-800">{claim.policy.payer || 'N/A'}</dd>
              </div>
              <div className="border-b border-slate-50 pb-1 flex justify-between items-baseline">
                <dt className="text-[10px] text-slate-400 uppercase tracking-wider">Policy ID</dt>
                <dd className="text-xs font-mono font-bold text-slate-700">{claim.policy.policy_id || 'N/A'}</dd>
              </div>
              <div className="flex justify-between items-baseline">
                <dt className="text-[10px] text-slate-400 uppercase tracking-wider">Policy Name</dt>
                <dd className="text-xs font-mono font-bold text-slate-700">{claim.policy.policy_name || 'N/A'}</dd>
              </div>
            </dl>
            <div className="border-t border-slate-100 pt-2 mt-3">
              <button
                type="button"
                onClick={() => setIsPolicyOpen(true)}
                className="text-[11px] font-bold text-brand-600 hover:text-brand-700 hover:underline"
              >
                View Policy Details
              </button>
            </div>
          </div>

        </div>
      </div>
      {claim && (
        <PolicyModal
          isOpen={isPolicyOpen}
          onClose={() => setIsPolicyOpen(false)}
          policyId={claim.policy?.policy_id}
          claim={claim}
        />
      )}
    </div>
  );
}
