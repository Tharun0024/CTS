CTS HACKATHON
# Prior Authorization Claim Ingestion & Simulation Pipeline

**Version 1**

This system simulates the clinical prior authorization (PA) workflow under a strict **Provider ↔ Payer trust boundary**.

---

## 1. Directory Structure

All code, data files, and database outputs are self-contained in the project folder.

```text
prior_auth_project/
│
├── final_patient_data_PA_IDs_final.xlsx
│   └── Raw patient demographics spreadsheet
│
├── clinical_events_PA_ids.csv
│   └── Raw longitudinal clinical history CSV
│
├── prior_authorization_policies.xlsx
│   └── Insurer policy rules configuration
│
├── big_patient_data.db
│   └── Provider Clinical Database (SQLite)
│
├── payer_data.db
│   └── Payer Administrative Database (SQLite)
│
├── Aetna_Knee_Arthroplasty_PA_Input.pdf
│   └── Sample clinical patient PDF
│
├── SC02_Missing_Documentation.pdf
│   └── Scenario PDF
│
├── SC03 to SC07 PDFs
│   └── Scenario PDFs
│
├── pa_pipeline/
│   │
│   ├── database/
│   │   └── db_manager.py
│   │       └── Schema initialization, routing & database helpers
│   │
│   ├── ingestion/
│   │   ├── ingest_data.py
│   │   │   └── Bulk clinical loader & Payer administrative generator
│   │   │
│   │   └── manual_parser.py
│   │       └── Parses manual clinical patient PDFs into clinical tables
│   │
│   ├── simulation/
│   │   ├── scenario_generator.py
│   │   │   └── Synthesizes clinical scenarios
│   │   │
│   │   └── simulation.py
│   │       └── Standard simulation loop with random seed support
│   │
│   ├── transformation/
│   │   ├── canonical_claim.py
│   │   │   └── Exports normalized decision-free claims to output/
│   │   │
│   │   └── rag_input.py
│   │       └── Exports context payloads to output/
│   │
│   └── pipeline_main.py
│       └── Core CLI entry point
│
└── output/
    ├── canonical_claim_<id>.json
    │   └── Consumed by Tharun's Decision Agent
    │
    └── rag_input_<id>.json
        └── Consumed by Thirumalai's RAG Retriever
```

---

## 2. Requirements & Setup

Make sure **Python 3** is installed.

Navigate to the project directory:

```powershell
cd C:\Users\swaro\Downloads\prior_auth_project
```

Install the required dependencies:

```powershell
pip install pandas openpyxl pdfplumber
```

---

## 3. How to Run the Pipeline

The pipeline is controlled through the central CLI entry point:

```text
pa_pipeline/pipeline_main.py
```

### 3.1 Ingest Raw Spreadsheets

Run this once to set up the databases.

This loads and structures provider clinical events into normalized tables and independently initializes/populates the synthetic payer administrative dataset in `payer_data.db`.

The payer dataset is **not a copy or transformation of the provider's complete clinical record**.

```powershell
python pa_pipeline/pipeline_main.py ingest
```

---

### 3.2 Run Deterministic Simulation for a Specific Patient

This simulates clinical facts, writes them to the correct normalized tables, applies sensitivity/provenance metadata, and submits Attempt 1.

```powershell
python pa_pipeline/pipeline_main.py run-simulation --patient-id PA045 --scenario-type EVIDENCE_OMITTED
```

Available scenario types:

```text
COMPLETE
INCOMPLETE
AMBIGUOUS
EVIDENCE_OMITTED
```

---

### 3.3 Run a Simulation Sequence with a Seed

For demonstrations, the pipeline can cycle through a set number of random patients using a reproducible seeded random index.

```powershell
python pa_pipeline/pipeline_main.py run-simulation --limit 5 --interval-seconds 3 --seed 123
```

---

### 3.4 Process a Manual Clinical Patient PDF

The manual parser extracts patient demographics, CPT codes, and conservative treatment records directly from a clinical PDF and generates the outputs immediately.

```powershell
python pa_pipeline/pipeline_main.py process-manual --file Aetna_Knee_Arthroplasty_PA_Input.pdf
```

---

# 4. Trust Boundary & Database Layout

To enforce the **Provider ↔ Payer trust boundary**, the datasets are kept physically separate.

```text
    [PROVIDER SYSTEM]                         [PAYER SYSTEM]
┌──────────────────────────┐             ┌─────────────────────────┐
│ big_patient_data.db      │             │ payer_data.db           │
│ Full Longitudinal Care   │             │ Eligibility & Claims    │
│                          │             │                         │
│ • conditions             │             │ • members               │
│ • observations           │             │ • eligibility           │
│ • procedures             │             │ • payer_claims           │
│ • diagnostic_reports     │             │ • prior_authorizations  │
│ • evidence (with tags)   │             │ • benefits              │
└────────────┬─────────────┘             └────────────┬────────────┘
             │                                        │
             │ Selects Evidence                       │ Mapped Member
             ▼                                        ▼
       ┌──────────────────────────────────────────────────┐
       │              Canonical Claim                      │
       │              Submitted Evidence Only              │
       └────────────────────────┬─────────────────────────┘
                                │
                                ▼
                         [Agent 1 / RAG]
```

---

## 4.1 Provider Database

### `big_patient_data.db`

Represents the longitudinal hospital record.

Tables include:

| Table                | Description                                                                   |
| -------------------- | ----------------------------------------------------------------------------- |
| `patients`           | Demographics                                                                  |
| `encounters`         | Patient visit events                                                          |
| `conditions`         | Diagnoses and onset tracking                                                  |
| `observations`       | Tests, clinical values, and units                                             |
| `procedures`         | Surgical recommendations and conservative therapies                           |
| `medications`        | Active prescriptions and dosages                                              |
| `allergies`          | Allergens, reactions, and severity                                            |
| `diagnostic_reports` | Imaging files, findings, and dates                                            |
| `clinical_documents` | Progress notes and clinical text                                              |
| `care_plans`         | Longitudinal patient treatment plans                                          |
| `evidence`           | Mapped evidence entries with sensitivity tags and structured provenance links |

---

## 4.2 Payer Database

### `payer_data.db`

Represents insurer administrative history.

**Payer agents cannot query the provider database directly.**

Tables include:

| Table                  | Description                                                          |
| ---------------------- | -------------------------------------------------------------------- |
| `members`              | Authoritative membership details                                     |
| `eligibility`          | Network verification and active ranges                               |
| `payer_claims`         | Billing claims previously filed to the health plan                   |
| `prior_authorizations` | Previous PA request decisions                                        |
| `utilization`          | Counts of prior services and duplicate patterns                      |
| `benefits`             | Covered categories, authorization requirements, and frequency limits |

---

# 5. Dynamic Policy Selection

The medical policy is dynamically selected using:

```text
Payer
   +
Plan
   +
Diagnosis
   +
Requested Procedure
   +
Domain
   │
   ▼
Policy Mapping
   │
   ▼
Policy ID
```

Aetna procedures map to **Clinical Policy Bulletins (CPBs)**.

Example:

```text
CPB-0660
```

Medicare/CMS procedures map to **Local/National Coverage Determinations (LCDs/NCDs)**.

Example:

```text
LCD-L35074
```

---

# 6. Supported Clinical Domains

The simulation framework supports eight clinical domains:

### 1. Orthopedics

* Knee Osteoarthritis
* Rheumatoid Arthritis
* Avascular Necrosis

### 2. Hip / Joint Replacement

* Hip Osteoarthritis

### 3. Spine

* Spinal stenosis
* Degenerative spine disease

### 4. Imaging

* Breast MRI
* Spine MRI
* Chest CT

### 5. Obesity

* Bariatric Surgery

### 6. Sleep Medicine

* Continuous Positive Airway Pressure (CPAP)

### 7. Cardiology

* Cardiac Catheterization

### 8. Neurology

* Electroencephalography (EEG)

---

# 7. Multi-Attempt Resubmission Flow

Attempt 1 is completely **immutable** and is never overwritten by Attempt 2.

```text
Attempt 1
(Omitted Evidence)
       │
       ▼
Decision Agent
       │
       ▼
NEED MORE INFO
       │
       ▼
Evidence Release Evaluation
       │
       ▼
Attempt 2
(Released Evidence)
```

In Attempt 2, the Canonical Claim tracks newly released evidence in the `new_evidence_delta` array.

Example:

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

# 8. Safe Sensitivity Escrow

Evidence is classified into six categories:

| Evidence Category         | Handling                                |
| ------------------------- | --------------------------------------- |
| `ROUTINE`                 | Eligible for automatic release          |
| `PROTECTED_MENTAL_HEALTH` | Controlled release                      |
| `PROTECTED_SUBSTANCE_USE` | Controlled release                      |
| `PROTECTED_HIV`           | Controlled release                      |
| `PROTECTED_GENETIC`       | Controlled release                      |
| `UNKNOWN`                 | Escalates automatically to human review |

### Deterministic Release Rules

```text
Evidence Item
      │
      ▼
Check Sensitivity
      │
      ├── ROUTINE
      │      └── RELEASE
      │
      ├── PROTECTED_*
      │      └── CONTROLLED
      │
      └── UNKNOWN
             └── ESCALATE / HUMAN REVIEW
```

---

# 9. Downstream Integration Contracts

## 9.1 Canonical Claim JSON

The generated canonical claim is a normalized, decision-free claim.

Example:

```json
{
  "prior_authorization_request": {
    "claim_id": "CLM-DD180B",
    "patient": {
      "patient_id": "PA045"
    },
    "payer": {
      "payer_id": "Aetna",
      "plan_id": "PLAN-AETNA-001"
    },
    "provider": {
      "provider_id": "PROV-HOSP-01",
      "facility_id": "FAC-NORTH-01"
    },
    "requested_service": {
      "code": "27447",
      "description": "Total knee arthroplasty (TKA), right knee",
      "service_date": "2026-08-14"
    },
    "diagnoses": [
      {
        "code": "M17.11",
        "description": "Knee Osteoarthritis"
      }
    ],
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
    "submission": {
      "attempt": 1,
      "submitted_at": "2026-08-14T22:16:12Z"
    },
    "new_evidence_delta": []
  }
}
```

Output:

```text
output/
└── canonical_claim_<id>.json
```

---

## 9.2 RAG Input JSON

The RAG input contains the information required by the downstream RAG Retriever.

Example:

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

Output:

```text
output/
└── rag_input_<id>.json
```

---

# 10. Automated Validation Suite

An automated test suite is provided in the repository under:

```text
C:\Users\swaro\.gemini\antigravity\brain\947570ef-18f4-4d52-bda9-c2e1bdc30720\scratch\test_version1.py
```

The suite verifies:

* **Provider Schema Integrity**

  * Demographics
  * Encounters
  * Conditions
  * Evidence schemas

* **Payer Schema Isolation**

  * Separate member and plan eligibility definitions

* **Trust Boundary Enforcement**

  * No leak of clinical connection parameters or databases to downstream Agent 1 inputs

* **Canonical Claim Evidence Constraints**

  * Only submitted evidence elements are included in the JSON output

* **Dynamic Policy and Condition Overrides**

  * Dynamic policy lookups for Aetna and CMS NCDs/LCDs

* **Dynamic RAG Inputs**

  * Non-hardcoded condition queries and case-specific questions across multiple domains

* **Seeded Arrival Determinism**

  * Seeded reproducibility across simulation loops

* **Resubmission Immutability**

  * Attempt 1 preservation
  * Attempt 2 resubmission delta computations

* **Sensitivity Release Constraints**

  * Safety checks for Routine and Escrow detours

* **Eight Clinical Domains Support**

  * Verification across all simulated patient categories

* **Ingestion Idempotency**

  * Duplicate-free database rebuilds
