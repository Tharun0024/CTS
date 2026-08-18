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

---

## 5. Final Synchronization, Unlimited Simulation & Dashboard Cleanups

- **Unlimited Simulation Loop**: Configured the simulation worker in [`api/simulation/manager.py`](file:///y:/CTS/api/simulation/manager.py) to execute indefinitely using `itertools.count()` when the request count is set to `None`. Patients are generated dynamically on the fly during iteration.
- **Upfront Generation for Fixed Runs**: Maintained synchronous upfront patient list initialization in [`api/simulation/manager.py`](file:///y:/CTS/api/simulation/manager.py) if a specific `count` is requested, guaranteeing complete compatibility with the contract test suite.
- **Globally Unique IDs**: Used full 32-character hex UUID generation for `simulation_id` and removed `self._issued_patient_ids.clear()` to ensure all generated IDs (patient, claim, correlation, evidence, documents) remain globally unique and never get recycled.
- **SQLite Targeted Cascaded Deletes**: Updated `delete()` in [`api/persistence/sqlite.py`](file:///y:/CTS/api/persistence/sqlite.py) to enable SQLite foreign keys (`PRAGMA foreign_keys = ON;`) and execute targeted deletions of only simulation-scoped claims and event history, leaving manual claims completely untouched.
- **Human Reentry Outcomes**: Updated [`HospitalHumanResolutionPanel.tsx`](file:///y:/CTS/uc_02/frontend/src/components/hospital/HospitalHumanResolutionPanel.tsx) to provide both "Approve Claim" and "Reject Claim" buttons, passing the chosen recommendation in the manual note to the backend V1 reentry pipeline.
- **Recalculated Dashboard KPI Stats**:
  - Restructured statistics grids in [`HospitalDashboard.tsx`](file:///y:/CTS/uc_02/frontend/src/pages/hospital/HospitalDashboard.tsx) and [`InsuranceDashboard.tsx`](file:///y:/CTS/uc_02/frontend/src/pages/insurance/InsuranceDashboard.tsx) to calculate counts and rates dynamically from the live claims list, eliminating hardcoded fallbacks and double counting.
  - Cards map to Total, Approved (`ACCEPTED`), Processing (`PROCESSING`, `UNDER_REVIEW`, `SUBMITTED`, `SUBMITTED_AGAIN`, `RESUBMISSION_CHECK`, `DRAFT`), Needs Info (`MORE_INFO`), Denied (`REJECTED`), and Human Review (`HUMAN_REVIEW`).
- **Segregated Review Workspaces**: Split the layout in [`HumanReviewWorkspace.tsx`](file:///y:/CTS/uc_02/frontend/src/components/shared/HumanReviewWorkspace.tsx) into dedicated sub-screens for **Agent 1 Clinical Holds** (showing evaluated criteria statuses, clinical rationale, evidence ledger, and provenance) and **Agent 2 Holds** (showing crawler recovery states, sensitive data blocks, and provider consent decisions).
- **Cleaned Mock Visualizations**: Removed the static "Priority Claims" card section entirely from the Hospital dashboard, ensuring the view remains clean and derived strictly from live backend records.

---

## 6. Final Database Purges & Role-Gated Reviews

- **Purged 5 Old Demo Claims**: Deleted `CLM-API-F9B7F3F5`, `CLM-API-4267D2A0`, `CLM-API-2F07A9FC`, `CLM-API-DD148D02`, and `CLM-API-EBED40F8` from the SQLite persistence (`claim_records` and `agent2_audit` tables). Dasboards now start at exactly 0 claims with no stale entries.
- **Role-Gated Review Controls**:
  - Removed interactive resolution forms from the Insurance portal ([`InsuranceClaimDetails.tsx`](file:///y:/CTS/uc_02/frontend/src/pages/insurance/InsuranceClaimDetails.tsx) and [`ReviewDetail.tsx`](file:///y:/CTS/uc_02/frontend/src/pages/insurance/ReviewDetail.tsx)) to establish the Hospital side as the single source of truth for resolving reviews.
  - Insurers view human review claims with read-only banners: **Hospital Clinical Resolution Pending** (for Agent 1 holds) and **Provider/Hospital Resolution Pending** (for Agent 2 holds).
- **Cache Invalidation**: Hooked `clearClaimsCache()` and `clearReviewsCache()` inside [`HospitalHumanResolutionPanel.tsx`](file:///y:/CTS/uc_02/frontend/src/components/hospital/HospitalHumanResolutionPanel.tsx) to run immediately after a human resolution is submitted.
- **Detailed Clinical Reasoning**: Allowed [`HumanReviewWorkspace.tsx`](file:///y:/CTS/uc_02/frontend/src/components/shared/HumanReviewWorkspace.tsx) to fallback to the real `decision.reason` string returned by the backend RAG evaluation, preventing generic text overlays.

---

## 7. Reentry Timeline Resolution Checks (Uvicorn Synchronization Fix)

- **Manual Resolution Event Check**: Configured the RAG pipeline classifier in [`services/integrated_pipeline.py`](file:///y:/CTS/services/integrated_pipeline.py) to check the claim's timeline for an active `ClaimWorkflowState.RESOLVED_REENTRY` event when evaluation results in `HUMAN_REVIEW`.
- **Authoritative Resolution Propagation**: If a resolution event is found, it parses the note for the human's choice (`APPROVE` or `REJECT`) and transitions the control plane to the terminal `APPROVED` or `REJECTED` state. Subsequent `GET` requests read and display this terminal outcome, syncing both dashboards immediately with no reversion or duplicate action controls.

---

## 8. Persistent SQLite Storage for Simulation Manager (404 Prevention)

- **Simulation Claim Persistence**: Configured `SimulationManager` in [`api/main.py`](file:///y:/CTS/api/main.py) with a `claim_service_factory` (`make_sim_claim_service`) that maps all active runtimes to save their claim entries and timeline events to the SQLite database (`agent2.db`).
- **Inactive/Restart Lookup Fallbacks**: Enhanced `claims()` and `delete()` in [`api/simulation/manager.py`](file:///y:/CTS/api/simulation/manager.py) to look up and resolve simulation claims in the SQLite simulation and claim stores as a fallback when in-memory runtimes are empty (e.g. after a backend restart).
- **Restart Immunity**: Simulation-scoped claim records, clinical metrics, and timelines are preserved across Uvicorn process restarts, preventing `404 Not Found` errors in the user's browser session.




