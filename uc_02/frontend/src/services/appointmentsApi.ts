import { mockRequest } from './api';
import { mockAppointments } from '../mock/appointments';
import type { Appointment } from '../types/appointment';

let store: Appointment[] = [...mockAppointments];

export async function getAppointments(): Promise<Appointment[]> {
  return mockRequest([...store]);
}

export async function createAppointment(appt: Omit<Appointment, 'appointment_id'>): Promise<Appointment> {
  const newAppt: Appointment = {
    ...appt,
    appointment_id: `APT-${String(store.length + 1).padStart(3, '0')}`,
  };
  store = [newAppt, ...store];
  return mockRequest(newAppt, 400);
}

export async function updateAppointmentStatus(id: string, status: Appointment['status']): Promise<Appointment> {
  const idx = store.findIndex(a => a.appointment_id === id);
  if (idx !== -1) store[idx] = { ...store[idx], status };
  return mockRequest({ ...store[idx] }, 300);
}

export async function cancelAppointment(id: string): Promise<{ success: boolean }> {
  const idx = store.findIndex(a => a.appointment_id === id);
  if (idx !== -1) store[idx] = { ...store[idx], status: 'Cancelled' };
  return mockRequest({ success: true }, 300);
}
