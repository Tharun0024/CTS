// Base API utility — wraps fetch and adds artificial delay for mock mode.
// To switch to real backend: replace `mockRequest` with real `fetch` calls
// in each service file. This file's `delay` helper can be removed.

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export function delay(ms = 400): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export interface ApiError {
  message: string;
  status?: number;
}

// Real fetch wrapper (used when VITE_API_BASE_URL is set)
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Unknown error' }));
    throw { message: err.message ?? res.statusText, status: res.status } as ApiError;
  }
  return res.json() as Promise<T>;
}

// Mock request helper — simulates network latency and returns mock data
export async function mockRequest<T>(data: T, ms = 400): Promise<T> {
  await delay(ms);
  return data;
}
