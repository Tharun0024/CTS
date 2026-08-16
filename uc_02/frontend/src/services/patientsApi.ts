import { mockRequest } from './api';
import { mockPatients } from '../mock/patients';
import type { Patient } from '../types/patient';

let patientsStore: Patient[] = [...mockPatients];

export async function getPatients(): Promise<Patient[]> {
  return mockRequest([...patientsStore]);
}

export async function getPatient(id: string): Promise<Patient> {
  const p = patientsStore.find(x => x.patient_id === id);
  if (!p) throw new Error(`Patient ${id} not found`);
  return mockRequest({ ...p });
}

export async function updatePatient(id: string, patch: Partial<Patient>): Promise<Patient> {
  const idx = patientsStore.findIndex(x => x.patient_id === id);
  if (idx !== -1) patientsStore[idx] = { ...patientsStore[idx], ...patch };
  return mockRequest({ ...patientsStore[idx] });
}
