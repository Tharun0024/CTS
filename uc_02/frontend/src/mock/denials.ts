export interface Denial {
  denial_id: string;
  claim_id: string;
  patient_name: string;
  payer: string;
  procedure: string;
  billed_amount: number;
  denied_amount: number;
  denial_reason: string;
  reason_code: string;
  denied_date: string;
  appeal_deadline: string;
  status: 'Open' | 'In Appeal' | 'Won' | 'Lost' | 'Closed';
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  notes?: string;
}

export const mockDenials: Denial[] = [
  {
    denial_id: 'DEN-001', claim_id: 'CLM-002', patient_name: 'Sarah Thompson',
    payer: 'UnitedHealth', procedure: 'Lumbar Spinal Fusion',
    billed_amount: 58000, denied_amount: 58000,
    denial_reason: 'Missing MRI report, insufficient conservative treatment documentation (8 weeks vs required 12)',
    reason_code: 'INSUFFICIENT_DOCUMENTATION',
    denied_date: '2026-08-11', appeal_deadline: '2026-09-10',
    status: 'In Appeal', priority: 'Critical',
    notes: 'Appeal submitted with MRI report. Awaiting insurer response.',
  },
  {
    denial_id: 'DEN-002', claim_id: 'CLM-009', patient_name: "James O'Brien",
    payer: 'Cigna', procedure: 'Knee Arthroscopy',
    billed_amount: 12500, denied_amount: 12500,
    denial_reason: 'Procedure not covered under current policy for age group',
    reason_code: 'NOT_COVERED',
    denied_date: '2026-08-08', appeal_deadline: '2026-09-07',
    status: 'Open', priority: 'High',
    notes: 'Reviewing policy terms for exception request.',
  },
  {
    denial_id: 'DEN-003', claim_id: 'CLM-010', patient_name: 'Angela Kim',
    payer: 'Humana', procedure: 'Cardiac Monitoring',
    billed_amount: 8200, denied_amount: 8200,
    denial_reason: 'Duplicate claim submission detected',
    reason_code: 'DUPLICATE_CLAIM',
    denied_date: '2026-08-05', appeal_deadline: '2026-09-04',
    status: 'Won', priority: 'Medium',
    notes: 'Duplicate resolved. Original claim approved and paid.',
  },
  {
    denial_id: 'DEN-004', claim_id: 'CLM-011', patient_name: 'Carlos Mendes',
    payer: 'BlueCross BlueShield', procedure: 'Peripheral Neuropathy Treatment',
    billed_amount: 5400, denied_amount: 5400,
    denial_reason: 'Prior authorization not obtained before service',
    reason_code: 'NO_PRIOR_AUTH',
    denied_date: '2026-07-28', appeal_deadline: '2026-08-27',
    status: 'Lost', priority: 'Low',
    notes: 'Appeal denied. Authorization was required prior to service date.',
  },
  {
    denial_id: 'DEN-005', claim_id: 'CLM-012', patient_name: 'Dorothy Singh',
    payer: 'Anthem', procedure: 'COPD Management Program',
    billed_amount: 6800, denied_amount: 4200,
    denial_reason: 'Partial denial — some services not covered under plan',
    reason_code: 'PARTIAL_COVERAGE',
    denied_date: '2026-08-09', appeal_deadline: '2026-09-08',
    status: 'In Appeal', priority: 'High',
    notes: 'Disputing partial denial for pulmonary rehab portion.',
  },
  {
    denial_id: 'DEN-006', claim_id: 'CLM-013', patient_name: 'Marcus Johnson',
    payer: 'UnitedHealth', procedure: 'Physical Therapy (12 sessions)',
    billed_amount: 3600, denied_amount: 3600,
    denial_reason: 'Exceeded annual PT session limit (20 sessions)',
    reason_code: 'BENEFIT_LIMIT_EXCEEDED',
    denied_date: '2026-08-03', appeal_deadline: '2026-09-02',
    status: 'Closed', priority: 'Low',
    notes: 'Patient notified. Switching to self-pay arrangement.',
  },
];
