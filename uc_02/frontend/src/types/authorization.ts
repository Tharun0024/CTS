import type { Patient } from './patient';
import type { Document } from './document';
import type { DecisionStatus } from './decision';

export type CaseStatus = 
  | 'DRAFT'
  | 'UPLOADING'
  | 'PROCESSING'
  | 'VALIDATION_FAILED'
  | 'EXTRACTION_COMPLETED'
  | 'POLICY_ANALYSIS'
  | 'DECISION_READY'
  | 'MORE_INFORMATION'
  | 'HUMAN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'EMERGENCY';

export type CaseSource = 'manual' | 'simulation';
export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Insurance {
  provider: string;
  member_id: string;
  plan: string;
  policy_id?: string;
}

export interface AuthorizationRequest {
  procedure: string;
  diagnosis: string;
  reason: string;
  previous_treatment?: string;
  clinical_findings?: string;
  doctor_recommendation?: string;
}

export interface AuthorizationCase {
  authorization_id: string;
  source: CaseSource;
  status: CaseStatus;
  patient: Patient;
  insurance: Insurance;
  request: AuthorizationRequest;
  documents: Document[];
  decision: DecisionStatus | null;
  priority?: Priority;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  timestamp: string;
  event: string;
  message: string;
}
