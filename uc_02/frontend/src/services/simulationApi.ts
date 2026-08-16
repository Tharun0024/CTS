import { mockRequest } from './api';
import { getClaimsStore, saveClaimsStore } from './claimsApi';
import type { ClaimDetails } from '../types/claim';

interface StartSimulationRequest {
  source: string;
}

interface StartSimulationResponse {
  success: boolean;
  message: string;
  run_id?: string;
}

// POST /api/simulation/start - Mocked version for frontend-only mode
export async function startSimulationTrigger(
  _payload: StartSimulationRequest
): Promise<StartSimulationResponse> {
  const store = getClaimsStore();
  
  // Generate a new simulated claim ID
  const simId = `CLM-SIM-${String(store.length + 1).padStart(3, '0')}`;
  
  const simClaim: ClaimDetails = {
    claim_id: simId,
    patient: {
      patient_id: 'PAT-SIM-099',
      name: 'Simulated Patient (RAG Case)',
      age: 62,
      gender: 'Female',
    },
    claim: {
      procedure: 'Implantable Cardioverter Defibrillator (ICD)',
      procedure_code: '33249',
      diagnosis_codes: ['I50.9', 'I47.2'],
      service_date: new Date().toISOString().split('T')[0],
      provider_id: 'PRV-SIM-01',
    },
    policy: {
      payer: 'CMS',
      policy_id: 'NCD-20.4',
      policy_name: 'NCD 20.4 – Implantable Cardioverter Defibrillators (ICDs)',
    },
    decision: null,
    status: 'PROCESSING',
    attempt: 1,
    submission_history: [
      {
        attempt: 1,
        submitted_at: new Date().toISOString(),
        status: 'SUBMITTED',
        note: 'Triggered via CMS Medicare simulation scenario.',
      }
    ],
    policy_evidence: [
      { criterion: 'Prior MI documented (>40 days)', patient_value: 'MI documented 60 days ago', status: 'MET', source: 'Discharge Summary 2026-06-12' },
      { criterion: 'LVEF ≤ 35% on optimal medical therapy', patient_value: 'Echo shows LVEF 30%', status: 'MET', source: 'Cardiology Report 2026-07-30' },
      { criterion: 'NYHA Class II or III heart failure symptoms', patient_value: 'NYHA Class III symptoms present', status: 'MET', source: 'Clinical notes' },
    ],
    missing_information: [],
    resubmission: { eligible: false, status: 'NOT_REQUIRED' },
    evidence_request: null,
    evidence_response: null,
    evidence_request_status: 'CLOSED',
    resubmission_status: 'NOT_REQUIRED',
    agent2_result: null,
    reevaluation_status: null,
    submitted_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    hospital: 'City General Hospital',
    documents: [
      { document_id: 'DOC-SIM-1', file_name: 'echocardiogram.pdf', file_type: 'application/pdf', uploaded_at: new Date().toISOString() },
    ],
    timeline: [
      { timestamp: new Date().toISOString(), event: 'SUBMITTED', message: 'Simulated claim created' },
      { timestamp: new Date().toISOString(), event: 'PROCESSING', message: 'Running Agent 1 initial check against CMS policy NCD-20.4...' }
    ],
  };

  // Push to local store and save
  const newStore = [simClaim, ...store];
  saveClaimsStore(newStore);

  // Transition to a state after a brief delay
  setTimeout(() => {
    const liveStore = getClaimsStore();
    const idx = liveStore.findIndex(c => c.claim_id === simId);
    if (idx !== -1) {
      liveStore[idx] = {
        ...liveStore[idx],
        status: 'ACCEPTED',
        decision: {
          status: 'ACCEPT',
          reason: 'All criteria for NCD 20.4 (LVEF <= 35%, post-MI period, and NYHA class symptoms) are met.',
          reason_code: 'CRITERIA_MET',
        },
        updated_at: new Date().toISOString(),
        timeline: [
          ...(liveStore[idx].timeline ?? []),
          { timestamp: new Date().toISOString(), event: 'ACCEPTED', message: 'Agent 1 decision: APPROVE (Criteria Met)' }
        ]
      };
      saveClaimsStore(liveStore);
    }
  }, 4000);

  return mockRequest({
    success: true,
    message: `V1 Simulation started: Created ${simId} (ICD replacement under CMS NCD-20.4 policy). Evaluated by Agent 1.`,
    run_id: `SIM-RUN-${Math.floor(Math.random() * 10000)}`,
  }, 800);
}
