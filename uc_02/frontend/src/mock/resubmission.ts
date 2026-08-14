import type { ResubmissionAnalysis } from '../types/resubmission';

// Keyed by claim_id
export const mockResubmissions: Record<string, ResubmissionAnalysis> = {
  'CLM-002': {
    eligible: true,
    resubmission_probability: 0.87,
    recommendation: 'RESUBMIT',
    confidence: 0.91,
    factors: [
      'MRI documentation is now available',
      'Conservative treatment period can be extended to 12+ weeks',
      'Orthopedic specialist referral obtained',
      'Policy criteria are achievable with additional documentation',
    ],
    policy_checks: {
      rejection_reason_corrected: true,
      required_documents_present: true,
      within_submission_window: true,
      max_attempts_exceeded: false,
    },
  },
  'CLM-003': {
    eligible: true,
    resubmission_probability: 0.74,
    recommendation: 'RESUBMIT',
    confidence: 0.78,
    factors: [
      'Lab results can be obtained quickly',
      'Prior imaging available from recent ER visit',
      'Conservative treatment criteria already met',
    ],
    policy_checks: {
      rejection_reason_corrected: false,
      required_documents_present: false,
      within_submission_window: true,
      max_attempts_exceeded: false,
    },
  },
  'CLM-007': {
    eligible: true,
    resubmission_probability: 0.94,
    recommendation: 'RESUBMIT',
    confidence: 0.95,
    factors: [
      'MRI report now provided and confirms indication',
      'Orthopedic specialist evaluation complete',
      'Conservative treatment fully documented at 14 weeks',
      'All policy criteria now satisfied',
    ],
    policy_checks: {
      rejection_reason_corrected: true,
      required_documents_present: true,
      within_submission_window: true,
      max_attempts_exceeded: false,
    },
  },
  // Low probability — don't resubmit
  'CLM-LOW': {
    eligible: false,
    resubmission_probability: 0.15,
    recommendation: "DON'T RESUBMIT",
    confidence: 0.82,
    factors: [
      'Procedure not covered under current plan',
      'Maximum submission attempts exceeded',
      'Policy exclusion applies',
    ],
    policy_checks: {
      rejection_reason_corrected: false,
      required_documents_present: false,
      within_submission_window: false,
      max_attempts_exceeded: true,
    },
  },
  // Human review recommended
  'CLM-MID': {
    eligible: true,
    resubmission_probability: 0.52,
    recommendation: 'HUMAN_REVIEW',
    confidence: 0.6,
    factors: [
      'Some criteria met but borderline case',
      'Clinical complexity warrants human review',
      'Prior approval history mixed',
    ],
    policy_checks: {
      rejection_reason_corrected: true,
      required_documents_present: false,
      within_submission_window: true,
      max_attempts_exceeded: false,
    },
  },
};
