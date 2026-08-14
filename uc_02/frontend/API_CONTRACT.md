# Frontend <-> Backend API Contract (UC02)

This document outlines the API endpoints, data models, and WebSocket events that the frontend expects the backend to support. The frontend is built strictly around these interfaces.

---

## 1. Core Data Models

### 1.1 `AuthorizationCase`
This is the central object that everything revolves around.

```json
{
  "authorization_id": "AUTH-2026-00001",
  "source": "manual", 
  "status": "PROCESSING",
  "patient": {
    "patient_id": "SYN-001",
    "name": "John Doe",
    "age": 57,
    "gender": "Male"
  },
  "insurance": {
    "provider": "Demo Payer",
    "member_id": "SYN-INS-001",
    "plan": "Gold"
  },
  "request": {
    "procedure": "Knee Replacement",
    "diagnosis": "Osteoarthritis",
    "reason": "Severe pain and functional limitation"
  },
  "documents": [],
  "decision": null,
  "created_at": "2026-08-11T10:30:00Z",
  "updated_at": "2026-08-11T10:31:00Z"
}
```
**`source` values:** `"manual"` | `"simulation"`

**`status` enum:**
- `DRAFT`
- `UPLOADING`
- `PROCESSING`
- `VALIDATION_FAILED`
- `EXTRACTION_COMPLETED`
- `POLICY_ANALYSIS`
- `DECISION_READY`
- `MORE_INFORMATION`
- `HUMAN_REVIEW`
- `APPROVED`
- `REJECTED`
- `EMERGENCY`

**`decision` enum:**
- `APPROVE`
- `REJECT`
- `MORE_INFORMATION`
- `HUMAN_REVIEW`
- `EMERGENCY`

---

## 2. API Endpoints

### 2.1 Hospital Portal

#### **GET** `/api/hospital/dashboard`
**Response:**
```json
{
  "total_cases": 128,
  "pending_cases": 23,
  "approved_cases": 82,
  "rejected_cases": 14,
  "more_information_cases": 6,
  "human_review_cases": 3,
  "recent_cases": [
    {
      "authorization_id": "AUTH-001",
      "patient_id": "SYN-001",
      "procedure": "Knee Replacement",
      "status": "APPROVED",
      "created_at": "2026-08-11T10:30:00Z"
    }
  ]
}
```

#### **POST** `/api/documents/upload`
**Request:** `multipart/form-data`
- `file`: The document file
- `authorization_id`: String (optional during initial creation)
- `document_type`: String (e.g. `doctor_report`, `diagnostic_report`, `treatment_history`, `insurance_document`, `supporting_document`, `other`)

**Response:**
```json
{
  "document_id": "DOC-001",
  "file_name": "MRI_Report.pdf",
  "document_type": "diagnostic_report",
  "status": "UPLOADED"
}
```

#### **POST** `/api/authorizations`
**Request:**
```json
{
  "source": "manual",
  "patient": {
    "patient_id": "SYN-001",
    "name": "John Doe",
    "age": 57,
    "gender": "Male"
  },
  "insurance": {
    "member_id": "SYN-INS-001",
    "plan": "Gold"
  },
  "request": {
    "procedure": "Knee Replacement",
    "diagnosis": "Osteoarthritis",
    "reason": "Severe pain and functional limitation",
    "previous_treatment": "Physical therapy for 14 weeks",
    "clinical_findings": "Reduced mobility"
  },
  "document_ids": [
    "DOC-001",
    "DOC-002",
    "DOC-003"
  ]
}
```
**Response:**
```json
{
  "authorization_id": "AUTH-2026-00001",
  "status": "PROCESSING",
  "message": "Authorization request created"
}
```

#### **POST** `/api/simulation/start`
**Request:**
```json
{
  "count": 1,
  "scenario": "STANDARD"
}
```
**Response:**
```json
{
  "simulation_id": "SIM-001",
  "status": "STARTED"
}
```

---

### 2.2 Insurance Portal

#### **GET** `/api/insurance/dashboard`
**Response:**
```json
{
  "new_cases": 32,
  "ai_ready_cases": 18,
  "human_review_cases": 7,
  "completed_cases": 104,
  "priority_queue": [
    {
      "authorization_id": "AUTH-001",
      "procedure": "Knee Replacement",
      "priority": "HIGH",
      "status": "HUMAN_REVIEW"
    }
  ]
}
```

#### **GET** `/api/insurance/cases`
**Query Parameters:** `?status=HUMAN_REVIEW&priority=HIGH&page=1&limit=20`

**Response:**
```json
{
  "cases": [
    {
      "authorization_id": "AUTH-001",
      "patient_id": "SYN-001",
      "procedure": "Knee Replacement",
      "priority": "HIGH",
      "status": "HUMAN_REVIEW",
      "created_at": "..."
    }
  ],
  "total": 7
}
```

#### **POST** `/api/insurance/cases/{id}/decision`
**Request:**
```json
{
  "decision": "APPROVE",
  "comment": "Reviewed conflicting treatment records."
}
```
**Response:**
```json
{
  "authorization_id": "AUTH-001",
  "status": "APPROVED",
  "decision": "APPROVE",
  "reviewed_by": "EMP-001",
  "reviewed_at": "2026-08-11T11:00:00Z"
}
```

#### **POST** `/api/insurance/cases/{id}/request-information`
**Request:**
```json
{
  "required_documents": [
    "treatment_history",
    "pt_documentation"
  ],
  "message": "Please provide the missing treatment documentation."
}
```
**Response:**
```json
{
  "authorization_id": "AUTH-001",
  "status": "MORE_INFORMATION",
  "requested_documents": [
    "treatment_history",
    "pt_documentation"
  ]
}
```

#### **POST** `/api/authorizations/{id}/resubmit`
Triggered by the hospital after uploading additional requested documents.
**Response:**
```json
{
  "authorization_id": "AUTH-001",
  "status": "PROCESSING"
}
```

---

## 3. WebSockets

WebSockets are used by the frontend for real-time visualization of processing and simulation steps.

### 3.1 Authorization Processing
**Endpoint:** `/ws/authorizations/{authorization_id}`

**Event Payload:**
```json
{
  "event": "PROCESSING_STEP",
  "authorization_id": "AUTH-2026-00001",
  "step": "EXTRACTION",
  "status": "COMPLETED",
  "message": "Clinical information extracted"
}
```
**Valid Steps:** `VALIDATION`, `DOCUMENT_UPLOAD`, `EXTRACTION`, `POLICY_RETRIEVAL`, `CROSS_VERIFICATION`, `DECISION`, `COMPLETED`

### 3.2 Simulation Processing
**Endpoint:** `/ws/simulation/{simulation_id}`

**Event Payload sequence example:**
```json
{ "event": "PATIENT_GENERATED", "patient_id": "SYN-10042" }
{ "event": "MEDICAL_HISTORY_LOADED", "patient_id": "SYN-10042" }
{ "event": "AUTHORIZATION_CREATED", "authorization_id": "AUTH-0042" }
{ "event": "SUBMITTED", "authorization_id": "AUTH-0042" }
```

---
## Note
The frontend logic relies on these contracts remaining stable. The UI uses the status enums and data models provided here to render the different states, badges, and queues. Decision logic remains entirely backend-side.
