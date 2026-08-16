export interface MemberEligibility {
  eligible: boolean;
  coverage_status: 'Active' | 'Inactive' | 'Suspended' | 'Terminated';
  effective_date: string;
  termination_date?: string;
  copay_amount?: number;
  deductible_met: number;
  deductible_total: number;
}

export interface PriorAuthHistoryItem {
  auth_id: string;
  procedure: string;
  procedure_code: string;
  requested_date: string;
  decision_date?: string;
  status: 'Approved' | 'Denied' | 'Pending';
  notes?: string;
}

export interface ClaimHistoryItem {
  claim_id: string;
  procedure: string;
  procedure_code: string;
  service_date: string;
  amount_billed: number;
  amount_paid?: number;
  status: 'Accepted' | 'Rejected' | 'In Progress';
}

export interface UtilizationFrequency {
  visits_this_year: number;
  max_allowed_visits_per_year: number;
  procedures_performed: number;
  er_visits: number;
  pt_sessions_count: number;
  pt_sessions_allowed: number;
}

export interface CoverageDetails {
  plan_type: string;
  group_number: string;
  subscriber_id: string;
  benefit_details: {
    in_network_coverage_percent: number;
    out_of_network_coverage_percent: number;
    max_out_of_pocket: number;
    max_out_of_pocket_met: number;
  };
}

export interface InsurerAdministrativeData {
  patient_id: string;
  patient_name: string;
  eligibility: MemberEligibility;
  prior_auth_history: PriorAuthHistoryItem[];
  claim_history: ClaimHistoryItem[];
  utilization_frequency: UtilizationFrequency;
  coverage_details: CoverageDetails;
}
