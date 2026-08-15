# CTS V1 — Clinical Testing System Simulation & Data Generation Framework

This repository contains the simulation and data generation pipeline for **CTS V1 (Clinical Testing System)** on branch `simulation-v1`.

The simulation framework generates realistic longitudinal clinical data, payer member records, evidence with provenance, temporal ordering, persisted multi-attempt resubmissions, and 8 genuine clinical decision scenarios backed by a genuine evidence-backed RAG policy criteria evaluation engine.

> [!IMPORTANT]
> **Architectural Boundary**: The simulation pipeline operates exclusively in `simulation/` and outputs to `DATA-VERSION1/`. Agent 1, RAG, API, services, and frontend code remain strictly untouched. Agent 1 receives payer decision context and claim data purely as in-memory structured objects (`CanonicalClaim` and `Payer Decision Context`).

---

## 📁 Repository Structure

```text
.
├── DATA-VERSION1/                            # Exported Deliverables
│   ├── big_patient_data.db                   # 13 Historical Patient Clinical Tables (SQLite)
│   ├── payer_data.db                         # 6 Payer-Side Member & Benefit Tables (SQLite)
│   ├── clinical_events_PA_ids.csv            # Event Export CSV
│   ├── final_patient_data_PA_ids_final.xlsx  # Excel Patient Events Export
│   └── SCENARIOS.md                          # Scenario Documentation
│
├── simulation/                               # Simulation & Data Generation Framework
│   ├── __init__.py
│   ├── policy_rag_dataset.json               # External RAG Policy Dataset (Single Source of Truth)
│   ├── db_patient.py                         # 13 Historical Patient DB Schemas & Generator
│   ├── db_payer.py                           # 6 Exact Payer DB Schemas & Generator
│   ├── linkage.py                            # Patient → Member → Payer → Plan → Policy RAG Loader
│   ├── evidence.py                           # Evidence Generation (Available vs Submitted + Provenance + Metrics)
│   ├── scenarios.py                          # 8 Data-Driven V1 Clinical Scenarios
│   ├── resubmissions.py                      # Dynamic RAG Policy Criteria Evaluation Engine
│   ├── adapter.py                            # Runtime Adapter (SQLite DBs → Structured In-Memory Objects)
│   ├── validator.py                          # Full V1 Validation Suite (PRAGMA Column Schema Assertions)
│   └── export.py                             # Deliverable Exporter Pipeline (With Persisted Resubmissions)
│
└── tests/
    └── test_simulation.py                    # Pytest & Unittest Test Suite (10 Test Cases)
```

---

## 🗄️ Database Schemas

### 1. Big Patient Data (`DATA-VERSION1/big_patient_data.db`)
Contains exactly **13 historical clinical tables**:

| # | Table Name | Key Columns |
|---|---|---|
| 1 | `patients` | `patient_id`, `name`, `dob`, `gender`, `address`, `insurance_id`, `created_at` |
| 2 | `encounters` | `encounter_id`, `patient_id`, `encounter_type`, `provider_id`, `start_date`, `end_date` |
| 3 | `conditions` | `condition_id`, `patient_id`, `icd10_code`, `condition_name`, `onset_date`, `status` |
| 4 | `observations` | `observation_id`, `patient_id`, `code`, `description`, `value`, `unit`, `observation_date` |
| 5 | `procedures` | `procedure_id`, `patient_id`, `cpt_code`, `description`, `procedure_date`, `status` |
| 6 | `medications` | `medication_id`, `patient_id`, `rxnorm_code`, `name`, `start_date`, `status` |
| 7 | `allergies` | `allergy_id`, `patient_id`, `substance`, `reaction`, `severity`, `onset_date` |
| 8 | `diagnostic_reports` | `report_id`, `patient_id`, `report_type`, `findings`, `report_date` |
| 9 | `clinical_documents` | `document_id`, `patient_id`, `title`, `doc_type`, `content`, `created_at` |
| 10 | `care_plans` | `care_plan_id`, `patient_id`, `title`, `start_date`, `end_date`, `status` |
| 11 | `evidence` | `evidence_id`, `patient_id`, `source_record_id`, `document_id`, `evidence_type`, `event_date`, `content_reference`, `provenance`, `is_submitted`, `kl_grade`, `pt_weeks_completed`, `neurological_deficit`, `abnormal_stress_test`, `refractory_angina` |
| 12 | `claims` | `claim_id`, `patient_id`, `payer_id`, `plan_id`, `requested_procedure`, `status` |
| 13 | `claim_submissions` | `submission_id`, `claim_id`, `attempt_number`, `submission_date`, `submitted_evidence_ids`, `status`, `notes` |

### 2. Payer Data (`DATA-VERSION1/payer_data.db`)
Preserves exact specified payer-side schemas:

| # | Table Name | Columns |
|---|---|---|
| 1 | `members` | `member_id`, `patient_id`, `payer_id`, `plan_id`, `coverage_status`, `coverage_start`, `coverage_end`, `plan_product` |
| 2 | `eligibility` | `eligibility_id`, `member_id`, `is_eligible`, `effective_date`, `termination_date` |
| 3 | `payer_claims` | `claim_id`, `member_id`, `service_date`, `provider_facility`, `claim_type`, `procedure_code`, `diagnosis_code`, `claim_status`, `allowed_amount`, `paid_amount`, `denial_reason` |
| 4 | `prior_authorizations` | `authorization_id`, `member_id`, `requested_service`, `diagnosis_code`, `provider`, `authorization_status`, `request_date`, `decision_date` |
| 5 | `utilization` | `utilization_id`, `member_id`, `service_type`, `units_used`, `limit_units` |
| 6 | `benefits` | `benefit_id`, `plan_id`, `service_category`, `copay`, `coinsurance`, `preauth_required` |

---

## 🧪 The 8 V1 Clinical Scenarios & Evaluated Criteria

| # | Scenario | Patient ID | Payer | Policy ID | Expected Result | Evaluated Criteria Reason |
|---|---|---|---|---|---|---|
| 1 | **Eligible** | `PA001` | Aetna | `AETNA_POL_KNEE_01` | `APPROVE` | KL Grade 4 (>=3) & PT 8 wks (>=6 wks required). All criteria satisfied. |
| 2 | **Failed criterion** | `PA002` | Aetna | `AETNA_POL_KNEE_01` | `REJECT` | Completed 1 week PT vs 6 weeks required (`pt_weeks_completed = 1 < 6`). |
| 3 | **Missing documentation** | `PA003` | CMS | `CMS_POL_MRI_02` | `REQUEST_MORE_INFORMATION` | Lumbar MRI policy requires 6 wks PT & progressive neurological deficit; PT notes omitted from submission. |
| 4 | **Conflicting evidence** | `PA004` | Aetna | `AETNA_POL_KNEE_01` | `HUMAN_REVIEW` | Doc A states Grade 4 OA, Doc B states Grade 1 No OA on same clinical fact. |
| 5 | **Unknown payer** | `PA005` | Unknown | N/A | `HUMAN_REVIEW` | Payer record cannot be resolved or linked for member. |
| 6 | **Multiple procedures** | `PA006` | Aetna | `AETNA_POL_KNEE_01` | `STRUCTURAL_VALIDATION_PASS` | Multiple procedure codes (27447 & 27487) preserved under single claim. |
| 7 | **RAG failure** | `PA007` | Aetna | `AETNA_POL_KNEE_01` (`intentional_rag_failure`) | `HUMAN_REVIEW` | RAG policy index retrieval genuinely fails with `RAGRetrievalError`. |
| 8 | **No policy constraint** | `PA008` | Aetna | N/A (`no_policy_established`) | `HUMAN_REVIEW` | Legitimate claim where no applicable policy can safely be established in RAG dataset. |

---

## 🔄 Dynamic Evidence-Backed Resubmission Evaluation

For Scenario 3 (`PA003`), multi-attempt resubmissions preserve claim identity while evaluating RAG policy criteria dynamically, and both attempts are persisted in `big_patient_data.db`:
- **Attempt 1 (`SUB_CLM_RESUB_PA003_ATT1`)**: `submitted_evidence_ids`: `EV_003_1` (Lumbar X-ray only) $\rightarrow$ Evaluator checks `min_pt_weeks = 6` $\rightarrow$ Missing required PT evidence $\rightarrow$ `REQUEST_MORE_INFORMATION`
- **Attempt 2 (`SUB_CLM_RESUB_PA003_ATT2`)**: `submitted_evidence_ids`: `EV_003_1,EV_RESUB_PA003_PT` under same claim ID (`CLM_RESUB_PA003`) $\rightarrow$ Evaluates `pt_weeks_completed = 6 (>=6)` $\rightarrow$ All criteria satisfied $\rightarrow$ `APPROVE`

---

## 🚀 Execution & Verification Commands

### 1. Export Deliverables
```powershell
python -m simulation.export
```

### 2. Run Full V1 Validation Suite
```powershell
python -m simulation.validator
```

### 3. Run Pytest Test Suite
```powershell
python -m pytest
```

### 4. Verify Repository Boundary & Commit Status
```powershell
git status
git log -1 --oneline
git diff mock...simulation-v1 -- decision rag services api frontend
```

---

## 📊 Actual Validation Output Log

```text
Export completed successfully to DATA-VERSION1/
=== FULL V1 SIMULATION VALIDATION PASSED ===
Total Patients: 8
Aetna Patients: 6
CMS Patients: 1
Valid Payer Linkages: 7
Claims Validated: 8
Evidence Records Validated: 11
Cross-patient Contamination: False
Total Validation Assertions Executed: 217
All required V1 validation checks & column schema PRAGMAs PASSED.

============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\motup\OneDrive\Documents\project
collected 10 items

tests\test_simulation.py ..........                                      [100%]

============================= 10 passed in 1.04s ==============================
```
