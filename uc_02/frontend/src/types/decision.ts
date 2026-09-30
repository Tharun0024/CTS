export type DecisionStatus = 'APPROVE' | 'REJECT' | 'MORE_INFORMATION' | 'HUMAN_REVIEW' | 'EMERGENCY';

export interface DecisionRecord {
  authorization_id: string;
  status: string;
  decision: DecisionStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  comment?: string;
}
