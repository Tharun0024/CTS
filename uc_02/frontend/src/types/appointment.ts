export interface Appointment {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  provider_id: string;
  provider_name: string;
  specialty: string;
  type: 'Consultation' | 'Follow-up' | 'Procedure' | 'Lab' | 'Imaging' | 'Emergency';
  date: string;
  time: string;
  duration_minutes: number;
  status: 'Scheduled' | 'Completed' | 'Cancelled' | 'No Show' | 'In Progress';
  room?: string;
  notes?: string;
  priority: 'Normal' | 'Urgent' | 'Emergency';
}
