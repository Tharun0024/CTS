import type { Provider } from '../types/provider';

export const mockProviders: Provider[] = [
  {
    provider_id: 'PRV-001', name: 'Dr. Karen Ellis', specialty: 'Orthopedic Surgery',
    department: 'Orthopedics', npi: '1234567890', phone: '(555) 200-1001',
    email: 'k.ellis@hospital.org', hospital: 'City General Hospital',
    status: 'Active', patients_count: 124, claims_count: 87, approval_rate: 91,
    joining_date: '2018-03-01', avatar_initials: 'KE', accent: 'bg-emerald-500',
  },
  {
    provider_id: 'PRV-002', name: 'Dr. Marcus Reid', specialty: 'Spinal Surgery',
    department: 'Neurosurgery', npi: '2345678901', phone: '(555) 200-1002',
    email: 'm.reid@hospital.org', hospital: 'Metro Medical Center',
    status: 'Active', patients_count: 98, claims_count: 64, approval_rate: 78,
    joining_date: '2019-07-15', avatar_initials: 'MR', accent: 'bg-blue-500',
  },
  {
    provider_id: 'PRV-003', name: 'Dr. Priya Nair', specialty: 'Gastroenterology',
    department: 'Gastro', npi: '3456789012', phone: '(555) 200-1003',
    email: 'p.nair@hospital.org', hospital: 'Eastside Clinic',
    status: 'Active', patients_count: 215, claims_count: 143, approval_rate: 88,
    joining_date: '2017-01-20', avatar_initials: 'PN', accent: 'bg-violet-500',
  },
  {
    provider_id: 'PRV-004', name: 'Dr. James Hartley', specialty: 'Cardiology',
    department: 'Cardiology', npi: '4567890123', phone: '(555) 200-1004',
    email: 'j.hartley@hospital.org', hospital: 'Northside Heart Institute',
    status: 'Active', patients_count: 186, claims_count: 122, approval_rate: 85,
    joining_date: '2015-09-10', avatar_initials: 'JH', accent: 'bg-rose-500',
  },
  {
    provider_id: 'PRV-005', name: 'Dr. Linda Foster', specialty: 'Sports Medicine',
    department: 'Orthopedics', npi: '5678901234', phone: '(555) 200-1005',
    email: 'l.foster@hospital.org', hospital: 'Westside Orthopedics',
    status: 'Active', patients_count: 142, claims_count: 91, approval_rate: 93,
    joining_date: '2020-04-05', avatar_initials: 'LF', accent: 'bg-amber-500',
  },
  {
    provider_id: 'PRV-006', name: 'Dr. Angela Torres', specialty: 'Bariatric Surgery',
    department: 'General Surgery', npi: '6789012345', phone: '(555) 200-1006',
    email: 'a.torres@hospital.org', hospital: 'Lakeside Surgical Center',
    status: 'On Leave', patients_count: 76, claims_count: 48, approval_rate: 82,
    joining_date: '2021-11-01', avatar_initials: 'AT', accent: 'bg-indigo-500',
  },
  {
    provider_id: 'PRV-007', name: 'Dr. Samuel Grant', specialty: 'Internal Medicine',
    department: 'Internal Medicine', npi: '7890123456', phone: '(555) 200-1007',
    email: 's.grant@hospital.org', hospital: 'Metro Medical Center',
    status: 'Active', patients_count: 310, claims_count: 198, approval_rate: 80,
    joining_date: '2014-06-22', avatar_initials: 'SG', accent: 'bg-teal-500',
  },
  {
    provider_id: 'PRV-008', name: 'Dr. Rachel Bloom', specialty: 'Radiology',
    department: 'Radiology', npi: '8901234567', phone: '(555) 200-1008',
    email: 'r.bloom@hospital.org', hospital: 'City General Hospital',
    status: 'Active', patients_count: 0, claims_count: 234, approval_rate: 95,
    joining_date: '2016-02-14', avatar_initials: 'RB', accent: 'bg-cyan-500',
  },
  {
    provider_id: 'PRV-009', name: 'Dr. Thomas Wu', specialty: 'Pulmonology',
    department: 'Pulmonology', npi: '9012345678', phone: '(555) 200-1009',
    email: 't.wu@hospital.org', hospital: 'Eastside Clinic',
    status: 'Inactive', patients_count: 45, claims_count: 29, approval_rate: 72,
    joining_date: '2022-08-01', avatar_initials: 'TW', accent: 'bg-slate-500',
  },
];
