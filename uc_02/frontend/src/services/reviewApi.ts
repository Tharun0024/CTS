import { mockRequest } from './api';
import { getClaimsStore, saveClaimsStore } from './claimsApi';
import type { ReviewItem, ReviewDetails, DecisionPayload } from '../types/claim';
import { mockReviews } from '../mock/reviews';

const LOCAL_STORAGE_KEY = 'authflow_reviews_store';

function loadReviewsStore(): ReviewItem[] {
  const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch (e) {
      console.error('Failed to parse saved reviews', e);
    }
  }
  return [...mockReviews];
}

function saveReviewsStore(store: ReviewItem[]) {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(store));
}

let reviewsStore: ReviewItem[] = loadReviewsStore();

export function getUpdatedReviewsStore(): ReviewItem[] {
  const claims = getClaimsStore();

  // 1. Find all claims with status 'HUMAN_REVIEW'
  const humanReviewClaims = claims.filter(c => c.status === 'HUMAN_REVIEW');

  // 2. Make sure each one has a corresponding review in reviewsStore
  let updated = [...reviewsStore];
  let changed = false;

  humanReviewClaims.forEach(c => {
    const exists = updated.some(r => r.claim_id === c.claim_id);
    if (!exists) {
      // Create a new ReviewItem
      const newReview: ReviewItem = {
        review_id: `REV-${String(updated.length + 1).padStart(3, '0')}`,
        claim_id: c.claim_id,
        hospital: c.hospital ?? 'City General Hospital',
        patient_id: c.patient.patient_id,
        procedure: c.claim.procedure,
        reason_for_review: c.decision?.reason || 'Escalated to human review due to clinical complexity.',
        assigned_at: new Date().toISOString(),
        status: 'PENDING',
        priority: 'HIGH', // Default to HIGH for new escalations
      };
      updated.push(newReview);
      changed = true;
    }
  });

  // 3. For any reviews whose corresponding claim is no longer HUMAN_REVIEW,
  // we can mark their status as COMPLETED.
  updated = updated.map(r => {
    const claim = claims.find(c => c.claim_id === r.claim_id);
    if (claim && claim.status !== 'HUMAN_REVIEW' && r.status !== 'COMPLETED') {
      changed = true;
      return { ...r, status: 'COMPLETED' };
    }
    return r;
  });

  if (changed) {
    reviewsStore = updated;
    saveReviewsStore(reviewsStore);
  }

  return reviewsStore;
}

// GET /api/reviews
export async function getReviews(): Promise<ReviewItem[]> {
  return mockRequest(getUpdatedReviewsStore());
}

// GET /api/reviews/{id}
export async function getReviewDetails(reviewId: string): Promise<ReviewDetails> {
  const reviews = getUpdatedReviewsStore();
  const rev = reviews.find(r => r.review_id === reviewId);
  if (!rev) throw new Error(`Review ${reviewId} not found`);

  // Find the live claim details
  const claims = getClaimsStore();
  const claimDetails = claims.find(c => c.claim_id === rev.claim_id);

  return mockRequest({
    ...rev,
    claim_details: claimDetails || claims[0], // fallback
    ai_recommendation: rev.priority === 'HIGH' ? 'HUMAN_REVIEW' : 'ACCEPT',
    ai_confidence: rev.priority === 'HIGH' ? 0.55 : 0.78,
  });
}

// POST /api/reviews/{id}/decision
export async function submitReviewDecision(
  reviewId: string,
  payload: DecisionPayload
): Promise<{ success: boolean; review_id: string }> {
  const reviews = getUpdatedReviewsStore();
  const idx = reviews.findIndex(r => r.review_id === reviewId);
  if (idx !== -1) {
    reviews[idx] = {
      ...reviews[idx],
      status: 'COMPLETED',
    };
    saveReviewsStore(reviews);

    // Update the corresponding claim in the claimsStore!
    const claimId = reviews[idx].claim_id;
    const claims = getClaimsStore();
    const claimIdx = claims.findIndex(c => c.claim_id === claimId);
    if (claimIdx !== -1) {
      const statusMap: Record<string, any> = {
        ACCEPT: 'ACCEPTED',
        REJECT: 'REJECTED',
        MORE_INFORMATION: 'MORE_INFO',
        HUMAN_REVIEW: 'HUMAN_REVIEW',
      };

      const nextStatus = statusMap[payload.decision] ?? claims[claimIdx].status;

      // Setup evidence request structure if more info is needed
      let nextEvRequest = claims[claimIdx].evidence_request;
      let nextResubStatus = claims[claimIdx].resubmission_status;
      let nextEvRequestStatus = claims[claimIdx].evidence_request_status;

      if (nextStatus === 'MORE_INFO') {
        nextEvRequest = {
          request_id: `EVR-${claimId.replace('CLM-', '')}`,
          requested_evidence: 'Clinical documentation & treatment logs',
          reason: payload.comments || 'Missing documentation required for clinical criteria analysis.',
          status: 'PENDING_PROVIDER_RESPONSE',
        };
        nextResubStatus = 'AWAITING_EVIDENCE';
        nextEvRequestStatus = 'PENDING_PROVIDER_RESPONSE';
      }

      claims[claimIdx] = {
        ...claims[claimIdx],
        status: nextStatus,
        decision: {
          status: payload.decision,
          reason: payload.comments || payload.reason_code.replace(/_/g, ' '),
          reason_code: payload.reason_code,
        },
        evidence_request: nextEvRequest,
        resubmission_status: nextResubStatus,
        evidence_request_status: nextEvRequestStatus,
        updated_at: new Date().toISOString(),
        timeline: [
          ...(claims[claimIdx].timeline ?? []),
          {
            timestamp: new Date().toISOString(),
            event: nextStatus,
            message: `Review queue decision: ${payload.decision}. Reason: ${payload.comments || payload.reason_code}`
          }
        ]
      };
      saveClaimsStore(claims);
    }
  }
  return mockRequest({ success: true, review_id: reviewId }, 600);
}
