import type { InsuranceClaim } from '../types/claim';
import { mockClaimDetails } from './claims';

const priorityByStatus: Record<string, InsuranceClaim['priority']> = {
  HUMAN_REVIEW: 'HIGH',
  MORE_INFO: 'MEDIUM',
  REJECTED: 'MEDIUM',
  UNDER_REVIEW: 'MEDIUM',
  PROCESSING: 'LOW',
  SUBMITTED_AGAIN: 'LOW',
  ACCEPTED: 'LOW',
};

export const mockInsuranceClaims: InsuranceClaim[] = mockClaimDetails.map((detail) => ({
  claim_id: detail.claim_id,
  hospital: detail.hospital ?? 'Unknown Hospital',
  patient_id: detail.patient.patient_id,
  procedure: detail.claim.procedure,
  procedure_code: detail.claim.procedure_code,
  diagnosis_codes: detail.claim.diagnosis_codes,
  service_date: detail.claim.service_date,
  status: detail.status,
  attempt: detail.attempt,
  submission_history: detail.submission_history,
  current_status: detail.reevaluation_status ?? detail.status,
  resubmission_status: detail.resubmission_status,
  evidence_request_status: detail.evidence_request_status,
  agent2_result: detail.agent2_result,
  evidence_request: detail.evidence_request,
  evidence_response: detail.evidence_response,
  submitted_at: detail.submitted_at,
  updated_at: detail.updated_at,
  priority: priorityByStatus[detail.status] ?? 'LOW',
}));
