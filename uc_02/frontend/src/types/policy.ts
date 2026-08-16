export interface Policy {
  provider: string;
  policy_id: string;
  title: string;
  version: string;
  reference: string;
}

export interface PolicyCriterion {
  criterion_id: string;
  description: string;
  status: 'PASS' | 'FAIL' | 'MISSING';
  evidence?: string;
}

export interface PolicyAssessment {
  policy: Policy;
  criteria: PolicyCriterion[];
}
