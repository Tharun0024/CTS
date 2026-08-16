// Simulation API service — Phase 6: wired to the real FastAPI V1 boundary
// (Phase 5B Simulation Manager). Lifecycle control and state are owned by the
// backend; the frontend only triggers and reads via these endpoints.

import { apiFetch } from './api';

interface StartSimulationRequest {
  source: string;
  count?: number;
}

interface StartSimulationResponse {
  success: boolean;
  message: string;
  run_id?: string;
}

export interface SimulationPatient {
  patient_id: string;
  claim_id?: string;
  scenario?: string;
  status?: string;
  decision_outcome?: string | null;
  decision_status?: string | null;
  claim_status?: string | null;
  duration_seconds?: number | null;
  documents?: unknown[];
}

export interface SimulationStatus {
  simulation_id?: string;
  status?: string;
  total_count?: number;
  completed_count?: number;
  patients?: SimulationPatient[];
  timing?: Record<string, unknown>;
  [key: string]: unknown;
}

// POST /api/simulation/start
export async function startSimulationTrigger(
  payload: StartSimulationRequest
): Promise<StartSimulationResponse> {
  try {
    return await apiFetch<StartSimulationResponse>('/simulation/start', {
      method: 'POST',
      body: JSON.stringify({
        source: payload.source,
        count: payload.count ?? 5,
      }),
    });
  } catch (error) {
    const message = (error as { message?: string }).message ?? 'Failed to start simulation.';
    return { success: false, message };
  }
}

// GET /api/simulation/status (optionally for a specific run)
export async function getSimulationStatus(simulationId?: string): Promise<SimulationStatus> {
  const query = simulationId ? `?simulation_id=${encodeURIComponent(simulationId)}` : '';
  return apiFetch<SimulationStatus>(`/simulation/status${query}`);
}

// GET /api/simulation — all run summaries
export async function listSimulations(): Promise<unknown[]> {
  const body = await apiFetch<{ simulations?: unknown[] } | unknown[]>('/simulation');
  return Array.isArray(body) ? body : (body.simulations ?? []);
}

// POST /api/simulation/stop
export async function stopSimulation(simulationId?: string): Promise<unknown> {
  const query = simulationId ? `?simulation_id=${encodeURIComponent(simulationId)}` : '';
  return apiFetch(`/simulation/stop${query}`, { method: 'POST' });
}

// POST /api/simulation/reset
export async function resetSimulation(simulationId?: string): Promise<unknown> {
  const query = simulationId ? `?simulation_id=${encodeURIComponent(simulationId)}` : '';
  return apiFetch(`/simulation/reset${query}`, { method: 'POST' });
}

// DELETE /api/simulation/{simulation_id}
export async function deleteSimulation(simulationId: string): Promise<unknown> {
  return apiFetch(`/simulation/${encodeURIComponent(simulationId)}`, { method: 'DELETE' });
}

// POST /api/simulation/{simulation_id}/resimulate
export async function resimulateSimulation(simulationId: string): Promise<unknown> {
  return apiFetch(`/simulation/${encodeURIComponent(simulationId)}/resimulate`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}
