// Claims API service — Phase 6: wired to the real FastAPI V1 boundary.
// The backend is the single source of truth for decision, status, versions,
// evidence, timeline and resubmissions; naming differences are reconciled in
// backendAdapter.ts at this service/type boundary only.

import { apiFetch } from './api';
import type { BackendRecord, BackendSummary } from './backendAdapter';
import { toClaimDetails, toClaimSummary } from './backendAdapter';
import type { Claim, ClaimDetails, CreateClaimPayload } from '../types/claim';

// Session cache of the most recently fetched backend snapshots. Read-only
// convenience for components that previously read the localStorage mock
// store; never authoritative — the backend always is.
const lastDetails = new Map<string, ClaimDetails>();

// GET /api/claims (+ /api/simulation/claims for simulation-scoped patients)
export async function getClaims(): Promise<Claim[]> {
  const [apiClaims, simClaims] = await Promise.all([
    apiFetch<BackendSummary[]>('/claims'),
    apiFetch<BackendSummary[]>('/simulation/claims').catch(() => [] as BackendSummary[]),
  ]);
  const seen = new Set<string>();
  const merged: Claim[] = [];
  for (const summary of [...apiClaims, ...simClaims]) {
    if (!summary || seen.has(summary.claim_id)) continue;
    seen.add(summary.claim_id);
    merged.push(toClaimSummary(summary));
  }
  return merged;
}

// GET /api/claims/{id} — falls back to the owning simulation's real
// ClaimService record for simulation-scoped claims.
export async function getClaimDetails(id: string): Promise<ClaimDetails> {
  let record: BackendRecord | null = null;
  try {
    record = await apiFetch<BackendRecord>(`/claims/${encodeURIComponent(id)}`);
  } catch (error) {
    if ((error as { status?: number }).status !== 404) throw error;
  }
  if (!record) {
    record = await apiFetch<BackendRecord>(
      `/simulation/claims?claim_id=${encodeURIComponent(id)}`
    );
  }
  const details = toClaimDetails(record);
  lastDetails.set(id, details);
  return details;
}

// POST /api/claims — runs the REAL V1 pipeline end-to-end.
export async function createClaim(payload: CreateClaimPayload): Promise<ClaimDetails> {
  const record = await apiFetch<BackendRecord>('/claims', {
    method: 'POST',
    body: JSON.stringify({
      patient_id: payload.patient_id || undefined,
      payer: payload.payer || undefined,
      policy_id: payload.policy_id || undefined,
      procedure_code: payload.procedure_code || undefined,
      procedure: payload.procedure || undefined,
      diagnosis_codes: payload.diagnosis_codes ?? [],
      service_date: payload.service_date || undefined,
      provider_id: payload.provider_id || undefined,
    }),
  });
  const details = toClaimDetails(record);
  lastDetails.set(details.claim_id, details);
  return details;
}

// V1 frozen routing: REQUEST_MORE_INFORMATION automatically routes to Agent 2
// recovery and re-evaluation — there is no separate manual resubmission step.
// This keeps the existing call sites honest by re-reading the backend state.
export async function resubmitClaim(id: string): Promise<{ success: boolean; claim_id: string }> {
  await getClaimDetails(id);
  return { success: true, claim_id: id };
}

// POST /api/claims/{id}/provider-decision — provider ACCEPT/DECLINE consent
// on Agent2-recovered evidence (control-plane record + audit trail).
export async function postProviderDecision(
  claimId: string,
  decision: 'ACCEPT' | 'DECLINE',
  reason?: string,
  evidenceIds: string[] = []
): Promise<{ decision_id: string; decision: 'ACCEPT' | 'DECLINE' }> {
  return apiFetch(`/claims/${encodeURIComponent(claimId)}/provider-decision`, {
    method: 'POST',
    body: JSON.stringify({ decision, reason: reason ?? null, evidence_ids: evidenceIds }),
  });
}

// GET /api/claims/{id}/provider-decisions
export async function getProviderDecisions(claimId: string): Promise<unknown[]> {
  const body = await apiFetch<{ provider_decisions: unknown[] }>(
    `/claims/${encodeURIComponent(claimId)}/provider-decisions`
  );
  return body.provider_decisions;
}

// POST /api/claims/{id}/human-resolution — resolve a HUMAN_REVIEW hold; the
// claim re-enters normal Agent 1 routing afterwards (frozen V1 semantics).
// Phase 3: ONLY the hospital portal may resolve; resolved_by marks the caller
// (the backend rejects any non-hospital resolver).
export async function resolveHumanReview(
  claimId: string,
  resolutionNote: string
): Promise<ClaimDetails> {
  const record = await apiFetch<BackendRecord>(
    `/claims/${encodeURIComponent(claimId)}/human-resolution`,
    {
      method: 'POST',
      body: JSON.stringify({ resolution_note: resolutionNote, resolved_by: 'hospital' }),
    }
  );
  const details = toClaimDetails(record);
  lastDetails.set(claimId, details);
  return details;
}

// Legacy accessors kept for compatibility: now read-only views over the last
// fetched backend snapshots (writes are no-ops — the backend owns the data).
export function getClaimsStore(): ClaimDetails[] {
  return [...lastDetails.values()];
}

export function saveClaimsStore(_store: ClaimDetails[]): void {
  // Intentional no-op: claim state lives in the backend, not in the browser.
}

export async function getPolicyDetails(policyId: string): Promise<any> {
  return apiFetch<any>(`/policies/${encodeURIComponent(policyId)}`);
}

export function clearClaimsCache(): void {
  lastDetails.clear();
}

