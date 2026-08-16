// Insurance-side API service — Phase 6: wired to the real FastAPI V1 boundary.
// The insurer portal reads the same backend claim records the hospital sees;
// the backend is the single source of truth. Human review decisions are
// recorded via the human-resolution endpoint (frozen V1 semantics: the claim
// re-enters normal Agent 1 routing — humans never fabricate final outcomes).

import { getClaimDetails, getClaims, resolveHumanReview } from './claimsApi';
import type { InsuranceClaim, ClaimDetails, DecisionPayload } from '../types/claim';

const priorityByStatus: Record<string, InsuranceClaim['priority']> = {
  HUMAN_REVIEW: 'HIGH',
  MORE_INFO: 'MEDIUM',
  REJECTED: 'MEDIUM',
  UNDER_REVIEW: 'MEDIUM',
  PROCESSING: 'LOW',
  SUBMITTED_AGAIN: 'LOW',
  ACCEPTED: 'LOW',
};

function mapClaimToInsurance(detail: ClaimDetails): InsuranceClaim {
  return {
    claim_id: detail.claim_id,
    hospital: detail.hospital ?? 'City General Hospital',
    patient_id: detail.patient.patient_id,
    procedure: detail.claim.procedure,
    procedure_code: detail.claim.procedure_code,
    diagnosis_codes: detail.claim.diagnosis_codes,
    service_date: detail.claim.service_date,
    status: detail.status,
    attempt: detail.attempt ?? 1,
    submission_history: detail.submission_history ?? [],
    current_status: detail.reevaluation_status ?? detail.status,
    resubmission_status: detail.resubmission_status ?? 'NOT_REQUIRED',
    evidence_request_status: detail.evidence_request_status ?? 'CLOSED',
    agent2_result: detail.agent2_result ?? null,
    evidence_request: detail.evidence_request ?? null,
    evidence_response: detail.evidence_response ?? null,
    submitted_at: detail.submitted_at,
    updated_at: detail.updated_at,
    priority: priorityByStatus[detail.status] ?? 'LOW',
  };
}

// GET /api/insurance/claims — derived from the real claim list.
export async function getInsuranceClaims(): Promise<InsuranceClaim[]> {
  const claims = await getClaims();
  const details = await Promise.all(
    claims.map((claim) =>
      getClaimDetails(claim.claim_id).catch(() => null)
    )
  );
  return details
    .filter((detail): detail is ClaimDetails => detail !== null)
    .map(mapClaimToInsurance);
}

// GET /api/insurance/claims/{id}
export async function getInsuranceClaimDetails(id: string): Promise<ClaimDetails> {
  return getClaimDetails(id);
}

// POST /api/insurance/claims/{id}/decision — recorded as a human-resolution
// note; the backend re-runs Agent 1 routing (frozen V1 authority model).
export async function submitDecision(
  claimId: string,
  payload: DecisionPayload
): Promise<{ success: boolean; claim_id: string; decision: string }> {
  const note =
    `Human review decision: ${payload.decision} (${payload.reason_code}). ` +
    (payload.comments || payload.reason_code.replace(/_/g, ' '));
  await resolveHumanReview(claimId, note);
  return { success: true, claim_id: claimId, decision: payload.decision };
}
