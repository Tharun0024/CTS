# CTS Hackathon
# Prior Authorization Claim Ingestion & Simulation Pipeline

**Version 1**

A clinical prior authorization (PA) simulation system that models the **Provider ↔ Payer trust boundary**. The pipeline ingests longitudinal clinical records, simulates PA scenarios, processes manual clinical PDFs, and produces normalized, decision-free payloads for downstream **RAG Retrievers** and **Decision Agents**.

---

## 1. Project Structure

The project is organized as follows:

```text
prior_auth_project/
│
├── final_patient_data_PA_IDs_final.xlsx
│   └── Raw patient demographics spreadsheet
│
├── clinical_events_PA_ids.csv
│   └── Raw longitudinal clinical history
│
├── prior_authorization_policies.xlsx
│   └── Insurer policy rules configuration
│
├── big_patient_data.db
│   └── Provider clinical database (SQLite)
│
├── payer_data.db
│   └── Payer administrative database (SQLite)
│
├── Aetna_Knee_Arthroplasty_PA_Input.pdf
│   └── Sample clinical patient PDF
│
├── SC02_Missing_Documentation.pdf
│   └── Scenario PDF
│
├── SC03...SC07 PDFs
│   └── Additional scenario PDFs
│
├── pa_pipeline/
│   │
│   ├── database/
│   │   ├── db_manager.py
│   │   └── __init__.py
│   │
│   ├── ingestion/
│   │   ├── ingest_data.py
│   │   ├── manual_parser.py
│   │   └── __init__.py
│   │
│   ├── simulation/
│   │   ├── scenario_generator.py
│   │   ├── simulation.py
│   │   └── __init__.py
│   │
│   ├── transformation/
│   │   ├── canonical_claim.py
│   │   ├── rag_input.py
│   │   └── __init__.py
│   │
│   ├── pipeline_main.py
│   └── __init__.py
│
└── output/
    ├── canonical_claim_<id>.json
    └── rag_input_<id>.json
```

---

## 2. System Overview

The pipeline simulates the clinical prior authorization workflow while maintaining a strict separation between provider and payer information.

### Main workflow

```text
Clinical Records
      │
      ▼
Data Ingestion
      │
      ▼
Provider / Payer Databases
      │
      ▼
Clinical Scenario Simulation
      │
      ▼
Evidence Selection
      │
      ▼
Canonical Claim
      │
      ├──────────────► RAG Input
      │
      └──────────────► Decision Agent
```

The system produces **decision-free normalized payloads** rather than making the final authorization decision.

---

## 3. Requirements

### Python

Python 3 or later is required.

### Install Dependencies

From the project directory:

```powershell
cd C:\Users\swaro\Downloads\prior_auth_project
pip install pandas openpyxl pdfplumber
```

---

## 4. Running the Pipeline

All major operations are controlled through:

```text
pa_pipeline/pipeline_main.py
```

### 4.1 Ingest Raw Data

Run the ingestion process once to initialize and populate the databases:

```powershell
python pa_pipeline/pipeline_main.py ingest
```

This process loads the clinical records into normalized provider tables and initializes the synthetic payer administrative dataset.

---

### 4.2 Run a Simulation for a Specific Patient

Example:

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

### 4.3 Run a Seeded Simulation Sequence

For demonstrations and reproducible testing:

```powershell
python pa_pipeline/pipeline_main.py run-simulation --limit 5 --interval-seconds 3 --seed 123
```

The seed ensures reproducibility across simulation runs.

---

### 4.4 Process a Manual Clinical PDF

To process a manually submitted clinical patient PDF:

```powershell
python pa_pipeline/pipeline_main.py process-manual --file Aetna_Knee_Arthroplasty_PA_Input.pdf
```

The parser extracts relevant patient information, CPT codes, and conservative treatment records and writes the resulting information into the appropriate database structures.

---

# 5. Provider ↔ Payer Trust Boundary

The system maintains separate provider and payer databases.

```text
┌──────────────────────────────┐
│       PROVIDER SYSTEM        │
│                              │
│    big_patient_data.db       │
│                              │
│  • patients                  │
│  • encounters                │
│  • conditions                │
│  • observations              │
│  • procedures                │
│  • medications               │
│  • allergies                 │
│  • diagnostic_reports        │
│  • clinical_documents        │
│  • care_plans                │
│  • evidence                  │
└──────────────┬───────────────┘
               │
               │ Selected Evidence
               ▼
       ┌──────────────────┐
       │ Canonical Claim  │
       └────────┬─────────┘
                │
                ▼
        Agent 1 / RAG
               
┌──────────────────────────────┐
│         PAYER SYSTEM         │
│                              │
│       payer_data.db          │
│                              │
│  • members                   │
│  • eligibility               │
│  • payer_claims              │
│  • prior_authorizations      │
│  • utilization               │
│  • benefits                  │
└──────────────────────────────┘
```

The payer system cannot directly query the provider's complete clinical database.

---

## 6. Provider Database

### `big_patient_data.db`

The provider database represents the longitudinal clinical record.

| Table                | Purpose                                                   |
| -------------------- | --------------------------------------------------------- |
| `patients`           | Patient demographics                                      |
| `encounters`         | Patient visit events                                      |
| `conditions`         | Diagnoses and onset tracking                              |
| `observations`       | Tests, clinical values, and units                         |
| `procedures`         | Surgical recommendations and conservative therapies       |
| `medications`        | Active prescriptions and dosages                          |
| `allergies`          | Allergens, reactions, and severity                        |
| `diagnostic_reports` | Imaging files, findings, and dates                        |
| `clinical_documents` | Progress notes and clinical text                          |
| `care_plans`         | Longitudinal treatment plans                              |
| `evidence`           | Evidence entries with sensitivity and provenance metadata |

---

## 7. Payer Database

### `payer_data.db`

The payer database contains insurer administrative information.

| Table                  | Purpose                                            |
| ---------------------- | -------------------------------------------------- |
| `members`              | Authoritative membership details                   |
| `eligibility`          | Network verification and active ranges             |
| `payer_claims`         | Previously submitted billing claims                |
| `prior_authorizations` | Previous PA request decisions                      |
| `utilization`          | Prior service and duplicate-use counts             |
| `benefits`             | Coverage categories and authorization requirements |

---

# 8. Dynamic Policy Selection

Medical policy selection follows:

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

The system supports payer-specific policy mappings.

For example:

```text
Aetna
  └── Clinical Policy Bulletin (CPB)

Medicare / CMS
  └── LCD / NCD
```

---

# 9. Supported Clinical Domains

The simulation framework supports eight clinical domains:

1. **Orthopedics**

   * Knee Osteoarthritis
   * Rheumatoid Arthritis
   * Avascular Necrosis

2. **Hip / Joint Replacement**

   * Hip Osteoarthritis

3. **Spine**

   * Spinal stenosis
   * Degenerative spine disease

4. **Imaging**

   * Breast MRI
   * Spine MRI
   * Chest CT

5. **Obesity**

   * Bariatric Surgery

6. **Sleep Medicine**

   * Continuous Positive Airway Pressure (CPAP)

7. **Cardiology**

   * Cardiac Catheterization

8. **Neurology**

   * Electroencephalography (EEG)

---

# 10. Multi-Attempt Resubmission Flow

The system supports multiple PA submission attempts.

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

### Attempt 1

Attempt 1 is immutable and is never overwritten.

### Attempt 2

Newly released evidence is represented through:

```json
{
  "submission": {
    "attempt": 2
  },
  "new_evidence_delta": [
    "EV-51A3F6"
  ]
}
```

---

# 11. Safe Sensitivity Escrow

Evidence is classified into six categories:

| Category                  | Release Behavior               |
| ------------------------- | ------------------------------ |
| `ROUTINE`                 | Eligible for automatic release |
| `PROTECTED_MENTAL_HEALTH` | Controlled release             |
| `PROTECTED_SUBSTANCE_USE` | Controlled release             |
| `PROTECTED_HIV`           | Controlled release             |
| `PROTECTED_GENETIC`       | Controlled release             |
| `UNKNOWN`                 | Escalates to human review      |

### Release Logic

```text
Evidence
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

# 12. Canonical Claim Output

The canonical claim is a normalized, decision-free representation of the PA request.

Example structure:

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
      "description": "Total knee arthroplasty (TKA), right knee"
    },
    "diagnoses": [
      {
        "code": "M17.11",
        "description": "Knee Osteoarthritis"
      }
    ],
    "clinical_facts": [],
    "supporting_evidence": [],
    "submission": {
      "attempt": 1
    },
    "new_evidence_delta": []
  }
}
```

Output files are generated as:

```text
output/
└── canonical_claim_<id>.json
```

---

# 13. RAG Input

The RAG input contains the policy context and clinical information required by the downstream retrieval system.

Example:

```json
{
  "claim_id": "CLM-DD180B",
  "patient_id": "PA045",
  "insurance": "Aetna",
  "policy_context": {
    "policy_id": "CPB-0660",
    "policy_title": "Knee Arthroplasty Prior Authorization CPB",
    "domain": "Orthopedics",
    "sub_domain": "Knee Osteoarthritis"
  },
  "domain": "orthopedics",
  "condition": "knee_osteoarthritis",
  "procedure": {
    "code": "27447",
    "description": "Total knee arthroplasty (TKA), right knee"
  },
  "clinical_facts": [],
  "policy_questions": []
}
```

Output files are generated as:

```text
output/
└── rag_input_<id>.json
```

---

# 14. Downstream Integration

The generated payloads are intended for downstream systems:

```text
                 PA Pipeline
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 Canonical Claim              RAG Input
          │                       │
          ▼                       ▼
 Decision Agent              RAG Retriever
```

The pipeline itself remains **decision-free**.

---

# 15. Validation Suite

An automated validation suite is used to verify the pipeline.

The validation checks include:

* Provider schema integrity
* Payer schema isolation
* Provider ↔ Payer trust boundary enforcement
* Canonical claim evidence constraints
* Dynamic policy and condition overrides
* Dynamic RAG inputs
* Seeded simulation determinism
* Resubmission immutability
* Sensitivity release constraints
* Support for all eight clinical domains
* Ingestion idempotency

The validation suite is located at:

```text
C:\Users\swaro\.gemini\antigravity\brain\947570ef-18f4-4d52-bda9-c2e1bdc30720\scratch\test_version1.py
```

---

# 16. GitHub Setup

The `pa_pipeline` directory contains the Python source code and can be version-controlled independently.

Recommended repository structure:

```text
prior_auth_project/
│
├── pa_pipeline/
│   ├── database/
│   ├── ingestion/
│   ├── simulation/
│   ├── transformation/
│   ├── pipeline_main.py
│   └── __init__.py
│
└── README.md
```

Large datasets such as `big_patient_data` should not be uploaded through the standard GitHub web uploader when they exceed GitHub's file-size limits.

---

# 17. Quick Start

```powershell
# Navigate to the project
cd C:\Users\swaro\Downloads\prior_auth_project

# Install dependencies
pip install pandas openpyxl pdfplumber

# Ingest data
python pa_pipeline/pipeline_main.py ingest

# Run a simulation
python pa_pipeline/pipeline_main.py run-simulation --patient-id PA045 --scenario-type EVIDENCE_OMITTED

# Run a seeded simulation
python pa_pipeline/pipeline_main.py run-simulation --limit 5 --interval-seconds 3 --seed 123

# Process a manual PDF
python pa_pipeline/pipeline_main.py process-manual --file Aetna_Knee_Arthroplasty_PA_Input.pdf
```

---

## 18. Project Objective

The objective of this project is to provide a structured prior authorization simulation pipeline that:

* Ingests longitudinal clinical records
* Maintains a strict Provider ↔ Payer separation
* Simulates multiple clinical PA scenarios
* Processes manually submitted clinical PDFs
* Applies sensitivity and evidence-release rules
* Dynamically maps cases to applicable policy contexts
* Generates normalized canonical claims
* Generates RAG-ready context payloads
* Supports multi-attempt PA submissions
* Provides deterministic simulation and validation capabilities
* Keeps final authorization decisions within downstream decision systems
