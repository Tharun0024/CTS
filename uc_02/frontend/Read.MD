# AuthFlow Portal Integration & API Contract (Read.MD)

This document provides a detailed mapping of all interactive frontend buttons, forms, and workflows in the **Hospital/Provider Portal** and **Insurance/Payer Portal**. It outlines the exact API endpoints, HTTP methods, and JSON request/response schemas to help the backend developer connect the dashboards to the AI decision engines (Agent 1 & Agent 2), RAG policy retrieval, and database layers.

---

## 1. Hospital / Provider Portal Buttons & Forms

### 1.1 "Submit Claim" Button (Create Claim Form)
* **Location:** `/hospital/claims/new` (Claim creation form)
* **Purpose:** Submits a new canonical claim containing clinical details and requested procedure codes for policy evaluation.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/claims`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "patient_id": "PAT-001",
  "provider_id": "PRV-001",
  "procedure": "Total Knee Replacement",
  "procedure_code": "27447",
  "diagnosis_codes": ["M17.11", "M79.622"],
  "service_date": "2026-08-20",
  "payer": "Aetna",
  "policy_id": "CPB-0660"
}
```

#### Response Payload Structure
Returns the created `ClaimDetails` object containing initial state details, and triggers Agent 1's automated policy check:
```json
{
  "claim_id": "CLM-101",
  "patient": {
    "patient_id": "PAT-001",
    "name": "John Mitchell",
    "age": 57,
    "gender": "Male"
  },
  "claim": {
    "procedure": "Total Knee Replacement",
    "procedure_code": "27447",
    "diagnosis_codes": ["M17.11", "M79.622"],
    "service_date": "2026-08-20",
    "provider_id": "PRV-001"
  },
  "policy": {
    "payer": "Aetna",
    "policy_id": "CPB-0660",
    "policy_name": "Aetna CPB 0660 – Knee Replacement"
  },
  "decision": null,
  "status": "PROCESSING",
  "attempt": 1,
  "submitted_at": "2026-08-16T12:00:00Z",
  "updated_at": "2026-08-16T12:00:00Z",
  "hospital": "City General Hospital",
  "documents": [],
  "timeline": [
    {
      "timestamp": "2026-08-16T12:00:00Z",
      "event": "SUBMITTED",
      "message": "Claim submitted successfully"
    }
  ]
}
```

---

### 1.2 "Start Simulation" Button
* **Location:** `/hospital/dashboard` (Top dashboard header actions)
* **Purpose:** Initiates a background processing simulation of predefined prior-authorization cases (e.g. running 8 Medicare scenarios end-to-end to test linkage and compliance).
* **HTTP Method:** `POST`
* **Endpoint:** `/api/simulation/start`
* **Content-Type:** `application/json`

#### Request Payload
```json
{
  "source": "hospital-dashboard"
}
```

#### Response Payload
```json
{
  "success": true,
  "message": "Simulation suite triggered successfully.",
  "run_id": "SIM-RUN-9921"
}
```

---

### 1.3 "Upload Supporting Document" Area
* **Location:** `/hospital/claims/new` (Form Section 4) & `/hospital/claims/:id` (Missing Information Uploader)
* **Purpose:** Uploads file attachments (PDFs, JPGs, or clinical notes) containing medical records to associate with a claim.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/claims/{claim_id}/documents`
* **Content-Type:** `multipart/form-data`

#### Form Data Fields
* `files[]`: File Blob(s)
* `document_type`: `diagnostic_report` | `doctor_report` | `treatment_history` | `other`

#### Response Payload
```json
{
  "claim_id": "CLM-003",
  "documents": [
    {
      "document_id": "DOC-901",
      "file_name": "mri_lumbar.pdf",
      "file_type": "application/pdf",
      "uploaded_at": "2026-08-16T12:05:00Z"
    }
  ]
}
```

---

### 1.4 "Submit & Resubmit Claim" Button
* **Location:** `/hospital/claims/:id` (Awaiting missing information phase)
* **Purpose:** Resubmits a claim after the provider has uploaded additional evidence requested by the payer. This kicks off the Agent 1 re-validation flow.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/claims/{claim_id}/resubmit`
* **Content-Type:** `application/json`

#### Request Payload
*(Empty body or optional notes)*
```json
{}
```

#### Response Payload
```json
{
  "success": true,
  "claim_id": "CLM-003"
}
```

---

### 1.5 "Human Review" Escalation Button
* **Location:** `/hospital/claims/:id` (Inside the Resubmission Analysis Panel)
* **Purpose:** Manually escalates a rejected or pending claim to human clinical reviewers because automatic release or alignment cannot be reached by Agent 2.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/claims/{claim_id}/escalate`
* **Content-Type:** `application/json`

#### Request Payload
```json
{
  "escalated_by": "Dr. Arjun Prasad",
  "comments": "Patient has critical comorbidities (Diabetes, Stage 3 CKD) requiring human clinical judgment."
}
```

#### Response Payload
```json
{
  "success": true,
  "claim_id": "CLM-002",
  "status": "HUMAN_REVIEW"
}
```

### 1.6 "View Policy / View Policy Details" Buttons
* **Location:** `/hospital/claims/:id`, `/insurance/claims/:id` & inside `PolicyEvidencePanel`
* **Purpose:** Opens a styled, readable, self-contained popup document showing NCD, LCD, or commercial policy specifications (procedure codes, active dates, clinical criteria thresholds, exclusions).
* **Execution:** Handled entirely by the client-side helper (`src/utils/policyViewer.ts`) without requiring a separate backend render.
* **API Extension (Future):** If the backend wishes to host policy lookup dynamically, expose:
  * `GET` `/api/policies/{policy_id}` returning policy details.

---

### 1.7 "Edit" Button (Patient Information Card)
* **Location:** `/hospital/claims/:id`, `/insurance/claims/:id`, and `/insurance/review/:id` (Patient Info panel)
* **Purpose:** Updates patient details (name, age, gender, contact, address) in-place.
* **HTTP Method:** `PUT`
* **Endpoint:** `/api/patients/{patient_id}`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "name": "John Mitchell",
  "age": 57,
  "gender": "Male",
  "contact": "98765 43210",
  "address": "Coimbatore, Tamil Nadu"
}
```

---

### 1.8 "Edit" Button (Clinical Information Card)
* **Location:** `/hospital/claims/:id`, `/insurance/claims/:id`, and `/insurance/review/:id` (Clinical Info panel)
* **Purpose:** Updates clinical details (procedure name, code, treating doctor) in-place.
* **HTTP Method:** `PUT`
* **Endpoint:** `/api/claims/{claim_id}/clinical`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "procedure": "Total Knee Replacement",
  "procedure_code": "27447",
  "doctor": "Dr. Arjun Prasad"
}
```

---

### 1.9 "Request All" Button (Missing Information Card)
* **Location:** `/hospital/claims/:id` (When status is `MORE_INFO`)
* **Purpose:** Sends notification messages to the patient or hospital staff requesting all listed missing documents.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/claims/{claim_id}/request-missing`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "missing_items": [
    "Recent lab results (CBC + CMP, within 90 days)",
    "Prior imaging report (X-ray or abdominal ultrasound)"
  ]
}
```

---

## 2. Insurance / Payer Portal Buttons & Actions

### 2.1 "Accept / Reject / More Info / Human Review" (Decision Panel Actions)
* **Location:** `/insurance/claims/:id` (Insurance Claim Details panel)
* **Purpose:** Submits an authorization decision for a claim after manual or automated evaluation.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/insurance/claims/{claim_id}/decision`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "decision": "ACCEPT" | "REJECT" | "MORE_INFORMATION" | "HUMAN_REVIEW",
  "reason_code": "CRITERIA_MET" | "INSUFFICIENT_DOCUMENTATION" | "MISSING_DOCUMENTS" | "CLINICAL_COMPLEXITY",
  "comments": "Conservative treatment duration of 14 weeks is fully documented."
}
```

#### Response Payload Structure
```json
{
  "success": true,
  "claim_id": "CLM-001",
  "decision": "ACCEPT"
}
```

---

### 2.2 "Submit Decision" (Human Review Queue Resolution)
* **Location:** `/insurance/review/:review_id` (Human Review Queue resolution panel)
* **Purpose:** Resolves a claim that has been routed to the human review queue. Submitting a decision here also transitions the underlying claim status.
* **HTTP Method:** `POST`
* **Endpoint:** `/api/reviews/{review_id}/decision`
* **Content-Type:** `application/json`

#### Request Payload Structure
```json
{
  "decision": "ACCEPT" | "REJECT" | "MORE_INFORMATION" | "HUMAN_REVIEW",
  "reason_code": "CLINICAL_COMPLEXITY",
  "comments": "Approved after reviewing surgeon's clinical justification."
}
```

#### Response Payload Structure
```json
{
  "success": true,
  "review_id": "REV-001"
}
```

---

### 2.3 Insurer Data (Administrative)
* **Location:** `/insurance/members` (Member Directory details) & `/insurance/claims/:id` (Insurer Data panel)
* **Purpose:** Retrieves administrative information (Member Eligibility, Prior Auth History, Claim History, Utilization/Frequency, and Coverage Details) for a specific patient.
* **HTTP Method:** `GET`
* **Endpoint:** `/api/insurance/patients/{patient_id}/administrative`
* **Content-Type:** `application/json`

#### Outgoing Response Payload Structure
```json
{
  "patient_id": "PAT-001",
  "patient_name": "John Mitchell",
  "eligibility": {
    "eligible": true,
    "coverage_status": "Active" | "Inactive" | "Suspended" | "Terminated",
    "effective_date": "2024-01-01",
    "termination_date": "2026-07-01",
    "copay_amount": 30,
    "deductible_met": 1250,
    "deductible_total": 2000
  },
  "prior_auth_history": [
    {
      "auth_id": "AUTH-001",
      "procedure": "Total Knee Replacement",
      "procedure_code": "27447",
      "requested_date": "2026-08-11",
      "decision_date": "2026-08-11",
      "status": "Approved" | "Denied" | "Pending",
      "notes": "All policy criteria satisfied."
    }
  ],
  "claim_history": [
    {
      "claim_id": "CLM-001",
      "procedure": "Total Knee Replacement",
      "procedure_code": "27447",
      "service_date": "2026-08-20",
      "amount_billed": 35000,
      "amount_paid": 28000,
      "status": "Accepted" | "Rejected" | "In Progress"
    }
  ],
  "utilization_frequency": {
    "visits_this_year": 14,
    "max_allowed_visits_per_year": 30,
    "procedures_performed": 2,
    "er_visits": 0,
    "pt_sessions_count": 12,
    "pt_sessions_allowed": 20
  },
  "coverage_details": {
    "plan_type": "PPO" | "HMO",
    "group_number": "AET-GRP-9012",
    "subscriber_id": "SUB-AET-5541",
    "benefit_details": {
      "in_network_coverage_percent": 80,
      "out_of_network_coverage_percent": 60,
      "max_out_of_pocket": 5000,
      "max_out_of_pocket_met": 1850
    }
  }
}
```

* **HTTP Method:** `PUT`
* **Endpoint:** `/api/insurance/patients/{patient_id}/administrative`
* **Content-Type:** `application/json`

#### Incoming Request Payload Structure (Partial Update)
```json
{
  "eligibility": {
    "coverage_status": "Inactive",
    "termination_date": "2026-07-01"
  }
}
```

---

## 3. Real-Time WebSockets

For active claims and simulation workflows, the frontend supports WebSocket channels to update status bars, extraction lists, and processing timelines dynamically without page polling.

### 3.1 Authorization Case Processing Socket
* **Endpoint:** `/ws/authorizations/{authorization_id}`
* **Payload Event Structure:**
```json
{
  "event": "PROCESSING_STEP",
  "authorization_id": "CLM-005",
  "step": "POLICY_RETRIEVAL" | "VALIDATION" | "DOCUMENT_UPLOAD" | "EXTRACTION" | "CROSS_VERIFICATION" | "DECISION" | "COMPLETED",
  "status": "IN_PROGRESS" | "COMPLETED" | "FAILED",
  "message": "Policy retrieved: Cigna Imaging Authorization Policy (CGN-IMG-002)"
}
```

### 3.2 Simulation Progress Socket
* **Endpoint:** `/ws/simulation/{simulation_id}`
* **Payload Event Sequence Example:**
```json
{ "event": "PATIENT_GENERATED", "patient_id": "PAT-009" }
{ "event": "MEDICAL_HISTORY_LOADED", "patient_id": "PAT-009" }
{ "event": "AUTHORIZATION_CREATED", "authorization_id": "CLM-009" }
{ "event": "SUBMITTED", "authorization_id": "CLM-009" }
```

---

## 4. Summary of Frontend Status Enums

To ensure seamless coordination, the backend database fields for claim status should match the following definitions:

| Status Code | Description | Next Allowed State / Actions |
|-------------|-------------|------------------------------|
| `DRAFT` | Initial claim draft | `SUBMITTED` |
| `SUBMITTED` | Submitted, awaiting Agent 1 evaluation | `PROCESSING` |
| `PROCESSING` | AI agent analyzing documents & policies | `UNDER_REVIEW` |
| `UNDER_REVIEW` | RAG context checks executing | `ACCEPTED` / `REJECTED` / `MORE_INFO` / `HUMAN_REVIEW` |
| `ACCEPTED` | Claim approved; criteria satisfied | None (Terminal) |
| `REJECTED` | Claim denied; criteria not met | `RESUBMISSION_CHECK` (if resubmission eligible) |
| `MORE_INFO` | Awaiting missing documents | `SUBMITTED_AGAIN` (after provider uploads documents) |
| `HUMAN_REVIEW` | Escalated to clinical reviewer queue | `ACCEPTED` / `REJECTED` / `MORE_INFO` (via Reviewer Queue) |
| `RESUBMISSION_CHECK` | Provider evaluating resubmission likelihood | `SUBMITTED_AGAIN` |
| `SUBMITTED_AGAIN` | Re-evaluating claim with new evidence | `PROCESSING` / `ACCEPTED` / `REJECTED` |

---

## 5. Client-Side Live Sync & Polling Architecture

To enable a real-time reactive interface without requiring backend database triggers or manual page refreshes:
- **Silent Background Polling:** The main dashboards, tables, and queues query `GET /api/claims`, `GET /api/insurance/claims`, and `GET /api/reviews` every 2 seconds.
- **Visual Performance:** Polling updates execute silently in the background (no loader overlays or layout flickers after the initial load). This allows live events—such as simulation runs changing claim status from `PROCESSING` to `ACCEPTED`, or manual reviews completing—to propagate to both the hospital and insurance panels in real-time.
