export interface Patient {
  patient_id: string;
  name: string;
  age: number;
  dob: string;
  gender: 'Male' | 'Female' | 'Other';
  blood_type: string;
  phone: string;
  email: string;
  address: string;
  insurance_id: string;
  payer: string;
  policy_id: string;
  primary_physician: string;
  diagnoses: string[];
  last_visit: string;
  status: 'Active' | 'Inactive' | 'Critical';
  claims_count: number;
  outstanding_amount: number;
}
