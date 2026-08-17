import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ClaimHeader } from '../../components/shared/ClaimHeader';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { HumanReviewWorkspace } from '../../components/shared/HumanReviewWorkspace';
import { DecisionPanel } from '../../components/insurance/DecisionPanel';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getInsuranceClaimDetails } from '../../services/insuranceApi';
import { PolicyModal } from '../../components/shared/PolicyModal';
import { decisionLabel } from '../../utils/decisionHumanizer';
import { usePolling, isTerminalStatus } from '../../services/polling';
import type { ClaimDetails, ClaimVersion, DecisionStatus } from '../../types/claim';
import { Loader2, Shield } from 'lucide-react';

export function InsuranceClaimDetails() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ClaimDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [decisionMade, setDecisionMade] = useState<DecisionStatus | null>(null);
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

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ClaimHeader claim={claim} backPath="/insurance/claims" backLabel="Back to Incoming Claims" />

      {/* Processing banner */}
      {isProcessing && (
        <div className="mb-4 bg-brand-50 border border-brand-200 rounded-lg p-3.5 flex items-center gap-3 shadow-sm animate-fade-in-up">
          <Loader2 className="w-4 h-4 text-brand-600 animate-spin flex-shrink-0" />
          <p className="text-xs text-brand-800 font-semibold">Claim is being processed. Polling for updates…</p>
        </div>
      )}

      {/* Decision confirmed banner */}
      {decisionMade && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3.5 shadow-sm animate-fade-in-up">
          <p className="text-xs font-bold text-green-800">
            ✓ Decision submitted: <span className="font-extrabold">{decisionMade.replace('_', ' ')}</span>
          </p>
        </div>
      )}

      {/* 3-col grid: main | decision */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left: claim data */}
        <div className="xl:col-span-2 space-y-4">
          {/* Patient + Clinical */}
          <div className="grid grid-cols-1 gap-4">
            <PatientInfoCard patient={claim.patient} />
          </div>

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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Evidence Request (if NEED_MORE_INFO triggered) */}
              {claim.evidence_request ? (
                <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black text-amber-900 uppercase tracking-wider">Evidence Request</span>
                    <span className="text-[9px] font-extrabold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                      {claim.evidence_request.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="space-y-1 text-xs">
                    <p className="text-slate-500 font-medium text-[10px] uppercase tracking-wide">Requested</p>
                    <p className="font-extrabold text-slate-900">{claim.evidence_request.requested_evidence}</p>
                    <p className="text-slate-500 font-medium text-[10px] uppercase tracking-wide mt-1">Reason</p>
                    <p className="font-medium text-slate-700">{claim.evidence_request.reason}</p>
                    <p className="text-slate-500 font-medium text-[10px] uppercase tracking-wide mt-1">Status</p>
                    <p className="font-extrabold text-amber-800">
                      {claim.evidence_request.status === 'WAITING_FOR_PROVIDER' ? 'WAITING FOR PROVIDER' : claim.evidence_request.status.replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>
              ) : null}

              {/* Evidence Received (if evidence has been uploaded/received) */}
              {((claim.evidence_request_status === 'RECEIVED' || claim.evidence_response) && claim.evidence_request_status !== 'CLOSED') ? (
                <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3.5 space-y-2 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-black text-emerald-900 uppercase tracking-wider">Evidence Received</span>
                      <span className="text-[9px] font-extrabold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">RECEIVED</span>
                    </div>
                    <div className="text-xs">
                      <p className="text-slate-500 font-medium text-[10px] uppercase tracking-wide">Evidence</p>
                      <p className="font-extrabold text-slate-900">{claim.evidence_response?.evidence || claim.evidence_request?.requested_evidence || 'PT Documentation'}</p>
                      <p className="text-slate-500 font-medium text-[10px] uppercase tracking-wide mt-1">Status</p>
                      <p className="font-extrabold text-emerald-800">RECEIVED</p>
                    </div>
                  </div>
                  <div className="mt-3 pt-2 border-t border-emerald-200/50 flex items-center justify-between">
                    <span className="text-[10px] text-emerald-800 font-bold uppercase tracking-wider">Next Step</span>
                    <span className="text-[9px] font-black bg-emerald-600 text-white px-2 py-0.5 rounded">
                      Agent 1 Re-evaluation
                    </span>
                  </div>
                </div>
              ) : null}
            </div>

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
          {claim.policy_evidence.length > 0 && (
            <PolicyEvidencePanel
              evidence={claim.policy_evidence}
              policyName={claim.policy.policy_name}
              policyId={claim.policy.policy_id}
              portal="insurance"
              onViewPolicy={() => setIsPolicyOpen(true)}
            />
          )}

          {claim.status === 'HUMAN_REVIEW' && (
            <HumanReviewWorkspace claim={claim} portal="insurance" />
          )}

          {/* Missing information list */}
          {claim.missing_information.length > 0 && (
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
              </dl>
            </div>
          )}

        </div>

        {/* Right: Decision Panel + Timeline + policy reference + documents */}
        <div className="space-y-4">
          {claim.status === 'HUMAN_REVIEW' && (
            <DecisionPanel
              claimId={claim.claim_id}
              recommendation={claim.decision?.status}
              reason={claim.decision?.reason}
              onDecisionMade={(d) => {
                setDecisionMade(d);
                fetchClaim();
              }}
            />
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
          policyId={claim.policy.policy_id}
          claim={claim}
        />
      )}
    </div>
  );
}
