import { mockRequest } from './api';
import { getClaimsStore, saveClaimsStore } from './claimsApi';
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

// GET /api/insurance/claims
export async function getInsuranceClaims(): Promise<InsuranceClaim[]> {
  const store = getClaimsStore();
  return mockRequest(store.map(mapClaimToInsurance));
}

// GET /api/insurance/claims/{id}
export async function getInsuranceClaimDetails(id: string): Promise<ClaimDetails> {
  const store = getClaimsStore();
  const detail = store.find(c => c.claim_id === id);
  if (!detail) throw new Error(`Claim ${id} not found`);
  return mockRequest({ ...detail });
}

// POST /api/insurance/claims/{id}/decision
export async function submitDecision(
  claimId: string,
  payload: DecisionPayload
): Promise<{ success: boolean; claim_id: string; decision: string }> {
  const statusMap: Record<string, InsuranceClaim['status']> = {
    ACCEPT: 'ACCEPTED',
    REJECT: 'REJECTED',
    MORE_INFORMATION: 'MORE_INFO',
    HUMAN_REVIEW: 'HUMAN_REVIEW',
  };

  const store = getClaimsStore();
  const idx = store.findIndex(c => c.claim_id === claimId);
  if (idx !== -1) {
    const nextStatus = statusMap[payload.decision] ?? store[idx].status;

    // Setup evidence request structure if more info is needed (V1 Workflow)
    let nextEvRequest = store[idx].evidence_request;
    let nextResubStatus = store[idx].resubmission_status;
    let nextEvRequestStatus = store[idx].evidence_request_status;

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

    store[idx] = {
      ...store[idx],
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
        ...(store[idx].timeline ?? []),
        {
          timestamp: new Date().toISOString(),
          event: nextStatus,
          message: `Decision submitted by insurance: ${payload.decision}. Reason: ${payload.comments || payload.reason_code}`
        }
      ]
    };
    saveClaimsStore(store);
  }

  return mockRequest({ success: true, claim_id: claimId, decision: payload.decision }, 600);
}
