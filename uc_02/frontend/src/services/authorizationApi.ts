// Authorizations service — gap 1 fix: derived from the REAL backend claims.
// V1 has no dedicated authorizations endpoint; every prior-authorization
// request IS a claim in the backend, so this view is a projection of the real
// claims dataset (GET /api/claims + /api/simulation/claims). Fields with no
// backend source (auth_number, expiry_date) are left empty rather than
// fabricated, and status writes are impossible — the backend owns status.

import { getClaims, getClaimDetails } from './claimsApi';
import type { Claim, ClaimStatus } from '../types/claim';

export interface Authorization {
  auth_id: string;
  claim_id?: string;
  patient_id: string;
  patient_name: string;
  provider_id: string;
  provider_name: string;
  payer: string;
  procedure: string;
  procedure_code: string;
  service_date: string;
  requested_at: string;
  updated_at: string;
  status: 'Pending' | 'Approved' | 'Denied' | 'Expired' | 'In Review' | 'Cancelled';
  auth_number?: string;
  expiry_date?: string;
  notes?: string;
  priority: 'Urgent' | 'Standard' | 'Elective';
}

// Claim lifecycle status → authorization display status.
function mapStatus(status: ClaimStatus): Authorization['status'] {
  switch (status) {
    case 'ACCEPTED':
      return 'Approved';
    case 'REJECTED':
      return 'Denied';
    case 'HUMAN_REVIEW':
      return 'In Review';
    default:
      return 'Pending';
  }
}

function toAuthorization(claim: Claim): Authorization {
  return {
    auth_id: claim.claim_id,
    claim_id: claim.claim_id,
    patient_id: claim.patient_id,
    // The backend summary carries no patient name — show the real patient id.
    patient_name: claim.patient_id,
    provider_id: claim.provider_id ?? claim.hospital ?? '',
    provider_name: claim.hospital ?? claim.provider_id ?? 'N/A',
    payer: claim.payer ?? 'Unknown payer',
    procedure: claim.procedure,
    procedure_code: claim.procedure_code,
    service_date: claim.service_date,
    requested_at: claim.submitted_at,
    updated_at: claim.updated_at,
    status: mapStatus(claim.status),
    // No auth number / expiry exists in V1 backend data — left undefined.
    priority: 'Standard',
  };
}

export async function getAuthorizations(): Promise<Authorization[]> {
  const claims = await getClaims();
  return claims.map(toAuthorization);
}

export async function getAuthorization(id: string): Promise<Authorization> {
  const details = await getClaimDetails(id);
  return {
    auth_id: details.claim_id,
    claim_id: details.claim_id,
    patient_id: details.patient.patient_id,
    patient_name: details.patient.name ?? details.patient.patient_id,
    provider_id: details.claim.provider_id ?? '',
    provider_name: details.hospital ?? details.claim.provider_id ?? 'N/A',
    payer: details.policy.payer,
    procedure: details.claim.procedure,
    procedure_code: details.claim.procedure_code,
    service_date: details.claim.service_date,
    requested_at: details.submitted_at,
    updated_at: details.updated_at,
    status: mapStatus(details.status),
    priority: 'Standard',
  };
}

// The backend owns authorization/claim status in V1 — there is no write
// endpoint for it. Kept for compatibility; always rejects honestly.
export async function updateAuthorizationStatus(
  id: string,
  _status: Authorization['status'],
  _auth_number?: string
): Promise<Authorization> {
  throw new Error(
    `Authorization ${id}: status is decided by the payer workflow in the backend and cannot be changed from the UI.`
  );
}
