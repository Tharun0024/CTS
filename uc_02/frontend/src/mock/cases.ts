import type { AuthorizationCase } from '../types/authorization';
import type { Patient } from '../types/patient';

export const mockCases: AuthorizationCase[] = [
  {
    authorization_id: "AUTH-001",
    source: "simulation",
    status: "APPROVED",
    patient: {
      patient_id: "SYN-001",
      name: "John Doe",
      age: 57,
      gender: "Male"
    } as unknown as Patient,
    insurance: {
      provider: "Demo Payer",
      member_id: "SYN-INS-001",
      plan: "Gold"
    },
    request: {
      procedure: "Knee Replacement",
      diagnosis: "Osteoarthritis",
      reason: "Severe pain and functional limitation",
      previous_treatment: "Physical therapy for 14 weeks"
    },
    documents: [],
    decision: "APPROVE",
    created_at: "2026-08-11T10:30:00Z",
    updated_at: "2026-08-11T10:31:00Z"
  },
  {
    authorization_id: "AUTH-002",
    source: "manual",
    status: "HUMAN_REVIEW",
    priority: "HIGH",
    patient: {
      patient_id: "SYN-002",
      name: "Jane Smith",
      age: 42,
      gender: "Female"
    } as unknown as Patient,
    insurance: {
      provider: "Demo Payer",
      member_id: "SYN-INS-002",
      plan: "Silver"
    },
    request: {
      procedure: "MRI",
      diagnosis: "Migraine",
      reason: "Chronic headaches",
    },
    documents: [],
    decision: null,
    created_at: "2026-08-11T10:32:00Z",
    updated_at: "2026-08-11T10:35:00Z"
  },
  {
    authorization_id: "AUTH-003",
    source: "manual",
    status: "MORE_INFORMATION",
    priority: "LOW",
    patient: {
      patient_id: "SYN-003",
      name: "Robert Brown",
      age: 65,
      gender: "Male"
    } as unknown as Patient,
    insurance: {
      provider: "Demo Payer",
      member_id: "SYN-INS-003",
      plan: "Bronze"
    },
    request: {
      procedure: "CT Scan",
      diagnosis: "Abdominal Pain",
      reason: "Unexplained pain",
    },
    documents: [],
    decision: "MORE_INFORMATION",
    created_at: "2026-08-11T10:35:00Z",
    updated_at: "2026-08-11T10:38:00Z"
  }
];
