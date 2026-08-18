// Claim lifecycle status
export type ClaimStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'PROCESSING'
  | 'UNDER_REVIEW'
  | 'PENDING_REVIEW'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'MORE_INFO'
  | 'HUMAN_REVIEW'
  | 'RESUBMISSION_CHECK'
  | 'SUBMITTED_AGAIN';

// Decision outcome (from insurance/system)
export type DecisionStatus = 'ACCEPT' | 'REJECT' | 'MORE_INFORMATION' | 'HUMAN_REVIEW';
export type Agent2ResultStatus = 'RELEASED' | 'ESCALATED_TO_HUMAN';
export type EvidenceRequestStatus = 'PENDING_PROVIDER_RESPONSE' | 'WAITING_FOR_PROVIDER' | 'RECEIVED' | 'UNDER_AGENT2_REVIEW' | 'CLOSED';
export type ResubmissionStatus = 'NOT_REQUIRED' | 'AWAITING_EVIDENCE' | 'RESUBMITTED' | 'UNDER_RE_EVALUATION';

export interface SubmissionAttempt {
  attempt: number;
  submitted_at: string;
  status: ClaimStatus;
  note: string;
}

export interface EvidenceRequestSummary {
  request_id: string;
  requested_evidence: string;
  reason: string;
  status: EvidenceRequestStatus;
}

export interface EvidenceResponseSummary {
  evidence: string;
  decision: Agent2ResultStatus | 'RELEASED' | 'ESCALATED';
  status: 'SENT_TO_PAYER' | 'RECEIVED' | 'ESCALATED';
  responded_at?: string;
}

export interface Claim {
  claim_id: string;
  patient_id: string;
  hospital?: string;
  procedure: string;
  procedure_code: string;
  diagnosis_codes: string[];
  service_date: string;
  provider_id?: string;
  payer?: string;
  policy_id?: string;
  status: ClaimStatus;
  attempt?: number;
  submission_history?: SubmissionAttempt[];
  evidence_request_status?: EvidenceRequestStatus;
  resubmission_status?: ResubmissionStatus;
  agent2_result?: Agent2ResultStatus | null;
  evidence_request?: EvidenceRequestSummary | null;
  evidence_response?: EvidenceResponseSummary | null;
  submitted_at: string;
  updated_at: string;
}

export interface PolicyEvidenceItem {
  criterion?: string;
  patient_value?: string;
  status?: 'MET' | 'NOT_MET';
  source?: string;
  evidence_id?: string;
  evidence_key?: string;
  content_reference?: string;
  source_record_id?: string;
  event_date?: string;
  provenance?: string;
  sensitive?: boolean;
  sensitivity_reason?: string | null;
}

export interface ClaimDecision {
  status: DecisionStatus;
  reason: string;
  reason_code?: string;
  comments?: string;
  criteria_results?: Record<string, boolean>;
  criteria_evaluations?: Record<string, any>;
  referenced_evidence_ids?: string[];
  criterion_assessments?: Record<string, any>;
  // Phase 2: informational-only Agent1 decision confidence (never changes the decision).
  confidence_score?: number | null;
  confidence_level?: string | null;
  confidence_factors?: string[];
}

export interface ClaimDetails {
  claim_id: string;
  patient: {
    patient_id: string;
    age: number;
    gender: string;
    name?: string;
    dob?: string;
    address?: string;
    contact?: string;
    relationship?: string;
    policy_holder?: string;
  };
  claim: {
    procedure: string;
    procedure_code: string;
    diagnosis_codes: string[];
    service_date: string;
    provider_id?: string;
  };
  policy: {
    payer: string;
    policy_id: string;
    policy_name: string;
  };
  decision: ClaimDecision | null;
  policy_evidence: PolicyEvidenceItem[];
  missing_information: string[];
  resubmission: {
    eligible: boolean;
    status: string;
  };
  status: ClaimStatus;
  submitted_at: string;
  updated_at: string;
  hospital?: string;
  documents?: DocumentRef[];
  timeline?: TimelineEvent[];
  attempt?: number;
  submission_history?: SubmissionAttempt[];
  evidence_request?: EvidenceRequestSummary | null;
  evidence_response?: EvidenceResponseSummary | null;
  evidence_request_status?: EvidenceRequestStatus;
  resubmission_status?: ResubmissionStatus;
  agent2_result?: Agent2ResultStatus | null;
  reevaluation_status?: string | null;
  // ---- Live backend record fields (Phase 6; set by the service adapter) ----
  workflow_state?: string;
  claim_version?: number;
  agent2_invoked?: boolean;
  resubmissions?: number;
  human_review_reasons?: string[];
  recovery_result?: RecoveryResult | null;
  versions?: ClaimVersion[];
  provider_decisions?: ProviderDecisionRecord[];
  simulation_id?: string;
  // Phase 3: human cross-verification of an Agent 1 REJECT. The claim stays
  // in HUMAN_REVIEW (never REJECTED) until the hospital resolves it.
  human_verification_pending?: boolean;
  human_resolution?: string | null;
  original_rejection?: OriginalRejection | null;
  // Phase 1: deterministic prior-auth pre-check outcome (display-only).
  prior_auth_precheck?: {
    requires_prior_auth?: boolean;
    matched_rule?: string;
    reason?: string;
    policy_reference?: string | null;
  } | null;
}

// Immutable snapshot of the original Agent 1 rejection (auditable; never
// altered by the human resolution).
export interface OriginalRejection {
  outcome?: string;
  reason_code?: string | null;
  reasoning?: string[];
  confidence_score?: number | null;
  confidence_level?: string | null;
  confidence_factors?: string[];
}

// Agent2 recovery result as serialized by the backend (FOUND | MISSING only).
export interface RecoveryItemResult {
  request_text: string;
  criterion_id: string | null;
  evidence_key: string;
  state: 'FOUND' | 'MISSING' | string;
  evidence_ids: string[];
}

export interface RecoveryResult {
  evidence_request_id: string;
  correlation_id?: string | null;
  claim_id?: string;
  item_results: RecoveryItemResult[];
  recovered_evidence_ids: string[];
  notes?: string[];
}

export interface ClaimVersion {
  version: string;
  attempt?: number;
  decision?: { status: DecisionStatus; reason: string; reason_code?: string; outcome?: string } | null;
  new_evidence_delta?: string[];
  evidence_ids?: string[];
}

export interface ProviderDecisionRecord {
  decision_id: string;
  claim_id: string;
  claim_version?: number;
  decision: 'ACCEPT' | 'DECLINE';
  evidence_ids: string[];
  evidence_request_id?: string | null;
  correlation_id?: string | null;
  reason?: string | null;
  decided_at?: string;
}

export interface DocumentRef {
  document_id: string;
  file_name: string;
  file_type: string;
  uploaded_at: string;
}

export interface TimelineEvent {
  timestamp: string;
  event: string;
  message: string;
  status?: ClaimStatus;
}

// Insurance-side claim list item
export interface InsuranceClaim {
  claim_id: string;
  hospital: string;
  patient_id: string;
  procedure: string;
  procedure_code: string;
  diagnosis_codes: string[];
  service_date: string;
  status: ClaimStatus;
  attempt?: number;
  submission_history?: SubmissionAttempt[];
  current_status?: string;
  resubmission_status?: ResubmissionStatus;
  evidence_request_status?: EvidenceRequestStatus;
  agent2_result?: Agent2ResultStatus | null;
  evidence_request?: EvidenceRequestSummary | null;
  evidence_response?: EvidenceResponseSummary | null;
  submitted_at: string;
  updated_at: string;
  priority?: 'HIGH' | 'MEDIUM' | 'LOW';
}

// Human review queue item
export interface ReviewItem {
  review_id: string;
  claim_id: string;
  hospital: string;
  patient_id: string;
  procedure: string;
  reason_for_review: string;
  assigned_at: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface ReviewDetails extends ReviewItem {
  claim_details: ClaimDetails;
  ai_recommendation: string;
  ai_confidence: number;
}

// Notification (derived client-side from real claim records; no backend
// notifications endpoint exists in V1). Alarming events only — REJECT,
// HUMAN_REVIEW, REQUEST_MORE_INFORMATION, provider decline, failed recovery.
export type NotificationType =
  | 'DECISION'
  | 'HUMAN_REVIEW'
  | 'MORE_INFO'
  | 'PROVIDER_DECLINE'
  | 'RECOVERY_FAILED'
  | 'STATUS_CHANGE'
  | 'RESUBMISSION';

export interface Notification {
  notification_id: string;
  claim_id: string;
  message: string;
  type: NotificationType;
  read: boolean;
  created_at: string;
}

// Create claim request body
export interface CreateClaimPayload {
  patient_id: string;
  procedure_code: string;
  procedure: string;
  diagnosis_codes: string[];
  service_date: string;
  provider_id?: string;
  payer: string;
  policy_id: string;
}

// Decision submit payload
export interface DecisionPayload {
  decision: DecisionStatus;
  reason_code: string;
  comments: string;
}
