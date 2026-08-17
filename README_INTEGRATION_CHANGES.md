# Integration Changes - V1 Workflow & Cockpit Alignment

This document outlines the full suite of changes made during this session to align the Hospital and Insurance dashboards with the V1 backend API architecture, ensuring high-fidelity patient demographics, clean RAG policy lookups, detailed human-in-the-loop review workspaces, targeted resets, and paced simulations.

---

## 1. Backend Changes (FastAPI V1 Service)

- **GET `/api/policies/{policy_id}` Endpoint**: Added in [`api/main.py`](file:///y:/CTS/api/main.py) to dynamically load and return aggregated policy criteria, title, payer, exclusions, and limitations from the real normalized RAG corpus (`data/normalized/normalized_policies.json`) without fabricating records.
- **Enriched Decision Serialization**: Updated `serialize_decision` in [`api/claims/mapping.py`](file:///y:/CTS/api/claims/mapping.py) to parse and include `criteria_results`, `criteria_evaluations`, `referenced_evidence_ids`, and `criterion_assessments` from `DecisionResponse` models.
- **Simulated Patient Demographic Generator**: Replaced `make_patient` in [`api/simulation/generator.py`](file:///y:/CTS/api/simulation/generator.py) to deterministicly generate realistic demographics: calculated DOB, gender, address, contact, relationship, and policy holder. Added dynamic policy-family mapping (Aetna to `CPB-0660`, CMS to `LCD-L36575`).
- **Global ID Uniqueness**: Extended UUID slices to 12 hex characters in [`api/simulation/manager.py`](file:///y:/CTS/api/simulation/manager.py) to prevent any key collisions across simulations.
- **Isolated Simulation Resets**: Configured `delete()` and `reset()` in [`api/simulation/manager.py`](file:///y:/CTS/api/simulation/manager.py) to stop the target run thread, clear memory runtimes, and delete only its respective claims/patients from the stores without deleting unrelated manual or simulation data. Enforced `SimulationNotFound` raise if no simulations exist during a reset request.

---

## 2. Frontend Services & Types (uc_02/frontend)

- **Extended Types**: Added demographic fields and RAG evaluation fields to `ClaimDetails['patient']` and `ClaimDecision` in [`src/types/claim.ts`](file:///y:/CTS/uc_02/frontend/src/types/claim.ts).
- **Adapter Mapping**: Propagated demographics from clinical metrics and serialized decision fields in `toClaimDetails` inside [`src/services/backendAdapter.ts`](file:///y:/CTS/uc_02/frontend/src/services/backendAdapter.ts).
- **Simulation Control API**: Modified `resetSimulation` in [`src/services/simulationApi.ts`](file:///y:/CTS/uc_02/frontend/src/services/simulationApi.ts) to support an optional `simulationId` query parameter for targeted resets. Set `pause_seconds: 45.0` in `startSimulationTrigger` for paced UI runs (while keeping test schemas fast). Added `listSimulations()` to fetch all runs.
- **Humanized Decisions**: Refactored `humanizeDecision` in [`src/utils/decisionHumanizer.ts`](file:///y:/CTS/uc_02/frontend/src/utils/decisionHumanizer.ts) to construct the multi-line structured explanation on `HUMAN_REVIEW` decisions.

---

## 3. Frontend UI Components

- **`<PolicyModal>` Component ([NEW])**: Created in [`src/components/shared/PolicyModal.tsx`](file:///y:/CTS/uc_02/frontend/src/components/shared/PolicyModal.tsx) to query GET `/api/policies/{policy_id}` and display structured clinical domain criteria, exclusions, and limitations. Integrated into `ClaimDetails.tsx` and `InsuranceClaimDetails.tsx`.
- **`<HumanReviewWorkspace>` Component ([NEW])**: Created in [`src/components/shared/HumanReviewWorkspace.tsx`](file:///y:/CTS/uc_02/frontend/src/components/shared/HumanReviewWorkspace.tsx) to present the clinical audit cockpit. It lists:
  - Agent 1 recommendation outcome, reason, and reason code.
  - Identification of Agent1 Clinical holds vs Agent2 Recovery holds.
  - Criterion status list with supporting evidence values and provenance (source document).
  - Missing or uncertain details.
  - Why automation stopped and recommended actions.
  - If Agent 2 recovery was run: requested items list, FOUND vs MISSING crawler status, provider release consent choice (ACCEPT/DECLINE), and Agent 2 exit reasons.
  - Integrated into Hospital details, Insurance details, and review detail pages.
- **`<HospitalHumanResolutionPanel>` Component ([NEW])**: Created in [`src/components/hospital/HospitalHumanResolutionPanel.tsx`](file:///y:/CTS/uc_02/frontend/src/components/hospital/HospitalHumanResolutionPanel.tsx) to let providers manually resolve `HUMAN_REVIEW` holds by submitting a resolution note to `POST /api/claims/{id}/human-resolution` (reentry flow).
- **Patient Info Display**: Updated [`src/components/shared/PatientInfoCard.tsx`](file:///y:/CTS/uc_02/frontend/src/components/shared/PatientInfoCard.tsx) to map and display DOB, contact, address, relationship, and policyholder rows.

---

## 4. Frontend Pages (V1 Alignment & Gating)

- **`InsuranceClaimDetails.tsx`**: 
  - Gated the manual `DecisionPanel` so human review overrides appear only when the actual workflow status is `HUMAN_REVIEW`.
  - Added `ClaimTimeline` rendering to present the live backend control plane timeline.
  - Integrated `<HumanReviewWorkspace>` panel.
  - Refreshes the claim details and timeline on decision submission.
- **`ReviewDetail.tsx`**: Integrated the `<HumanReviewWorkspace>` panel to present the complete recovery and consent context.
- **`ClaimDetails.tsx` (Hospital)**: Integrated `<HumanReviewWorkspace>` and `<HospitalHumanResolutionPanel>` for resolving holds.
- **`HospitalDashboard.tsx`**: Added a select box in the simulation control card listing all runs. Update the reset button handler to reset only the selected simulation run.
