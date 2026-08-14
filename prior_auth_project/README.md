# Prior Authorization Claim Ingestion & Simulation Pipeline

Welcome to the Prior Authorization (PA) Claim Ingestion & Simulation Pipeline. This system bulk-loads longitudinal clinical records, simulates clinical scenarios for prior authorization, parses manual patient submission PDFs, and outputs normalized, decision-free payloads for downstream **RAG Retrievers** and **Decision Agents**.

---

## 1. Directory Structure

All code, data files, and database outputs are self-contained in this folder:

```text
prior_auth_project/
│
├── final_patient_data_PA_IDs_final.xlsx # Raw patient demographics spreadsheet
├── clinical_events_PA_ids.csv           # Raw longitudinal clinical history CSV
├── prior_authorization_policies.xlsx    # Insurer policy rules configuration
├── big_patient_data.db                  # Rebuilt SQLite database
│
├── Aetna_Knee_Arthroplasty_PA_Input.pdf # Sample clinical patient PDF
├── SC02_Missing_Documentation.pdf       # Scenario PDF
├── SC03_Criteria_Not_Satisfied.pdf      # Scenario PDF
├── ... (SC04 to SC07 PDFs)              # Scenario PDF
│
├── pa_pipeline/                         # Python Source Package
│   ├── database/
│   │   └── db_manager.py                # Schema initialization & SQLite helpers
│   ├── ingestion/
│   │   ├── ingest_data.py               # Bulk excel/csv loader preserving database constraints
│   │   └── manual_parser.py             # Key-value line parser for clinical PDFs
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

### 1. Ingest raw spreadsheets (Run once to set up the DB)
This initializes the SQLite schema with foreign keys and bulk-loads the Excel/CSV data without dropping constraints.
```powershell
python pa_pipeline/pipeline_main.py ingest
```

### 2. Run deterministic simulation for a specific patient
Simulates clinical facts and submits a claim for a specific patient.
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

## 4. Scenario Types Explained

The simulator generates clinical facts and evidence conditions rather than making downstream approval decisions. The four scenario styles are:
1.  **`COMPLETE`**: All required clinical notes, imaging, and conservative trials (e.g. 12 weeks of PT) are created and submitted in Attempt 1.
2.  **`INCOMPLETE`**: Patient clinical records are deficient (e.g. only 1-2 weeks of PT completed), which is submitted in Attempt 1.
3.  **`AMBIGUOUS`**: Clinical notes contain conflicting dates or diagnoses in Attempt 1.
4.  **`EVIDENCE_OMITTED`**: The patient has a complete clinical record (including 12 weeks of PT), but the PT record is **omitted** from the Attempt 1 submission. This creates a data gap for the downstream Resubmission Agent to repair.

---

## 5. Multi-Attempt Resubmission Modeling

For audits and resubmissions, the system tracks attempts under a **stable claim identifier**:

```text
Patient (PA045)
   ↓
Claim (CLM-8BA436)
   ├── Attempt 1 (submitted_evidence_ids: [EV-1, EV-2])  --> Rejected due to missing PT record
   └── Attempt 2 (submitted_evidence_ids: [EV-1, EV-2, EV-3]) --> Restored with PT record
```

When a claim is resubmitted:
*   The original `claim_id` remains constant.
*   A new record is inserted into `claim_submissions` with `attempt = 2`.
*   The transformation module (`canonical_claim.py`) automatically fetches the latest attempt for that `claim_id`, ensuring the downstream Decision Agent evaluates the newly appended evidence.

---

## 6. Downstream Integration Contracts

The output JSONs generated in the `output/` directory are decision-free, flat structures ready for downstream consumption:

### A. Canonical Claim JSON (`canonical_claim_<id>.json`)
*   **Target**: Consumed by Tharun's **Decision Agent**.
*   **Key Fields**:
    *   `claim_id` (str): Unique claim identifier.
    *   `patient_id` (str): Unique patient identifier.
    *   `policy_id` (str): Unique insurance policy identifier (e.g. `CPB-0660`).
    *   `attempt` (int): Number of current attempt.
    *   `patient_demographics` (dict): Name, age, insurance carrier.
    *   `procedure` (dict): Requested CPT code and description.
    *   `diagnoses` (list): ICD-10 diagnosis code and description resolved from policy configuration.
    *   `evidence_refs` (list): Details of all evidence submitted in this attempt.

### B. RAG Input JSON (`rag_input_<id>.json`)
*   **Target**: Consumed by Thirumalai's **RAG Retriever** to fetch corresponding policy PDF sections.
*   **Key Fields**:
    *   `claim_id` (str) & `patient_id` (str)
    *   `insurance` (str): `Aetna` or `CMS` (Medicare).
    *   `policy_context` (dict): Target policy ID and policy title (e.g. Knee Arthroplasty).
    *   `clinical_facts` (list): Flat strings summarizing the patient's diagnostic and physical therapy facts.
    *   `policy_questions` (list): Core evaluation questions matching the insurer policy targets.
