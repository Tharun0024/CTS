export interface ResubmissionAnalysis {
  eligible?: boolean;
  resubmission_probability: number; // 0–1
  recommendation: 'RESUBMIT' | "DON'T RESUBMIT" | 'HUMAN_REVIEW';
  confidence: number;
  factors: string[];
  policy_checks?: {
    rejection_reason_corrected: boolean;
    required_documents_present: boolean;
    within_submission_window: boolean;
    max_attempts_exceeded: boolean;
  };
}
