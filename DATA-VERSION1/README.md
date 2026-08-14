# Prior Authorization Claim Ingestion & Simulation Pipeline (Version-1)

Welcome to the Prior Authorization (PA) Claim Ingestion & Simulation Pipeline. This system simulates the clinical prior authorization workflow under a strict **Provider ↔ Payer trust boundary**.

---

## 1. Directory Structure

All code, data files, and database outputs are self-contained in this folder:

```text
prior_auth_project/
│
├── final_patient_data_PA_IDs_final.xlsx # Raw patient demographics spreadsheet
├── clinical_events_PA_ids.csv           # Raw longitudinal clinical history CSV
├── prior_authorization_policies.xlsx    # Insurer policy rules configuration
│
├── big_patient_data.db                  # Provider Clinical Database (SQLite)
├── payer_data.db                        # Payer Administrative Database (SQLite)
│
├── Aetna_Knee_Arthroplasty_PA_Input.pdf # Sample clinical patient PDF
├── SC02_Missing_Documentation.pdf       # Scenario PDF
├── ... (SC03 to SC07 PDFs)              # Scenario PDF
│
├── pa_pipeline/                         # Python Source Package
│   ├── database/
│   │   └── db_manager.py                # Schema initialization, routing & database helpers
│   ├── ingestion/
│   │   ├── ingest_data.py               # Bulk clinical loader & Payer administrative generator
│   │   └── manual_parser.py             # Parses manual clinical patient PDFs into clinical tables
│   ├── simulation/
│   │   ├── scenario_generator.py        # Synthesizes clinical scenarios (COMPLETE, EVIDENCE_OMITTED, etc.)
│   │   └── simulation.py                # Standard simulation loop (supports random seeds)
│   ├── transformation/
│   │   ├── canonical_claim.py           # Exports normalized decision-free claims to output/
│   │   └── rag_input.py                 # Exports context payloads to output/
│   └── pipeline_main.py                 # Core CLI entry point
│
└── output/                              # Generated JSON Output Directory
    ├── canonical_claim_<id>.json        # Consumed by Tharun's Decision Agent
    └── rag_input_<id>.json              # Consumed by Thirumalai's RAG Retriever
```

---

## 2. Requirements & Setup

Make sure you have Python 3 installed. Navigate to the project directory and install the required dependencies:

```powershell
cd C:\Users\swaro\Downloads\prior_auth_project
pip install pandas openpyxl pdfplumber
```

---

## 3. How to Run the Commands

You can control all aspects of the pipeline using the central CLI command:

### 1. Ingest raw spreadsheets (Run once to set up databases)
This loads and structures provider clinical events into normalized tables and independently initializes/populates the synthetic payer administrative dataset in `payer_data.db`. The payer dataset is not a copy or transformation of the provider's complete clinical record.
```powershell
python pa_pipeline/pipeline_main.py ingest
```

### 2. Run deterministic simulation for a specific patient
Simulates clinical facts, writes them to the correct normalized tables, applies sensitivity/provenance metadata, and submits Attempt 1.
```powershell
python pa_pipeline/pipeline_main.py run-simulation --patient-id PA045 --scenario-type EVIDENCE_OMITTED
```
*   **Available scenario types**: `COMPLETE`, `INCOMPLETE`, `AMBIGUOUS`, and `EVIDENCE_OMITTED`.

### 3. Run a simulation sequence with a seed (For demos)
Cycles through a set number of random patients in a reproducible sequence using a seeded random index.
```powershell
python pa_pipeline/pipeline_main.py run-simulation --limit 5 --interval-seconds 3 --seed 123
```

### 4. Process a manual clinical patient PDF
Parses patient demographics, CPT codes, and conservative treatment records directly from a clinical PDF into the database, generating the outputs immediately.
```powershell
python pa_pipeline/pipeline_main.py process-manual --file Aetna_Knee_Arthroplasty_PA_Input.pdf
```

---

## 4. Trust Boundary & Database Layout

To enforce the **Provider ↔ Payer trust boundary**, data sets are kept physically separate:

```text
  [PROVIDER SYSTEM]                           [PAYER SYSTEM]
+--------------------------+                +-------------------------+
| big_patient_data.db      |                | payer_data.db           |
| (Full Longitudinal Care) |                | (Eligibility & Claims)  |
| - conditions             |                | - members               |
| - observations           |                | - eligibility           |
| - procedures             |                | - payer_claims          |
| - diagnostic_reports     |                | - prior_authorizations  |
| - evidence (with tags)   |                | - benefits              |
+------------+-------------+                +------------+------------+
             |                                           |
             | Selects Evidence                          | Mapped Member
             v                                           v
    [Canonical Claim] ───────────────────────────> [Agent 1 / RAG]
 (Submitted Evidence Only)
```

### A. Provider Database (`big_patient_data.db`)
Represents the longitudinal hospital record. The tables are:
*   `patients` — Demographics.
*   `encounters` — Patient visit events.
*   `conditions` — Diagnoses and onset tracking.
*   `observations` — Tests, clinical values, and units.
*   `procedures` — Surgical recommendations and conservative therapies.
*   `medications` — Active prescriptions and dosages.
*   `allergies` — Allergens, reactions, and severity.
*   `diagnostic_reports` — Imaging files, findings, and dates.
*   `clinical_documents` — Progress notes, clinical text.
*   `care_plans` — Longitudinal patient treatment plans.
*   `evidence` — Mapped evidence entries with sensitivity tags and structured provenance links.

### B. Payer Database (`payer_data.db`)
Represents insurer administrative history. Payer agents cannot query the provider database directly. Tables are:
*   `members` — Authoritative membership details.
*   `eligibility` — Network verification and active ranges.
*   `payer_claims` — Billing claims previously filed to the health plan.
*   `prior_authorizations` — Previous PA request decisions.
*   `utilization` — Counts of prior services and duplicate patterns.
*   `benefits` — Covered categories, authorization requirements, and frequency limits.

---

## 5. Dynamic Policy Selection

The medical policy is dynamically selected using:
```text
Payer + Plan + Diagnosis + Requested Procedure + Domain ──> Policy Mapping ──> Policy ID
```
Aetna procedures map to **Clinical Policy Bulletins (CPBs)** (e.g. `CPB-0660` for Knee Arthroplasty) whereas Medicare/CMS procedures map to **Local/National Coverage Determinations (LCDs/NCDs)** (e.g. `LCD-L35074` for Knee Arthroplasty).

---

## 6. Supported Clinical Domains

The simulation framework is generic and supports the following eight domains:
1.  **Orthopedics** (Knee Osteoarthritis, Rheumatoid Arthritis, Avascular Necrosis)
2.  **Hip / Joint Replacement** (Hip Osteoarthritis)
3.  **Spine** (Spinal stenosis, Degenerative spine disease)
4.  **Imaging** (Breast MRI, Spine MRI, Chest CT)
5.  **Obesity** (Bariatric Surgery)
6.  **Sleep Medicine** (Continuous Positive Airway Pressure CPAP)
7.  **Cardiology** (Cardiac Catheterization)
8.  **Neurology** (Electroencephalography EEG)

---

## 7. Multi-Attempt Resubmission Flow

Attempt 1 is completely **immutable** and is never overwritten by Attempt 2.
```text
Attempt 1 (Omitted Evidence)
   ↓
Decision Agent: NEED MORE INFO
   ↓
Evidence release evaluation
   ↓
Attempt 2 (Released Evidence)
```
In Attempt 2, the Canonical Claim tracks newly released evidence in the `new_evidence_delta` array:
```json
{
  "submission": {
    "attempt": 2,
    "submitted_at": "2026-08-14T22:16:35Z"
  },
  "new_evidence_delta": [
    "EV-51A3F6"
  ]
}
```

---

## 8. Safe Sensitivity Escrow

Evidence is classified into six categories:
*   `ROUTINE` — Eligible for automatic release.
*   `PROTECTED_MENTAL_HEALTH` — Controlled release.
*   `PROTECTED_SUBSTANCE_USE` — Controlled release.
*   `PROTECTED_HIV` — Controlled release.
*   `PROTECTED_GENETIC` — Controlled release.
*   `UNKNOWN` — Escalates automatically to human review.

Deterministic rules evaluate release suitability:
```text
Evidence item ──> Check Sensitivity
                     ├── ROUTINE ───────> RELEASE
                     ├── PROTECTED_* ───> CONTROLLED
                     └── UNKNOWN ───────> ESCALATE / HUMAN REVIEW
```

---

## 9. Downstream Integration Contracts

### A. Canonical Claim JSON (`canonical_claim_<id>.json`)
```json
{
  "prior_authorization_request": {
    "claim_id": "CLM-DD180B",
    "patient": { "patient_id": "PA045" },
    "payer": { "payer_id": "Aetna", "plan_id": "PLAN-AETNA-001" },
    "provider": { "provider_id": "PROV-HOSP-01", "facility_id": "FAC-NORTH-01" },
    "requested_service": { "code": "27447", "description": "Total knee arthroplasty (TKA), right knee", "service_date": "2026-08-14" },
    "diagnoses": [{ "code": "M17.11", "description": "Knee Osteoarthritis" }],
    "clinical_facts": [
      {
        "type": "diagnosis",
        "code": "M17.11",
        "value": "Diagnosis: Primary osteoarthritis of right knee (M17.11) ..."
      }
    ],
    "supporting_evidence": [
      {
        "evidence_id": "EV-BF93BC",
        "type": "DIAGNOSIS",
        "reference": "Diagnosis: Primary osteoarthritis...",
        "sensitivity": "ROUTINE",
        "provenance": {
          "source_type": "conditions",
          "source_record_id": "45925"
        }
      }
    ],
    "submission": { "attempt": 1, "submitted_at": "2026-08-14T22:16:12Z" },
    "new_evidence_delta": []
  }
}
```

### B. RAG Input JSON (`rag_input_<id>.json`)
```json
{
  "claim_id": "CLM-DD180B",
  "insurance": {
    "primary": {
      "payer": "Aetna",
      "policy_id": "CPB-0660"
    }
  },
  "diagnosis": [
    {
      "code": "M17.11",
      "description": "Knee Osteoarthritis"
    }
  ],
  "procedure": {
    "code": "27447",
    "description": "Total knee arthroplasty (TKA), right knee"
  },
  "clinical_domain": "orthopedics"
}
```

---

## 10. Automated Validation Suite

An automated test suite is provided in the repository under:
```text
C:\Users\swaro\.gemini\antigravity\brain\947570ef-18f4-4d52-bda9-c2e1bdc30720\scratch\test_version1.py
```
This suite programmatically verifies the following correctness criteria:
*   **Provider Schema Integrity**: Demographics, encounters, conditions, and evidence schemas.
*   **Payer Schema Isolation**: Separate member and plan eligibility definitions.
*   **Trust Boundary Enforcement**: No leak of clinical connection parameters or databases to downstream Agent 1 inputs.
*   **Canonical Claim Evidence constraints**: Only submitted evidence elements are included in the JSON output.
*   **Dynamic Policy and Condition overrides**: Check dynamic policy lookups for Aetna and CMS NCDs/LCDs.
*   **Dynamic RAG Inputs**: Non-hardcoded condition queries and case-specific questions across multiple domains.
*   **Seeded Arrival determinism**: Seeded reproducibility across simulation loops.
*   **Resubmission Immutability**: Attempt 1 preservation and Attempt 2 resubmission delta computations.
*   **Sensitivity release constraints**: Safety check release rules for Routine and Escrow detours.
*   **Eight clinical domains support**: Verification across all simulated patient categories.
*   **Ingestion Idempotency**: Verify duplicate-free database rebuilds.
