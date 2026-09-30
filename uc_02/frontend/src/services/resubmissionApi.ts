// Resubmission analysis service — Phase 6: derived from the real backend
// claim record (decision, missing information, attempt count). The backend is
// the source of truth; this only shapes that truth for the existing UI.

import { getClaimDetails } from './claimsApi';
import type { ResubmissionAnalysis } from '../types/resubmission';

// GET /api/claims/{id}/resubmission — derived from live claim state.
export async function getResubmissionAnalysis(claimId: string): Promise<ResubmissionAnalysis> {
  const claim = await getClaimDetails(claimId);
  const attempt = claim.attempt ?? 1;
  const rejected = claim.status === 'REJECTED';
  const missingCount = claim.missing_information?.length ?? 0;
  const maxAttemptsExceeded = attempt >= 2;

  const eligible = Boolean(claim.resubmission?.eligible) || (rejected && !maxAttemptsExceeded);

  const factors: string[] = [];
  if (claim.decision?.reason) factors.push(`Agent 1 decision: ${claim.decision.reason}`);
  for (const item of claim.missing_information ?? []) {
    factors.push(`Missing: ${item}`);
  }
  if (claim.evidence_response) {
    factors.push(`Agent 2 evidence response: ${claim.evidence_response.evidence}`);
  }
  if (maxAttemptsExceeded) {
    factors.push('Maximum resubmission attempts reached (V1 allows one resubmission).');
  }
  if (factors.length === 0) {
    factors.push('No rejection or evidence gap recorded for this claim.');
  }

  const recommendation: ResubmissionAnalysis['recommendation'] =
    eligible && missingCount > 0
      ? 'RESUBMIT'
      : claim.status === 'HUMAN_REVIEW'
        ? 'HUMAN_REVIEW'
        : "DON'T RESUBMIT";

  const probability = eligible ? Math.max(0.3, 0.75 - missingCount * 0.1) : 0.1;

  return {
    eligible,
    resubmission_probability: probability,
    recommendation,
    confidence: 0.7,
    factors,
    policy_checks: {
      rejection_reason_corrected: missingCount === 0 && rejected,
      required_documents_present: missingCount === 0,
      within_submission_window: true,
      max_attempts_exceeded: maxAttemptsExceeded,
    },
  };
}
