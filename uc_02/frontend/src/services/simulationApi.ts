import { apiFetch } from './api';

interface StartSimulationRequest {
  source: string;
}

interface StartSimulationResponse {
  success: boolean;
  message: string;
  run_id?: string;
}

// POST /api/simulation/start
export async function startSimulationTrigger(
  payload: StartSimulationRequest
): Promise<StartSimulationResponse> {
  return apiFetch<StartSimulationResponse>('/simulation/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
