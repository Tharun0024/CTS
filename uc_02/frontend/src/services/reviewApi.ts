import { mockRequest } from './api';
import { mockReviews, mockReviewDetails } from '../mock/reviews';
import type { ReviewItem, ReviewDetails, DecisionPayload } from '../types/claim';

let reviewsStore: ReviewItem[] = [...mockReviews];

// GET /api/reviews
export async function getReviews(): Promise<ReviewItem[]> {
  return mockRequest([...reviewsStore]);
}

// GET /api/reviews/{id}
export async function getReviewDetails(reviewId: string): Promise<ReviewDetails> {
  const detail = mockReviewDetails.find(r => r.review_id === reviewId);
  if (!detail) throw new Error(`Review ${reviewId} not found`);
  return mockRequest({ ...detail });
}

// POST /api/reviews/{id}/decision
export async function submitReviewDecision(
  reviewId: string,
  _payload: DecisionPayload
): Promise<{ success: boolean; review_id: string }> {
  const idx = reviewsStore.findIndex(r => r.review_id === reviewId);
  if (idx !== -1) {
    reviewsStore[idx] = {
      ...reviewsStore[idx],
      status: 'COMPLETED',
    };
  }
  return mockRequest({ success: true, review_id: reviewId }, 600);
}
