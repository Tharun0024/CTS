export interface Authorization {
  auth_id: string;
  claim_id?: string;
  patient_id: string;
  patient_name: string;
  provider_id: string;
  provider_name: string;
  payer: string;
  procedure: string;
  procedure_code: string;
  service_date: string;
  requested_at: string;
  updated_at: string;
  status: 'Pending' | 'Approved' | 'Denied' | 'Expired' | 'In Review' | 'Cancelled';
  auth_number?: string;
  expiry_date?: string;
  notes?: string;
  priority: 'Urgent' | 'Standard' | 'Elective';
}

export const mockAuthorizations: Authorization[] = [
  {
    auth_id: 'AUTH-001', claim_id: 'CLM-001', patient_id: 'PAT-001', patient_name: 'John Mitchell',
    provider_id: 'PRV-001', provider_name: 'Dr. Karen Ellis', payer: 'Aetna',
    procedure: 'Total Knee Replacement', procedure_code: '27447',
    service_date: '2026-08-20', requested_at: '2026-08-11T10:30:00Z', updated_at: '2026-08-11T11:00:00Z',
    status: 'Approved', auth_number: 'AET-2026-9921', expiry_date: '2026-11-20',
    notes: 'All policy criteria satisfied.', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-002', claim_id: 'CLM-002', patient_id: 'PAT-002', patient_name: 'Sarah Thompson',
    provider_id: 'PRV-002', provider_name: 'Dr. Marcus Reid', payer: 'UnitedHealth',
    procedure: 'Lumbar Spinal Fusion', procedure_code: '22612',
    service_date: '2026-08-22', requested_at: '2026-08-10T14:00:00Z', updated_at: '2026-08-11T09:30:00Z',
    status: 'Denied', notes: 'Missing MRI and orthopedic evaluation. Appeal in progress.', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-003', claim_id: 'CLM-003', patient_id: 'PAT-003', patient_name: 'Robert Chen',
    provider_id: 'PRV-003', provider_name: 'Dr. Priya Nair', payer: 'Cigna',
    procedure: 'CT Scan – Abdomen & Pelvis', procedure_code: '74178',
    service_date: '2026-08-18', requested_at: '2026-08-11T08:00:00Z', updated_at: '2026-08-11T10:15:00Z',
    status: 'In Review', notes: 'Awaiting lab results upload.', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-004', claim_id: 'CLM-004', patient_id: 'PAT-004', patient_name: 'Eleanor Walsh',
    provider_id: 'PRV-004', provider_name: 'Dr. James Hartley', payer: 'BlueCross BlueShield',
    procedure: 'Cardiac Catheterization', procedure_code: '93460',
    service_date: '2026-08-25', requested_at: '2026-08-09T11:00:00Z', updated_at: '2026-08-10T16:00:00Z',
    status: 'In Review', notes: 'Escalated for human clinical review.', priority: 'Urgent',
  },
  {
    auth_id: 'AUTH-005', claim_id: 'CLM-005', patient_id: 'PAT-005', patient_name: 'David Park',
    provider_id: 'PRV-005', provider_name: 'Dr. Linda Foster', payer: 'Humana',
    procedure: 'Shoulder Arthroscopy', procedure_code: '29807',
    service_date: '2026-08-30', requested_at: '2026-08-12T10:00:00Z', updated_at: '2026-08-12T10:02:00Z',
    status: 'Pending', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-006', claim_id: 'CLM-006', patient_id: 'PAT-006', patient_name: 'Linda Reyes',
    provider_id: 'PRV-006', provider_name: 'Dr. Angela Torres', payer: 'Anthem',
    procedure: 'Bariatric Surgery (Gastric Bypass)', procedure_code: '43644',
    service_date: '2026-09-05', requested_at: '2026-08-11T15:00:00Z', updated_at: '2026-08-12T09:00:00Z',
    status: 'In Review', priority: 'Elective',
  },
  {
    auth_id: 'AUTH-007', patient_id: 'PAT-007', patient_name: 'Marcus Johnson',
    provider_id: 'PRV-002', provider_name: 'Dr. Marcus Reid', payer: 'UnitedHealth',
    procedure: 'Lumbar Spinal Fusion', procedure_code: '22612',
    service_date: '2026-09-10', requested_at: '2026-08-05T09:00:00Z', updated_at: '2026-08-12T11:00:00Z',
    status: 'In Review', notes: 'Resubmission with complete MRI documentation.', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-008', claim_id: 'CLM-008', patient_id: 'PAT-008', patient_name: 'Patricia Novak',
    provider_id: 'PRV-001', provider_name: 'Dr. Karen Ellis', payer: 'Aetna',
    procedure: 'Hip Replacement', procedure_code: '27130',
    service_date: '2026-09-15', requested_at: '2026-08-12T12:00:00Z', updated_at: '2026-08-12T12:00:00Z',
    status: 'Pending', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-009', patient_id: 'PAT-010', patient_name: 'Angela Kim',
    provider_id: 'PRV-004', provider_name: 'Dr. James Hartley', payer: 'Humana',
    procedure: 'Echocardiogram', procedure_code: '93306',
    service_date: '2026-08-11', requested_at: '2026-08-01T09:00:00Z', updated_at: '2026-08-10T14:00:00Z',
    status: 'Approved', auth_number: 'HUM-2026-4432', expiry_date: '2026-10-11', priority: 'Standard',
  },
  {
    auth_id: 'AUTH-010', patient_id: 'PAT-012', patient_name: 'Dorothy Singh',
    provider_id: 'PRV-007', provider_name: 'Dr. Samuel Grant', payer: 'Anthem',
    procedure: 'Pulmonary Function Test', procedure_code: '94010',
    service_date: '2026-08-05', requested_at: '2026-07-28T10:00:00Z', updated_at: '2026-08-04T16:00:00Z',
    status: 'Expired', auth_number: 'ANT-2026-8812', expiry_date: '2026-08-12',
    notes: 'Authorization expired. Renewal required.', priority: 'Urgent',
  },
];
