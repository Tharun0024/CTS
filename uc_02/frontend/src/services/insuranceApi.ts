import { mockRequest } from './api';
import { mockInsuranceClaims } from '../mock/insuranceClaims';
import { mockClaimDetails } from '../mock/claims';
import type { InsuranceClaim, ClaimDetails, DecisionPayload } from '../types/claim';

let insuranceStore: InsuranceClaim[] = [...mockInsuranceClaims];

// GET /api/insurance/claims
export async function getInsuranceClaims(): Promise<InsuranceClaim[]> {
  return mockRequest([...insuranceStore]);
}

// GET /api/insurance/claims/{id}
export async function getInsuranceClaimDetails(id: string): Promise<ClaimDetails> {
  const detail = mockClaimDetails.find(c => c.claim_id === id);
  if (!detail) throw new Error(`Claim ${id} not found`);
  return mockRequest({ ...detail });
}

// POST /api/insurance/claims/{id}/decision
export async function submitDecision(
  claimId: string,
  payload: DecisionPayload
): Promise<{ success: boolean; claim_id: string; decision: string }> {
  // Update in-memory store
  const idx = insuranceStore.findIndex(c => c.claim_id === claimId);
  if (idx !== -1) {
    const statusMap: Record<string, InsuranceClaim['status']> = {
      ACCEPT: 'ACCEPTED',
      REJECT: 'REJECTED',
      MORE_INFORMATION: 'MORE_INFO',
      HUMAN_REVIEW: 'HUMAN_REVIEW',
    };
    insuranceStore[idx] = {
      ...insuranceStore[idx],
      status: statusMap[payload.decision] ?? insuranceStore[idx].status,
      updated_at: new Date().toISOString(),
    };
  }
  return mockRequest({ success: true, claim_id: claimId, decision: payload.decision }, 600);
}
