export interface Provider {
  provider_id: string;
  name: string;
  specialty: string;
  department: string;
  npi: string;
  phone: string;
  email: string;
  hospital: string;
  status: 'Active' | 'On Leave' | 'Inactive';
  patients_count: number;
  claims_count: number;
  approval_rate: number;
  joining_date: string;
  avatar_initials: string;
  accent: string;
}
