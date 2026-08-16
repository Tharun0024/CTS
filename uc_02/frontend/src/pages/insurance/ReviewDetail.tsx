import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { ClinicalInfoCard } from '../../components/shared/ClinicalInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { HumanReviewPanel } from '../../components/insurance/HumanReviewPanel';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getReviewDetails } from '../../services/reviewApi';
import type { ReviewDetails } from '../../types/claim';
import { ArrowLeft, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [review, setReview] = useState<ReviewDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true); setError('');
    getReviewDetails(id)
      .then(setReview)
      .catch(() => setError('Failed to load review details.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  if (loading) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <LoadingState message="Loading review…" fullPage />
    </div>
  );

  if (error || !review) return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ErrorState message={error || 'Review not found.'} onRetry={fetchData} />
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

      {done && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3.5 shadow-sm animate-fade-in-up">
          <p className="text-xs font-bold text-green-800">✓ Decision submitted — this review is now complete.</p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left: claim data */}
        <div className="xl:col-span-2 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <PatientInfoCard patient={claim.patient} />
            <ClinicalInfoCard claim={claim.claim} />
          </div>

          {claim.policy_evidence.length > 0 && (
            <PolicyEvidencePanel
              evidence={claim.policy_evidence}
              policyName={claim.policy.policy_name}
              policyId={claim.policy.policy_id}
              portal="insurance"
            />
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
          {!done && (
            <HumanReviewPanel
              reviewId={review.review_id}
              aiRecommendation={review.ai_recommendation}
              aiConfidence={review.ai_confidence}
              onDecisionMade={() => setDone(true)}
            />
          )}
          {claim.timeline && <ClaimTimeline events={claim.timeline} />}
        </div>
      </div>
    </div>
  );
}
