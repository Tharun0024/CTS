import type { Appointment } from '../types/appointment';

export const mockAppointments: Appointment[] = [
  {
    appointment_id: 'APT-001', patient_id: 'PAT-001', patient_name: 'John Mitchell',
    provider_id: 'PRV-001', provider_name: 'Dr. Karen Ellis', specialty: 'Orthopedic Surgery',
    type: 'Follow-up', date: '2026-08-14', time: '09:00', duration_minutes: 30,
    status: 'Scheduled', room: 'OPD-3A', notes: 'Pre-op evaluation for knee replacement', priority: 'Normal',
  },
  {
    appointment_id: 'APT-002', patient_id: 'PAT-004', patient_name: 'Eleanor Walsh',
    provider_id: 'PRV-004', provider_name: 'Dr. James Hartley', specialty: 'Cardiology',
    type: 'Consultation', date: '2026-08-13', time: '10:30', duration_minutes: 45,
    status: 'In Progress', room: 'CARD-1B', notes: 'Cardiac catheterization discussion', priority: 'Urgent',
  },
  {
    appointment_id: 'APT-003', patient_id: 'PAT-005', patient_name: 'David Park',
    provider_id: 'PRV-005', provider_name: 'Dr. Linda Foster', specialty: 'Sports Medicine',
    type: 'Procedure', date: '2026-08-13', time: '14:00', duration_minutes: 90,
    status: 'Scheduled', room: 'OR-2', notes: 'Shoulder arthroscopy pre-op', priority: 'Normal',
  },
  {
    appointment_id: 'APT-004', patient_id: 'PAT-002', patient_name: 'Sarah Thompson',
    provider_id: 'PRV-002', provider_name: 'Dr. Marcus Reid', specialty: 'Spinal Surgery',
    type: 'Consultation', date: '2026-08-12', time: '11:00', duration_minutes: 60,
    status: 'Completed', room: 'NSG-2A', notes: 'Lumbar spinal fusion review', priority: 'Normal',
  },
  {
    appointment_id: 'APT-005', patient_id: 'PAT-003', patient_name: 'Robert Chen',
    provider_id: 'PRV-003', provider_name: 'Dr. Priya Nair', specialty: 'Gastroenterology',
    type: 'Lab', date: '2026-08-12', time: '08:00', duration_minutes: 20,
    status: 'Completed', room: 'LAB-A', notes: 'CBC + CMP lab draw', priority: 'Normal',
  },
  {
    appointment_id: 'APT-006', patient_id: 'PAT-006', patient_name: 'Linda Reyes',
    provider_id: 'PRV-006', provider_name: 'Dr. Angela Torres', specialty: 'Bariatric Surgery',
    type: 'Consultation', date: '2026-08-15', time: '13:00', duration_minutes: 45,
    status: 'Scheduled', room: 'SRG-1A', notes: 'Bariatric surgery pre-assessment', priority: 'Normal',
  },
  {
    appointment_id: 'APT-007', patient_id: 'PAT-007', patient_name: 'Marcus Johnson',
    provider_id: 'PRV-002', provider_name: 'Dr. Marcus Reid', specialty: 'Spinal Surgery',
    type: 'Follow-up', date: '2026-08-16', time: '09:30', duration_minutes: 30,
    status: 'Scheduled', room: 'NSG-2B', notes: 'Resubmission status review', priority: 'Normal',
  },
  {
    appointment_id: 'APT-008', patient_id: 'PAT-008', patient_name: 'Patricia Novak',
    provider_id: 'PRV-001', provider_name: 'Dr. Karen Ellis', specialty: 'Orthopedic Surgery',
    type: 'Procedure', date: '2026-08-18', time: '07:30', duration_minutes: 120,
    status: 'Scheduled', room: 'OR-1', notes: 'Hip replacement surgery', priority: 'Normal',
  },
  {
    appointment_id: 'APT-009', patient_id: 'PAT-010', patient_name: 'Angela Kim',
    provider_id: 'PRV-004', provider_name: 'Dr. James Hartley', specialty: 'Cardiology',
    type: 'Imaging', date: '2026-08-11', time: '10:00', duration_minutes: 30,
    status: 'No Show', room: 'IMG-B2', notes: 'Echocardiogram', priority: 'Normal',
  },
  {
    appointment_id: 'APT-010', patient_id: 'PAT-012', patient_name: 'Dorothy Singh',
    provider_id: 'PRV-007', provider_name: 'Dr. Samuel Grant', specialty: 'Internal Medicine',
    type: 'Emergency', date: '2026-08-13', time: '08:45', duration_minutes: 60,
    status: 'In Progress', room: 'ER-3', notes: 'COPD exacerbation', priority: 'Emergency',
  },
  {
    appointment_id: 'APT-011', patient_id: 'PAT-009', patient_name: "James O'Brien",
    provider_id: 'PRV-005', provider_name: 'Dr. Linda Foster', specialty: 'Sports Medicine',
    type: 'Consultation', date: '2026-08-14', time: '15:00', duration_minutes: 30,
    status: 'Scheduled', room: 'OPD-2B', notes: 'Pre-op knee arthroscopy', priority: 'Normal',
  },
  {
    appointment_id: 'APT-012', patient_id: 'PAT-011', patient_name: 'Carlos Mendes',
    provider_id: 'PRV-003', provider_name: 'Dr. Priya Nair', specialty: 'Gastroenterology',
    type: 'Follow-up', date: '2026-08-10', time: '12:00', duration_minutes: 20,
    status: 'Cancelled', room: 'GASTRO-1', notes: 'Diabetes management', priority: 'Normal',
  },
];
