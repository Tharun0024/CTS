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

export interface Claim {
  claim_id: string;
  patient_id: string;
  hospital?: string;
  procedure: string;
  procedure_code: string;
  diagnosis_codes: string[];
  service_date: string;
  provider_id?: string;
  status: ClaimStatus;
  submitted_at: string;
  updated_at: string;
}

export interface PolicyEvidenceItem {
  criterion: string;
  patient_value: string;
  status: 'MET' | 'NOT_MET';
  source: string;
}

export interface ClaimDecision {
  status: DecisionStatus;
  reason: string;
  reason_code?: string;
  comments?: string;
}

export interface ClaimDetails {
  claim_id: string;
  patient: {
    patient_id: string;
    age: number;
    gender: string;
    name?: string;
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

// Notification
export interface Notification {
  notification_id: string;
  claim_id: string;
  message: string;
  type: 'STATUS_CHANGE' | 'DECISION' | 'MORE_INFO' | 'RESUBMISSION';
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
