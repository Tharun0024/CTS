import { mockRequest } from './api';
import { mockInsurerAdministrativeData } from '../mock/insurerAdministrative';
import type { InsurerAdministrativeData } from '../types/insurerAdministrative';

let store: InsurerAdministrativeData[] = [...mockInsurerAdministrativeData];

export async function getInsurerAdministrativeDataList(): Promise<InsurerAdministrativeData[]> {
  return mockRequest([...store]);
}

export async function getInsurerAdministrativeDataByPatient(patientId: string): Promise<InsurerAdministrativeData> {
  const data = store.find(d => d.patient_id === patientId);
  if (!data) throw new Error(`Administrative data for patient ${patientId} not found`);
  return mockRequest({ ...data });
}

export async function updateInsurerAdministrativeData(
  patientId: string,
  patch: Partial<InsurerAdministrativeData>
): Promise<InsurerAdministrativeData> {
  const idx = store.findIndex(d => d.patient_id === patientId);
  if (idx !== -1) {
    store[idx] = { ...store[idx], ...patch };
    return mockRequest({ ...store[idx] });
  }
  throw new Error(`Patient ${patientId} not found to update administrative data`);
}
