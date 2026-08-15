import type { ClaimDetails } from '../types/claim';

// Full ClaimDetails objects (one per status in the spec)
export const mockClaimDetails: ClaimDetails[] = [
  // 1. ACCEPTED
  {
    claim_id: 'CLM-001',
    patient: { patient_id: 'PAT-001', age: 57, gender: 'Male', name: 'John Mitchell' },
    claim: {
      procedure: 'Total Knee Replacement',
      procedure_code: '27447',
      diagnosis_codes: ['M17.11', 'M79.622'],
      service_date: '2026-08-20',
      provider_id: 'PRV-001',
    },
    policy: { payer: 'Aetna', policy_id: 'CPB-0660', policy_name: 'Aetna CPB 0660 – Knee Replacement' },
    decision: { status: 'ACCEPT', reason: 'All policy criteria satisfied. Conservative treatment documented.', reason_code: 'CRITERIA_MET' },
    policy_evidence: [
      { criterion: 'Conservative treatment (≥12 weeks)', patient_value: '14 weeks of physical therapy', status: 'MET', source: 'Physician notes 2026-07-10' },
      { criterion: 'BMI within acceptable range', patient_value: 'BMI 28.4', status: 'MET', source: 'Lab results 2026-06-15' },
      { criterion: 'Radiological evidence of OA', patient_value: 'X-ray confirms Grade III OA', status: 'MET', source: 'Radiology report 2026-07-20' },
      { criterion: 'Failed non-surgical interventions', patient_value: 'NSAIDs 8 months, steroid injections ×2', status: 'MET', source: 'Medical history' },
    ],
    missing_information: [],
    resubmission: { eligible: false, status: 'NOT_REQUIRED' },
    status: 'ACCEPTED',
    submitted_at: '2026-08-11T10:30:00Z',
    updated_at: '2026-08-11T11:00:00Z',
    hospital: 'City General Hospital',
    documents: [
      { document_id: 'DOC-001', file_name: 'physician_notes.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-11T10:28:00Z' },
      { document_id: 'DOC-002', file_name: 'xray_report.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-11T10:28:30Z' },
    ],
    timeline: [
      { timestamp: '2026-08-11T10:30:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-11T10:31:00Z', event: 'PROCESSING', message: 'Documents extracted & indexed' },
      { timestamp: '2026-08-11T10:45:00Z', event: 'UNDER_REVIEW', message: 'Policy analysis in progress' },
      { timestamp: '2026-08-11T11:00:00Z', event: 'ACCEPTED', message: 'All criteria satisfied — claim accepted' },
    ],
  },

  // 2. REJECTED
  {
    claim_id: 'CLM-002',
    patient: { patient_id: 'PAT-002', age: 42, gender: 'Female', name: 'Sarah Thompson' },
    claim: {
      procedure: 'Lumbar Spinal Fusion',
      procedure_code: '22612',
      diagnosis_codes: ['M51.16', 'M54.5'],
      service_date: '2026-08-22',
      provider_id: 'PRV-002',
    },
    policy: { payer: 'UnitedHealth', policy_id: 'UHC-SPINE-001', policy_name: 'UHC Spine Surgery Policy' },
    decision: { status: 'REJECT', reason: 'Missing orthopedic specialist report. MRI evidence not provided. Conservative treatment duration insufficient (8 weeks, minimum 12 required).', reason_code: 'INSUFFICIENT_DOCUMENTATION' },
    policy_evidence: [
      { criterion: 'Conservative treatment (≥12 weeks)', patient_value: '8 weeks documented', status: 'NOT_MET', source: 'Physician notes 2026-07-01' },
      { criterion: 'MRI evidence of disc herniation', patient_value: 'Not provided', status: 'NOT_MET', source: 'N/A' },
      { criterion: 'Orthopedic specialist evaluation', patient_value: 'Not documented', status: 'NOT_MET', source: 'N/A' },
      { criterion: 'Neurological symptoms documented', patient_value: 'Lower back pain reported', status: 'MET', source: 'GP referral 2026-07-15' },
    ],
    missing_information: [
      'MRI scan report (lumbar spine, within 6 months)',
      'Orthopedic specialist evaluation letter',
      'Evidence of 12+ weeks conservative treatment',
    ],
    resubmission: { eligible: true, status: 'ELIGIBLE' },
    status: 'REJECTED',
    submitted_at: '2026-08-10T14:00:00Z',
    updated_at: '2026-08-11T09:30:00Z',
    hospital: 'Metro Medical Center',
    documents: [
      { document_id: 'DOC-003', file_name: 'gp_referral.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-10T13:55:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-10T14:00:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-10T14:05:00Z', event: 'PROCESSING', message: 'Documents extracted' },
      { timestamp: '2026-08-10T14:30:00Z', event: 'UNDER_REVIEW', message: 'Policy analysis in progress' },
      { timestamp: '2026-08-11T09:30:00Z', event: 'REJECTED', message: 'Insufficient documentation for policy criteria' },
    ],
  },

  // 3. MORE_INFO
  {
    claim_id: 'CLM-003',
    patient: { patient_id: 'PAT-003', age: 65, gender: 'Male', name: 'Robert Chen' },
    claim: {
      procedure: 'CT Scan – Abdomen & Pelvis',
      procedure_code: '74178',
      diagnosis_codes: ['R10.9', 'K92.1'],
      service_date: '2026-08-18',
      provider_id: 'PRV-003',
    },
    policy: { payer: 'Cigna', policy_id: 'CGN-IMG-002', policy_name: 'Cigna Imaging Authorization Policy' },
    decision: { status: 'MORE_INFORMATION', reason: 'Lab results and prior imaging not included with submission.', reason_code: 'MISSING_DOCUMENTS' },
    policy_evidence: [
      { criterion: 'Prior conservative treatment documented', patient_value: 'PPI therapy 4 weeks', status: 'MET', source: 'Medical history' },
      { criterion: 'Lab work (CBC, CMP) within 90 days', patient_value: 'Not provided', status: 'NOT_MET', source: 'N/A' },
      { criterion: 'Prior imaging (X-ray or ultrasound)', patient_value: 'Not provided', status: 'NOT_MET', source: 'N/A' },
    ],
    missing_information: [
      'Recent lab results (CBC + CMP, within 90 days)',
      'Prior imaging report (X-ray or abdominal ultrasound)',
    ],
    resubmission: { eligible: true, status: 'AWAITING_DOCUMENTS' },
    status: 'MORE_INFO',
    submitted_at: '2026-08-11T08:00:00Z',
    updated_at: '2026-08-11T10:15:00Z',
    hospital: 'Eastside Clinic',
    documents: [],
    timeline: [
      { timestamp: '2026-08-11T08:00:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-11T08:10:00Z', event: 'PROCESSING', message: 'Documents extracted' },
      { timestamp: '2026-08-11T10:15:00Z', event: 'MORE_INFO', message: 'Additional documentation required' },
    ],
  },

  // 4. HUMAN_REVIEW
  {
    claim_id: 'CLM-004',
    patient: { patient_id: 'PAT-004', age: 72, gender: 'Female', name: 'Eleanor Walsh' },
    claim: {
      procedure: 'Cardiac Catheterization',
      procedure_code: '93460',
      diagnosis_codes: ['I25.10', 'I20.9'],
      service_date: '2026-08-25',
      provider_id: 'PRV-004',
    },
    policy: { payer: 'BlueCross BlueShield', policy_id: 'BCBS-CARD-001', policy_name: 'BCBS Cardiac Procedures Policy' },
    decision: { status: 'HUMAN_REVIEW', reason: 'Conflicting clinical evidence detected. Patient age and comorbidities require human clinical judgment.', reason_code: 'CLINICAL_COMPLEXITY' },
    policy_evidence: [
      { criterion: 'Documented angina symptoms', patient_value: 'Stable angina, Class II', status: 'MET', source: 'Cardiologist report 2026-08-01' },
      { criterion: 'Non-invasive testing (stress test/echo)', patient_value: 'Stress test abnormal', status: 'MET', source: 'Cardiology 2026-07-28' },
      { criterion: 'Optimal medical therapy documented', patient_value: 'Beta-blockers, statins 6 months', status: 'MET', source: 'Prescription history' },
      { criterion: 'Left ventricular function assessment', patient_value: 'EF 45% — borderline', status: 'MET', source: 'Echo report 2026-08-01' },
      { criterion: 'Comorbidity risk assessment', patient_value: 'Diabetes, CKD Stage 3 — complex', status: 'NOT_MET', source: 'Medical history' },
    ],
    missing_information: [],
    resubmission: { eligible: false, status: 'UNDER_HUMAN_REVIEW' },
    status: 'HUMAN_REVIEW',
    submitted_at: '2026-08-09T11:00:00Z',
    updated_at: '2026-08-10T16:00:00Z',
    hospital: 'Northside Heart Institute',
    documents: [
      { document_id: 'DOC-004', file_name: 'cardiology_report.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-09T10:58:00Z' },
      { document_id: 'DOC-005', file_name: 'stress_test_results.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-09T10:59:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-09T11:00:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-09T11:05:00Z', event: 'PROCESSING', message: 'Documents extracted' },
      { timestamp: '2026-08-09T12:00:00Z', event: 'UNDER_REVIEW', message: 'Policy analysis in progress' },
      { timestamp: '2026-08-10T16:00:00Z', event: 'HUMAN_REVIEW', message: 'Escalated to clinical reviewer' },
    ],
  },

  // 5. PROCESSING
  {
    claim_id: 'CLM-005',
    patient: { patient_id: 'PAT-005', age: 34, gender: 'Male', name: 'David Park' },
    claim: {
      procedure: 'Shoulder Arthroscopy',
      procedure_code: '29807',
      diagnosis_codes: ['M75.1', 'M75.5'],
      service_date: '2026-08-30',
      provider_id: 'PRV-005',
    },
    policy: { payer: 'Humana', policy_id: 'HUM-ORTH-003', policy_name: 'Humana Orthopedic Surgery Policy' },
    decision: null,
    policy_evidence: [],
    missing_information: [],
    resubmission: { eligible: false, status: 'PROCESSING' },
    status: 'PROCESSING',
    submitted_at: '2026-08-12T10:00:00Z',
    updated_at: '2026-08-12T10:02:00Z',
    hospital: 'Westside Orthopedics',
    documents: [
      { document_id: 'DOC-006', file_name: 'mri_shoulder.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-12T09:58:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-12T10:00:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-12T10:02:00Z', event: 'PROCESSING', message: 'Extracting documents and matching policy...' },
    ],
  },

  // 6. UNDER_REVIEW
  {
    claim_id: 'CLM-006',
    patient: { patient_id: 'PAT-006', age: 55, gender: 'Female', name: 'Linda Reyes' },
    claim: {
      procedure: 'Bariatric Surgery (Gastric Bypass)',
      procedure_code: '43644',
      diagnosis_codes: ['E66.01', 'E11.9'],
      service_date: '2026-09-05',
      provider_id: 'PRV-006',
    },
    policy: { payer: 'Anthem', policy_id: 'ANT-BAR-001', policy_name: 'Anthem Bariatric Surgery Coverage' },
    decision: null,
    policy_evidence: [
      { criterion: 'BMI ≥ 40 or BMI ≥ 35 with comorbidities', patient_value: 'BMI 38, Type 2 Diabetes', status: 'MET', source: 'Physical exam 2026-07-20' },
      { criterion: 'Medically supervised diet (6 months)', patient_value: 'Nutritionist program 7 months', status: 'MET', source: 'Nutritionist records' },
      { criterion: 'Psychiatric clearance', patient_value: 'Pending evaluation', status: 'NOT_MET', source: 'N/A' },
    ],
    missing_information: ['Psychiatric clearance letter'],
    resubmission: { eligible: false, status: 'UNDER_REVIEW' },
    status: 'UNDER_REVIEW',
    submitted_at: '2026-08-11T15:00:00Z',
    updated_at: '2026-08-12T09:00:00Z',
    hospital: 'Lakeside Surgical Center',
    documents: [
      { document_id: 'DOC-007', file_name: 'bmi_records.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-11T14:55:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-11T15:00:00Z', event: 'SUBMITTED', message: 'Claim submitted' },
      { timestamp: '2026-08-11T15:10:00Z', event: 'PROCESSING', message: 'Documents extracted' },
      { timestamp: '2026-08-12T09:00:00Z', event: 'UNDER_REVIEW', message: 'Policy criteria check in progress...' },
    ],
  },

  // 7. RESUBMISSION_CHECK
  {
    claim_id: 'CLM-007',
    patient: { patient_id: 'PAT-007', age: 48, gender: 'Male', name: 'Marcus Johnson' },
    claim: {
      procedure: 'Lumbar Spinal Fusion',
      procedure_code: '22612',
      diagnosis_codes: ['M51.16'],
      service_date: '2026-09-10',
      provider_id: 'PRV-002',
    },
    policy: { payer: 'UnitedHealth', policy_id: 'UHC-SPINE-001', policy_name: 'UHC Spine Surgery Policy' },
    decision: { status: 'REJECT', reason: 'Originally rejected due to missing MRI. Now under resubmission check.', reason_code: 'RESUBMISSION' },
    policy_evidence: [
      { criterion: 'Conservative treatment (≥12 weeks)', patient_value: '14 weeks documented', status: 'MET', source: 'Physician notes' },
      { criterion: 'MRI evidence of disc herniation', patient_value: 'MRI report uploaded 2026-08-05', status: 'MET', source: 'Radiology 2026-08-05' },
      { criterion: 'Orthopedic specialist evaluation', patient_value: 'Dr. Kim evaluation 2026-08-08', status: 'MET', source: 'Orthopedic referral' },
    ],
    missing_information: [],
    resubmission: { eligible: true, status: 'RESUBMISSION_CHECK' },
    status: 'RESUBMISSION_CHECK',
    submitted_at: '2026-08-05T09:00:00Z',
    updated_at: '2026-08-12T11:00:00Z',
    hospital: 'Metro Medical Center',
    documents: [
      { document_id: 'DOC-008', file_name: 'mri_lumbar.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-05T08:55:00Z' },
      { document_id: 'DOC-009', file_name: 'ortho_eval.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-08T10:00:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-01T14:00:00Z', event: 'SUBMITTED', message: 'Initial claim submitted' },
      { timestamp: '2026-08-02T09:30:00Z', event: 'REJECTED', message: 'Rejected: missing MRI and orthopedic eval' },
      { timestamp: '2026-08-05T09:00:00Z', event: 'SUBMITTED', message: 'Resubmitted with additional documents' },
      { timestamp: '2026-08-12T11:00:00Z', event: 'RESUBMISSION_CHECK', message: 'Analyzing resubmission criteria...' },
    ],
  },

  // 8. SUBMITTED_AGAIN
  {
    claim_id: 'CLM-008',
    patient: { patient_id: 'PAT-008', age: 61, gender: 'Female', name: 'Patricia Novak' },
    claim: {
      procedure: 'Hip Replacement',
      procedure_code: '27130',
      diagnosis_codes: ['M16.11', 'M79.652'],
      service_date: '2026-09-15',
      provider_id: 'PRV-001',
    },
    policy: { payer: 'Aetna', policy_id: 'CPB-0660', policy_name: 'Aetna CPB 0660 – Hip Replacement' },
    decision: null,
    policy_evidence: [
      { criterion: 'Conservative treatment (≥12 weeks)', patient_value: '16 weeks documented', status: 'MET', source: 'PT records' },
      { criterion: 'Radiological evidence of OA', patient_value: 'X-ray Grade IV OA', status: 'MET', source: 'Radiology 2026-08-01' },
      { criterion: 'Functional limitation documented', patient_value: 'Harris Hip Score 38', status: 'MET', source: 'Orthopedic assessment' },
    ],
    missing_information: [],
    resubmission: { eligible: true, status: 'RESUBMITTED' },
    status: 'SUBMITTED_AGAIN',
    submitted_at: '2026-08-12T12:00:00Z',
    updated_at: '2026-08-12T12:00:00Z',
    hospital: 'City General Hospital',
    documents: [
      { document_id: 'DOC-010', file_name: 'pt_records.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-12T11:58:00Z' },
      { document_id: 'DOC-011', file_name: 'hip_xray.pdf', file_type: 'application/pdf', uploaded_at: '2026-08-12T11:59:00Z' },
    ],
    timeline: [
      { timestamp: '2026-08-05T10:00:00Z', event: 'SUBMITTED', message: 'Initial claim submitted' },
      { timestamp: '2026-08-06T14:00:00Z', event: 'REJECTED', message: 'Rejected: incomplete documentation' },
      { timestamp: '2026-08-12T12:00:00Z', event: 'SUBMITTED_AGAIN', message: 'Resubmitted with complete documentation' },
    ],
  },

  // 9. DRAFT
  {
    claim_id: 'CLM-009',
    patient: { patient_id: 'PAT-009', age: 29, gender: 'Male', name: 'James O\'Brien' },
    claim: {
      procedure: 'Knee Arthroscopy',
      procedure_code: '29881',
      diagnosis_codes: ['M23.201'],
      service_date: '2026-09-20',
      provider_id: 'PRV-005',
    },
    policy: { payer: 'Cigna', policy_id: 'CGN-ORTH-001', policy_name: 'Cigna Orthopedic Surgery' },
    decision: null,
    policy_evidence: [],
    missing_information: [],
    resubmission: { eligible: false, status: 'DRAFT' },
    status: 'DRAFT',
    submitted_at: '2026-08-12T13:00:00Z',
    updated_at: '2026-08-12T13:00:00Z',
    hospital: 'Sports Medicine Clinic',
    documents: [],
    timeline: [
      { timestamp: '2026-08-12T13:00:00Z', event: 'DRAFT', message: 'Claim draft saved' },
    ],
  },
];

const workflowDefaults = {
  attempt: 1,
  submission_history: [] as ClaimDetails['submission_history'],
  evidence_request: null,
  evidence_response: null,
  evidence_request_status: 'CLOSED' as const,
  resubmission_status: 'NOT_REQUIRED' as const,
  agent2_result: null,
  reevaluation_status: null,
};

const workflowByClaimId: Record<string, Partial<ClaimDetails>> = {
  'CLM-001': {
    attempt: 1,
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-11T10:30:00Z', status: 'ACCEPTED', note: 'Approved on first pass.' },
    ],
  },
  'CLM-002': {
    attempt: 1,
    resubmission_status: 'AWAITING_EVIDENCE',
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-10T14:00:00Z', status: 'REJECTED', note: 'Denied due to insufficient documentation.' },
    ],
  },
  'CLM-003': {
    attempt: 1,
    evidence_request_status: 'WAITING_FOR_PROVIDER',
    resubmission_status: 'AWAITING_EVIDENCE',
    evidence_request: {
      request_id: 'EVR-003',
      requested_evidence: 'PT Documentation',
      reason: 'Required documentation is missing',
      status: 'WAITING_FOR_PROVIDER',
    },
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-11T08:00:00Z', status: 'MORE_INFO', note: 'Agent 1 requested additional documentation.' },
    ],
    timeline: [
      { timestamp: '2026-08-11T08:00:00Z', event: 'SUBMITTED', message: 'Claim Submitted', status: 'SUBMITTED' },
      { timestamp: '2026-08-11T08:10:00Z', event: 'UNDER_REVIEW', message: 'Agent 1 Analysis', status: 'UNDER_REVIEW' },
      { timestamp: '2026-08-11T10:15:00Z', event: 'MORE_INFO', message: 'Need More Info', status: 'MORE_INFO' },
      { timestamp: '2026-08-11T10:16:00Z', event: 'MORE_INFO', message: 'Evidence Request', status: 'MORE_INFO' },
      { timestamp: '2026-08-11T10:17:00Z', event: 'MORE_INFO', message: 'Provider Received Request', status: 'MORE_INFO' },
    ],
  },
  'CLM-004': {
    attempt: 1,
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-09T11:00:00Z', status: 'HUMAN_REVIEW', note: 'Escalated to human review by Agent 1.' },
    ],
  },
  'CLM-005': {
    attempt: 1,
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-12T10:00:00Z', status: 'PROCESSING', note: 'Under AI processing.' },
    ],
  },
  'CLM-006': {
    attempt: 1,
    evidence_request_status: 'PENDING_PROVIDER_RESPONSE',
    resubmission_status: 'AWAITING_EVIDENCE',
    evidence_request: {
      request_id: 'EVR-006',
      requested_evidence: 'Psychiatric Clearance',
      reason: 'Behavioral health clearance is required before approval.',
      status: 'PENDING_PROVIDER_RESPONSE',
    },
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-11T15:00:00Z', status: 'UNDER_REVIEW', note: 'Under Agent 1 review.' },
    ],
  },
  'CLM-007': {
    attempt: 1,
    evidence_request_status: 'RECEIVED',
    resubmission_status: 'UNDER_RE_EVALUATION',
    evidence_request: {
      request_id: 'EVR-007',
      requested_evidence: 'MRI + Orthopedic evaluation',
      reason: 'Original submission lacked mandatory specialist evidence.',
      status: 'RECEIVED',
    },
    evidence_response: {
      evidence: 'MRI + Orthopedic evaluation',
      decision: 'RELEASED',
      status: 'SENT_TO_PAYER',
      responded_at: '2026-08-12T10:58:00Z',
    },
    agent2_result: 'RELEASED',
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-01T14:00:00Z', status: 'MORE_INFO', note: 'Need more clinical evidence.' },
      { attempt: 2, submitted_at: '2026-08-05T09:00:00Z', status: 'RESUBMISSION_CHECK', note: 'Submitted for re-evaluation with new evidence.' },
    ],
    timeline: [
      { timestamp: '2026-08-01T14:00:00Z', event: 'SUBMITTED', message: 'Claim Submitted', status: 'SUBMITTED' },
      { timestamp: '2026-08-01T14:20:00Z', event: 'UNDER_REVIEW', message: 'Agent 1 Analysis', status: 'UNDER_REVIEW' },
      { timestamp: '2026-08-02T09:30:00Z', event: 'MORE_INFO', message: 'Need More Info', status: 'MORE_INFO' },
      { timestamp: '2026-08-02T09:40:00Z', event: 'MORE_INFO', message: 'Evidence Request', status: 'MORE_INFO' },
      { timestamp: '2026-08-05T09:00:00Z', event: 'SUBMITTED_AGAIN', message: 'Resubmission', status: 'SUBMITTED_AGAIN' },
      { timestamp: '2026-08-05T09:10:00Z', event: 'UNDER_REVIEW', message: 'Agent 1 Re-evaluation', status: 'UNDER_REVIEW' },
    ],
  },
  'CLM-008': {
    attempt: 2,
    evidence_request_status: 'RECEIVED',
    resubmission_status: 'RESUBMITTED',
    evidence_request: {
      request_id: 'EVR-008',
      requested_evidence: 'PT Documentation',
      reason: 'Required documentation is missing',
      status: 'RECEIVED',
    },
    evidence_response: {
      evidence: 'PT Documentation',
      decision: 'RELEASED',
      status: 'SENT_TO_PAYER',
      responded_at: '2026-08-12T11:59:00Z',
    },
    agent2_result: 'RELEASED',
    reevaluation_status: 'UNDER REVIEW',
    submission_history: [
      { attempt: 1, submitted_at: '2026-08-05T10:00:00Z', status: 'MORE_INFO', note: 'Need more information after initial analysis.' },
      { attempt: 2, submitted_at: '2026-08-12T12:00:00Z', status: 'SUBMITTED_AGAIN', note: 'New evidence added and submitted for re-evaluation.' },
    ],
    timeline: [
      { timestamp: '2026-08-05T10:00:00Z', event: 'SUBMITTED', message: 'Claim Submitted', status: 'SUBMITTED' },
      { timestamp: '2026-08-05T10:05:00Z', event: 'UNDER_REVIEW', message: 'Agent 1 Analysis', status: 'UNDER_REVIEW' },
      { timestamp: '2026-08-06T14:00:00Z', event: 'MORE_INFO', message: 'Need More Info', status: 'MORE_INFO' },
      { timestamp: '2026-08-06T14:10:00Z', event: 'MORE_INFO', message: 'Evidence Request', status: 'MORE_INFO' },
      { timestamp: '2026-08-06T14:15:00Z', event: 'MORE_INFO', message: 'Provider Received Request', status: 'MORE_INFO' },
      { timestamp: '2026-08-12T11:30:00Z', event: 'UNDER_REVIEW', message: 'Agent 2', status: 'UNDER_REVIEW' },
      { timestamp: '2026-08-12T11:40:00Z', event: 'ACCEPTED', message: 'Released', status: 'ACCEPTED' },
      { timestamp: '2026-08-12T12:00:00Z', event: 'SUBMITTED_AGAIN', message: 'Resubmission', status: 'SUBMITTED_AGAIN' },
      { timestamp: '2026-08-12T12:10:00Z', event: 'UNDER_REVIEW', message: 'Agent 1 Re-evaluation', status: 'UNDER_REVIEW' },
    ],
  },
  'CLM-009': {
    attempt: 1,
    submission_history: [{ attempt: 1, submitted_at: '2026-08-12T13:00:00Z', status: 'DRAFT', note: 'Draft saved.' }],
  },
};

for (const claim of mockClaimDetails) {
  const specific = workflowByClaimId[claim.claim_id] ?? {};
  Object.assign(claim, workflowDefaults, specific);
}

// Flat claim list (for tables/lists)
export const mockClaims = mockClaimDetails.map(cd => ({
  claim_id: cd.claim_id,
  patient_id: cd.patient.patient_id,
  hospital: cd.hospital,
  procedure: cd.claim.procedure,
  procedure_code: cd.claim.procedure_code,
  diagnosis_codes: cd.claim.diagnosis_codes,
  service_date: cd.claim.service_date,
  status: cd.status,
  attempt: cd.attempt,
  submission_history: cd.submission_history,
  evidence_request_status: cd.evidence_request_status,
  resubmission_status: cd.resubmission_status,
  agent2_result: cd.agent2_result,
  evidence_request: cd.evidence_request,
  evidence_response: cd.evidence_response,
  submitted_at: cd.submitted_at,
  updated_at: cd.updated_at,
}));
