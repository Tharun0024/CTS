// Review queue API service — Phase 6: wired to the real FastAPI V1 boundary.
// The queue is derived live from backend claim records in HUMAN_REVIEW status;
// review ids are deterministic (REV-{claim_id}).
//
// Phase 4: the queue state is derived ONLY from the authoritative backend
// record. A claim is PENDING while its live status is HUMAN_REVIEW; it is
// COMPLETED once the hospital's resolution is applied (human_resolution is
// persisted and the claim left HUMAN_REVIEW). No frontend-only session state
// participates — both portals converge on the same persisted record, and
// insurance never resolves (read-only).

import { getClaimDetails, getClaims } from './claimsApi';
import type { ReviewItem, ReviewDetails } from '../types/claim';

export function reviewIdForClaim(claimId: string): string {
  return `REV-${claimId}`;
}

export function claimIdForReview(reviewId: string): string {
  return reviewId.replace(/^REV-/, '');
}

function reviewStatus(detail: { status: string; human_resolution?: string | null }): 'PENDING' | 'COMPLETED' {
  if (detail.status !== 'HUMAN_REVIEW' && detail.human_resolution) return 'COMPLETED';
  return 'PENDING';
}

// GET /api/reviews — derived from live backend claim records: claims currently
// in HUMAN_REVIEW are PENDING; claims carrying a persisted human resolution
// (already left HUMAN_REVIEW) stay visible as COMPLETED.
export async function getReviews(portal?: 'hospital' | 'insurance'): Promise<ReviewItem[]> {
  const claims = await getClaims();
  const details = await Promise.all(
    claims.map((claim) => getClaimDetails(claim.claim_id).catch(() => null))
  );

  const items: ReviewItem[] = [];
  for (const detail of details) {
    if (!detail) continue;
    const pending = detail.status === 'HUMAN_REVIEW';
    const resolved = !pending && !!detail.human_resolution;
    if (!pending && !resolved) continue;

    // Filter by portal/flow type
    if (portal === 'insurance' && !detail.human_verification_pending) continue;
    if (portal === 'hospital' && detail.human_verification_pending) continue;

    items.push({
      review_id: reviewIdForClaim(detail.claim_id),
      claim_id: detail.claim_id,
      hospital: detail.hospital ?? 'City General Hospital',
      patient_id: detail.patient.patient_id,
      procedure: detail.claim.procedure,
      reason_for_review:
        (detail.human_review_reasons ?? []).join('; ') ||
        detail.decision?.reason ||
        'Escalated to human review due to clinical complexity.',
      assigned_at: detail.updated_at,
      status: reviewStatus(detail),
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
    status: reviewStatus(detail),
    priority: 'HIGH',
    claim_details: detail,
    ai_recommendation: recommendation,
    // Backend does not expose a calibrated confidence score for human-review
    // escalations; report a neutral value rather than inventing one.
    ai_confidence: 0.5,
  };
}

export function clearReviewsCache(): void {
  // Phase 4: the queue holds no frontend-only state anymore — everything is
  // re-derived from the backend on every fetch. Kept as a no-op for the
  // existing call sites (hospital resolution panel, simulation controls).
}
