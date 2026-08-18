# Provider-Side Prior Authorization Orchestrator (Agent 2)
### CTS Hackathon V1 - Provider Prior Authorization & Clinical Evidence Engine

This repository contains the complete implementation of **Agent 2**, a provider-side Prior Authorization Orchestrator. Agent 2 ingests raw clinical patient records from Synthea FHIR bundles, normalizes insurance coverage policies (RAG), matches clinical evidence criteria, filters evidence packages to enforce the provider-to-payer minimum-necessary trust boundary (Trust Boundary Filter), submits authorization packages to a payer engine (Agent 1), and manages closed-loop resubmissions on failure.

---

## 🏛️ System Architecture

```text
                    PROVIDER / HOSPITAL
                           │
                           ▼
                ┌─────────────────────┐
                │ Big Patient Record  │
                │ SQLite Warehouse    │
                │ 6,000+ Lab Records  │
                └──────────┬──────────┘
                           │
                  Candidate Evidence
                           │
                           ▼
                ┌─────────────────────┐
                │       AGENT 2       │
                │    Provider Side    │
                │                     │
                │ 1. Retrieves Policy │
                │ 2. Identifies       │
                │    Required Criteria│
                │ 3. Matches Evidence │
                │ 4. Finds Missing /  │
                │    Conflicting Data │
                │ 5. Builds Minimum   │
                │    Necessary        │
                │    SubmissionPackage│
                └──────────┬──────────┘
                           │
                   SubmissionPackage
                           │
          =====================================
                    TRUST BOUNDARY
          =====================================
                           │
                           ▼
                ┌─────────────────────┐
                │       AGENT 1       │
                │     Payer Side      │
                │                     │
                │ 1. Payer Validation │
                │ 2. Payer Decision   │
                │    Logic            │
                │ 3. Final Coverage   │
                │    Outcome          │
                └──────────┬──────────┘
                           │
                           ▼
                    PayerResponse
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
          ▼                ▼                 ▼
      APPROVED          REJECTED         MORE_INFO /
          │                │              HUMAN_REVIEW
          ▼                │                 │
   Approved Claim          └────────┬────────┘
                                    │
                                    ▼
                            Recovery Search
                            (Provider SQLite)
                                    │
                                    ▼
                           Rebuild Evidence
                                    │
                                    ▼
                                  V2+
                                    │
                                    ▼
                            SubmissionPackage
                                    │
                                    ▼
                            ─ TRUST BOUNDARY ─
                                    │
                                    ▼
                                AGENT 1
```

---

## 📁 Repository Directory Structure

*   [`config.py`](file:///C:/Users/swaro/OneDrive/Documents/agent2/config.py): Base configurations (workspace, database, directories, maximum resubmissions).
*   [`database/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/database):
    *   [`db_manager.py`](file:///C:/Users/swaro/OneDrive/Documents/agent2/database/db_manager.py): Creates SQLite clinical tables and metadata tables (claims, versions, audits, reviews).
    *   [`importer.py`](file:///C:/Users/swaro/OneDrive/Documents/agent2/database/importer.py): Parses and ingests Synthea FHIR JSON records into SQLite.
    *   [`repositories/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/database/repositories/): SQL read/write helpers for patient records, claims, audit timelines, and reviews.
*   [`schemas/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/schemas): Structured models (`CanonicalClaim`, `Evidence`, `SubmissionPackage`, `PayerResponse`, `HumanReview`).
*   [`validators/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/validators): Logical checks including intake validations, evidence matching, and privacy validation.
*   [`retrieval/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/retrieval): Queries candidate patient records, selects policies, and maps them to criteria.
*   [`reasoning/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/reasoning): Matches provider clinical evidence against normalized policy criteria using Gemini-assisted reasoning with a deterministic Python fallback.
*   [`submission/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/submission): Bundles evidence, filters unreferenced files (Trust Boundary filter), and increments claim versions.
*   [`agent1/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/agent1): Simulates the payer decision engine based on insurance guidelines.
*   [`workflow/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/workflow): The state machine orchestrator managing the full life-cycle.
*   [`tests/`](file:///C:/Users/swaro/OneDrive/Documents/agent2/tests):
    *   [`setup_test_data.py`](file:///C:/Users/swaro/OneDrive/Documents/agent2/tests/setup_test_data.py): Seeds scenario-specific test patient profiles.
    *   [`test_end_to_end.py`](file:///C:/Users/swaro/OneDrive/Documents/agent2/tests/test_end_to_end.py): Main E2E test suite covering Scenarios A-E.

---

## 🚀 Setup & Execution

### 1. Configure Credentials
Create a `.env` file in the project root (`C:\Users\swaro\OneDrive\Documents\agent2\.env`) containing your Gemini API key:
```env
GEMINI_API_KEY=AIzaSy...
```
*Note: If the key is not set or quota is exceeded, the orchestrator automatically activates its local rule-based clinical engine to ensure the platform remains online.*

### 2. Ingest Patient Bundles
Seed the SQLite database with Synthea FHIR records and scenario test profiles:
```bash
python -m database.importer
python -m tests.setup_test_data
```

### 3. Run E2E Integration Suite
Verify the state machine logic on all five test scenarios:
```bash
python -m tests.test_end_to_end
```
You should see: `ALL SCENARIOS PASSED SUCCESSFULLY!`

---

## 🖥️ Launching the Streamlit Portal

The interactive Prior Authorization Portal resides in the companion directory:
`C:\Users\swaro\OneDrive\Documents\project\prior-auth-companion`

To launch it:
1. Open a terminal in that folder:
   ```bash
   cd C:\Users\swaro\OneDrive\Documents\project\prior-auth-companion
   ```
2. Start the server:
   ```bash
   streamlit run src/app.py
   ```
   *(Or run the preconfigured `run.bat` file).*

### Portal Features:
*   **Live Orchestrator State Timeline**: Watch states transition (`VALIDATING` ➡️ `RETRIEVING_EVIDENCE` ➡️ `WAITING_FOR_PAYER` ➡️ `BUILDING_RESUBMISSION` ➡️ `APPROVED`!) in real time.
*   **Version Compare Explorer**: Inspect the JSON claim metadata and minimum necessary clinical evidence packages side-by-side (V1 vs V2).
*   **Metrics Tab**: Renders aggregate analytics (total claims, approval rates, resubmission effectiveness) queried live from the SQLite warehouse.
*   **RAG Chatbot Tab**: Natural language querying of CMS and commercial guidelines.
