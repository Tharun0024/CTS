import { mockRequest } from './api';
import { mockAuthorizations } from '../mock/authorizations';
import type { Authorization } from '../mock/authorizations';

export type { Authorization };

let store: Authorization[] = [...mockAuthorizations];

export async function getAuthorizations(): Promise<Authorization[]> {
  return mockRequest([...store]);
}

export async function getAuthorization(id: string): Promise<Authorization> {
  const a = store.find(x => x.auth_id === id);
  if (!a) throw new Error(`Authorization ${id} not found`);
  return mockRequest({ ...a });
}

export async function updateAuthorizationStatus(
  id: string,
  status: Authorization['status'],
  auth_number?: string
): Promise<Authorization> {
  const idx = store.findIndex(x => x.auth_id === id);
  if (idx !== -1) {
    store[idx] = {
      ...store[idx],
      status,
      ...(auth_number ? { auth_number } : {}),
      updated_at: new Date().toISOString(),
    };
  }
  return mockRequest({ ...store[idx] }, 400);
}
