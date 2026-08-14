import { mockRequest } from './api';
import { mockClaimDetails } from '../mock/claims';
import type { Claim, ClaimDetails, CreateClaimPayload } from '../types/claim';

// Mutable in-memory state for the current session
let claimsStore: ClaimDetails[] = [...mockClaimDetails];

// GET /api/claims
export async function getClaims(): Promise<Claim[]> {
  const flat = claimsStore.map(cd => ({
    claim_id: cd.claim_id,
    patient_id: cd.patient.patient_id,
    hospital: cd.hospital,
    procedure: cd.claim.procedure,
    procedure_code: cd.claim.procedure_code,
    diagnosis_codes: cd.claim.diagnosis_codes,
    service_date: cd.claim.service_date,
    status: cd.status,
    submitted_at: cd.submitted_at,
    updated_at: cd.updated_at,
  }));
  return mockRequest(flat as Claim[]);
}

// GET /api/claims/{id}
export async function getClaimDetails(id: string): Promise<ClaimDetails> {
  const detail = claimsStore.find(c => c.claim_id === id);
  if (!detail) throw new Error(`Claim ${id} not found`);
  return mockRequest({ ...detail });
}

// POST /api/claims
export async function createClaim(payload: CreateClaimPayload): Promise<ClaimDetails> {
  const newId = `CLM-${String(claimsStore.length + 1).padStart(3, '0')}`;
  
  const missing: string[] = [];
  if (!payload.patient_id) missing.push('Patient Identification');
  if (!payload.procedure) missing.push('Procedure Details');
  if (!payload.procedure_code) missing.push('Procedure Code');
  if (!payload.diagnosis_codes || payload.diagnosis_codes.length === 0) missing.push('Diagnosis Codes');
  if (!payload.service_date) missing.push('Service Date');
  if (!payload.policy_id) missing.push('Policy/Payer Info');

  const newClaim: ClaimDetails = {
    claim_id: newId,
    patient: { 
      patient_id: payload.patient_id || 'PAT-UNSPECIFIED', 
      age: 0, 
      gender: 'Unknown' 
    },
    claim: {
      procedure: payload.procedure || 'Unspecified Procedure',
      procedure_code: payload.procedure_code || 'N/A',
      diagnosis_codes: payload.diagnosis_codes ?? [],
      service_date: payload.service_date || new Date().toISOString().split('T')[0],
      provider_id: payload.provider_id || '',
    },
    policy: { 
      payer: payload.payer || 'Unspecified Payer', 
      policy_id: payload.policy_id || 'N/A', 
      policy_name: `${payload.payer || 'Unspecified'} Policy` 
    },
    decision: missing.length > 0 ? {
      status: 'MORE_INFORMATION',
      reason: 'Automated policy analysis identified missing clinical or patient information required for review.',
    } : null,
    policy_evidence: [],
    missing_information: missing,
    resubmission: { eligible: missing.length > 0, status: 'SUBMITTED' },
    status: missing.length > 0 ? 'MORE_INFO' : 'SUBMITTED',
    submitted_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    hospital: 'City General Hospital',
    documents: [],
    timeline: [
      { timestamp: new Date().toISOString(), event: 'SUBMITTED', message: 'Claim submitted' },
      ...(missing.length > 0 ? [{
        timestamp: new Date().toISOString(),
        event: 'MORE_INFO',
        message: 'Status changed to More Info Needed due to missing fields: ' + missing.join(', ')
      }] : [])
    ],
  };
  
  claimsStore = [newClaim, ...claimsStore];

  // Simulate async status transition only if no missing fields, or keep as MORE_INFO if missing
  if (missing.length === 0) {
    setTimeout(() => {
      const idx = claimsStore.findIndex(c => c.claim_id === newId);
      if (idx !== -1) {
        claimsStore[idx] = {
          ...claimsStore[idx],
          status: 'PROCESSING',
          updated_at: new Date().toISOString(),
          timeline: [
            ...(claimsStore[idx].timeline ?? []),
            { timestamp: new Date().toISOString(), event: 'PROCESSING', message: 'Claim transitioned to processing' }
          ]
        };
      }
    }, 2000);
  }

  return mockRequest(newClaim, 600);
}

// POST /api/claims/{id}/resubmit
export async function resubmitClaim(id: string): Promise<{ success: boolean; claim_id: string }> {
  const idx = claimsStore.findIndex(c => c.claim_id === id);
  if (idx !== -1) {
    claimsStore[idx] = {
      ...claimsStore[idx],
      status: 'SUBMITTED_AGAIN',
      updated_at: new Date().toISOString(),
      timeline: [
        ...(claimsStore[idx].timeline ?? []),
        { timestamp: new Date().toISOString(), event: 'SUBMITTED_AGAIN', message: 'Claim resubmitted' },
      ],
    };
  }
  return mockRequest({ success: true, claim_id: id }, 500);
}

// Export store accessor (used by polling)
export function getClaimsStore() {
  return claimsStore;
}
