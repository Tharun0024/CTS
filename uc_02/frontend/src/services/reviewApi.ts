// Review queue API service — Phase 6: wired to the real FastAPI V1 boundary.
// The queue is derived live from backend claim records in HUMAN_REVIEW status;
// review ids are deterministic (REV-{claim_id}). Resolutions go through the
// human-resolution endpoint — frozen V1 semantics: the resolved claim
// re-enters normal Agent 1 routing.

import { getClaimDetails, getClaims, resolveHumanReview } from './claimsApi';
import type { ReviewItem, ReviewDetails, DecisionPayload } from '../types/claim';

// Claim ids resolved during this browser session (backend has no dedicated
// review-status field; a resolved claim simply leaves HUMAN_REVIEW).
const resolvedThisSession = new Set<string>();

export function reviewIdForClaim(claimId: string): string {
  return `REV-${claimId}`;
}

export function claimIdForReview(reviewId: string): string {
  return reviewId.replace(/^REV-/, '');
}

// GET /api/reviews — derived from claims currently in HUMAN_REVIEW.
export async function getReviews(): Promise<ReviewItem[]> {
  const claims = await getClaims();
  const humanReview = claims.filter((claim) => claim.status === 'HUMAN_REVIEW');
  const details = await Promise.all(
    humanReview.map((claim) =>
      getClaimDetails(claim.claim_id).catch(() => null)
    )
  );

  const items: ReviewItem[] = [];
  for (const detail of details) {
    if (!detail) continue;
    const claimId = detail.claim_id;
    const resolved = resolvedThisSession.has(claimId) && detail.status !== 'HUMAN_REVIEW';
    items.push({
      review_id: reviewIdForClaim(claimId),
      claim_id: claimId,
      hospital: detail.hospital ?? 'City General Hospital',
      patient_id: detail.patient.patient_id,
      procedure: detail.claim.procedure,
      reason_for_review:
        (detail.human_review_reasons ?? []).join('; ') ||
        detail.decision?.reason ||
        'Escalated to human review due to clinical complexity.',
      assigned_at: detail.updated_at,
      status: resolved ? 'COMPLETED' : 'PENDING',
      priority: 'HIGH',
    });
  }

  // Resolved claims that left HUMAN_REVIEW remain visible as COMPLETED.
  for (const claimId of resolvedThisSession) {
    if (items.some((item) => item.claim_id === claimId)) continue;
    const detail = await getClaimDetails(claimId).catch(() => null);
    if (!detail) continue;
    items.push({
      review_id: reviewIdForClaim(claimId),
      claim_id: claimId,
      hospital: detail.hospital ?? 'City General Hospital',
      patient_id: detail.patient.patient_id,
      procedure: detail.claim.procedure,
      reason_for_review: detail.decision?.reason || 'Escalated to human review.',
      assigned_at: detail.updated_at,
      status: 'COMPLETED',
      priority: 'HIGH',
    });
  }

  return items;
}

// GET /api/reviews/{id}
export async function getReviewDetails(reviewId: string): Promise<ReviewDetails> {
  const claimId = claimIdForReview(reviewId);
  const detail = await getClaimDetails(claimId);
  const recommendation = detail.decision?.status ?? 'HUMAN_REVIEW';
  return {
    review_id: reviewId,
    claim_id: claimId,
    hospital: detail.hospital ?? 'City General Hospital',
    patient_id: detail.patient.patient_id,
    procedure: detail.claim.procedure,
    reason_for_review:
      (detail.human_review_reasons ?? []).join('; ') ||
      detail.decision?.reason ||
      'Escalated to human review due to clinical complexity.',
    assigned_at: detail.updated_at,
    status: resolvedThisSession.has(claimId) && detail.status !== 'HUMAN_REVIEW'
      ? 'COMPLETED'
      : 'PENDING',
    priority: 'HIGH',
    claim_details: detail,
    ai_recommendation: recommendation,
    // Backend does not expose a calibrated confidence score for human-review
    // escalations; report a neutral value rather than inventing one.
    ai_confidence: 0.5,
  };
}

// POST /api/reviews/{id}/decision — recorded as a human-resolution note; the
// claim re-enters Agent 1 routing (Agent 1 owns final coverage decisions).
export async function submitReviewDecision(
  reviewId: string,
  payload: DecisionPayload
): Promise<{ success: boolean; review_id: string }> {
  const claimId = claimIdForReview(reviewId);
  const note =
    `Human review decision: ${payload.decision} (${payload.reason_code}). ` +
    (payload.comments || payload.reason_code.replace(/_/g, ' '));
  resolvedThisSession.add(claimId);
  await resolveHumanReview(claimId, note);
  return { success: true, review_id: reviewId };
}
