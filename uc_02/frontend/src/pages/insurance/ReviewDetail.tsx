import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { ClinicalInfoCard } from '../../components/shared/ClinicalInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getReviewDetails } from '../../services/reviewApi';
import { HumanReviewWorkspace } from '../../components/shared/HumanReviewWorkspace';
import { PriorAuthStatusCard } from '../../components/shared/PriorAuthStatusCard';
import type { ReviewDetails } from '../../types/claim';
import { ArrowLeft, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { usePolling, isTerminalStatus } from '../../services/polling';
import { decisionLabel } from '../../utils/decisionHumanizer';

export function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [review, setReview] = useState<ReviewDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback((showLoading = true) => {
    if (!id) return;
    if (showLoading) { setLoading(true); setError(''); }
    getReviewDetails(id)
      .then(setReview)
      .catch(() => { if (showLoading) setError('Failed to load review details.'); })
      .finally(() => { if (showLoading) setLoading(false); });
  }, [id]);

  useEffect(() => { fetchData(true); }, [fetchData]);

  // Phase 4: same backend-driven polling pattern as the other detail pages —
  // the insurance view converges on the hospital's resolution without any
  // frontend-only state.
  usePolling(
    () => getReviewDetails(id!),
    (data) => setReview(data),
    (data) => isTerminalStatus(data.claim_details.status),
    5000,
    !!id && !!review && !isTerminalStatus(review.claim_details.status)
  );

  if (loading) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <LoadingState message="Loading review…" fullPage />
    </div>
  );

  if (error || !review) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ErrorState message={error || 'Review not found.'} onRetry={() => fetchData(true)} />
    </div>
  );

  const claim = review.claim_details;

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      {/* Back */}
      <button
        onClick={() => navigate('/insurance/review')}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-brand-600 mb-3 transition-colors group animate-fade-in-up"
      >
        <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
        Back to Review Queue
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2.5 mb-4 animate-fade-in-up stagger-1">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg md:text-xl font-bold text-slate-900 leading-none">{review.review_id}</h1>
            <span className="text-[10px] font-extrabold bg-red-55 bg-red-50 text-red-700 px-1.5 py-0.5 rounded border border-red-200">
              {review.priority}
            </span>
          </div>
          <p className="text-slate-600 text-xs mt-1 font-semibold">{review.procedure}</p>
          <p className="text-[11px] text-slate-400 mt-0.5 font-medium">Claim: {review.claim_id} · {review.hospital}</p>
        </div>
      </div>

      {/* Reason for review banner */}
      <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg p-3.5 flex items-start gap-2.5 shadow-sm animate-fade-in-up">
        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-xs font-bold text-amber-900 uppercase tracking-wide">Reason for Human Review</p>
          <p className="text-xs text-amber-800 mt-0.5 font-medium">{review.reason_for_review}</p>
        </div>
      </div>



      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left: claim data */}
        <div className="xl:col-span-2 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <PatientInfoCard patient={claim.patient} />
            <ClinicalInfoCard claim={claim.claim} />
          </div>

          {/* Phase 4: persisted Phase 1 prior-auth pre-check (same authoritative record) */}
          <PriorAuthStatusCard claim={claim} portal="insurance" />

          {claim.policy_evidence.length > 0 && (
            <PolicyEvidencePanel
              evidence={claim.policy_evidence}
              policyName={claim.policy.policy_name}
              policyId={claim.policy.policy_id}
              portal="insurance"
            />
          )}

          {claim.status === 'HUMAN_REVIEW' && (
            <HumanReviewWorkspace claim={claim} portal="insurance" />
          )}

          {claim.missing_information.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3.5 shadow-sm animate-fade-in-up">
              <h3 className="text-xs font-bold text-amber-905 uppercase tracking-wide mb-2">Missing Information</h3>
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
        </div>

        {/* Right: human review panel + timeline */}
        <div className="space-y-4">
          {/* Phase 4: the pending panel is gated on the live backend status so a
              stale HUMAN_REVIEW hold can never reappear after the hospital
              resolves; resolved claims show the terminal decision instead. */}
          {claim.status === 'HUMAN_REVIEW' ? (
            claim.agent2_invoked ? (
              <div className="bg-amber-50 border border-amber-250 rounded-2xl p-4.5 text-center shadow-sm animate-fade-in-up">
                <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                <p className="text-xs font-black text-amber-900 uppercase tracking-wider">Provider/Hospital Resolution Pending</p>
                <p className="text-[11px] text-amber-700 mt-1.5 font-semibold leading-relaxed">
                  This claim is held for provider evidence release consent. Waiting for hospital resolution.
                </p>
              </div>
            ) : (
              <div className="bg-blue-50 border border-blue-250 rounded-2xl p-4.5 text-center shadow-sm animate-fade-in-up">
                <AlertTriangle className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                <p className="text-xs font-black text-blue-900 uppercase tracking-wider">Hospital Clinical Resolution Pending</p>
                <p className="text-[11px] text-blue-700 mt-1.5 font-semibold leading-relaxed">
                  This claim requires manual clinical review and resolution by the hospital provider. The insurance portal is read-only.
                </p>
              </div>
            )
          ) : (
            <div className={`rounded-2xl border p-4.5 text-center shadow-sm animate-fade-in-up ${claim.status === 'ACCEPTED' ? 'bg-emerald-50 border-emerald-250' : 'bg-red-50 border-red-250'}`}>
              {claim.status === 'ACCEPTED'
                ? <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                : <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />}
              <p className="text-xs font-black uppercase tracking-wider mb-1 text-slate-900">
                Final Decision: {decisionLabel(claim.decision?.status ?? claim.status)}
              </p>
              <p className="text-[11px] text-slate-600 font-semibold leading-relaxed">
                Resolved by the hospital through the authoritative human-resolution workflow.
              </p>
              {claim.human_resolution && (
                <p className="text-[11px] text-slate-700 font-medium bg-white border border-slate-200 rounded-lg p-2 mt-2 text-left leading-relaxed whitespace-pre-wrap">
                  {claim.human_resolution}
                </p>
              )}
            </div>
          )}
          {claim.timeline && <ClaimTimeline events={claim.timeline} />}
        </div>
      </div>
    </div>
  );
}
