import { mockRequest } from './api';
import { mockProviders } from '../mock/providers';
import type { Provider } from '../types/provider';

let providersStore: Provider[] = [...mockProviders];

export async function getProviders(): Promise<Provider[]> {
  return mockRequest([...providersStore]);
}

export async function getProvider(id: string): Promise<Provider> {
  const p = providersStore.find(x => x.provider_id === id);
  if (!p) throw new Error(`Provider ${id} not found`);
  return mockRequest({ ...p });
}
