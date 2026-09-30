# ORCA Frontend API Contract

Every page's API calls, request/response shapes, polling behavior, and mock backing.

---

## Base URL
All endpoints are relative to `/api` (or `VITE_API_BASE_URL` env var).

---

## Pages & API Calls

### `/` — Role Select
No API calls. Sets role in `RoleContext` and navigates to dashboard.

---

### `/hospital/dashboard` — Hospital Dashboard
| Method | Endpoint | Mock File | Mock Function |
|--------|----------|-----------|---------------|
| GET | `/api/claims` | `mock/claims.ts` | `mockClaims` (flat list) |

**Response shape:**
```ts
Claim[]
// { claim_id, patient_id, hospital, procedure, procedure_code,
//   diagnosis_codes, service_date, status, submitted_at, updated_at }
```
No polling.

---

### `/hospital/claims/new` — Create Claim
| Method | Endpoint | Mock File | Mock Function |
|--------|----------|-----------|---------------|
| POST | `/api/claims` | `mock/claims.ts` | `claimsStore` (in-memory push) |

**Request shape:**
```ts
{ patient_id: string; procedure_code: string; procedure: string;
  diagnosis_codes: string[]; service_date: string;
  provider_id?: string; payer: string; policy_id: string; }
```
**Response shape:** `ClaimDetails` — the newly created claim.

On success: redirects to `/hospital/claims/:id`.

---

### `/hospital/claims` — Claims List
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/claims` | `mock/claims.ts` |

**Response shape:** `Claim[]`  
Status filter tabs applied client-side. No polling.

---

### `/hospital/claims/:id` — Hospital Claim Details *(centerpiece)*
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/claims/{id}` | `mock/claims.ts` → `mockClaimDetails` |
| GET | `/api/claims/{id}/resubmission` | `mock/resubmission.ts` |
| POST | `/api/claims/{id}/documents` | `documentApi.ts` (in-memory) |
| POST | `/api/claims/{id}/resubmit` | `claimsApi.ts` (in-memory) |

**GET response shape:** `ClaimDetails`
```ts
{ claim_id, patient, claim, policy, decision, policy_evidence[],
  missing_information[], resubmission, status, submitted_at, updated_at,
  hospital?, documents?, timeline? }
```

**Polling:** Every 5 seconds while `status` ∈ `{SUBMITTED, PROCESSING, UNDER_REVIEW}`.  
Stops when status reaches any terminal value: `ACCEPTED | REJECTED | MORE_INFO | HUMAN_REVIEW | RESUBMISSION_CHECK | SUBMITTED_AGAIN`.

**POST /documents request:**
```ts
FormData with files[]
```
**POST /documents response:**
```ts
{ claim_id: string; documents: DocumentRef[] }
```

**POST /resubmit response:**
```ts
{ success: boolean; claim_id: string }
```

---

### `/hospital/notifications` — Hospital Notifications
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/notifications` | `mock/notifications.ts` |

**Response shape:** `Notification[]`
```ts
{ notification_id, claim_id, message, type, read, created_at }
```
No polling.

---

### `/insurance/dashboard` — Insurance Dashboard
| Method | Endpoint |
|--------|----------|
| GET | `/api/insurance/claims` |
| GET | `/api/reviews` |

Response: `InsuranceClaim[]` + `ReviewItem[]`. No polling.

---

### `/insurance/claims` — Incoming Claims
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/insurance/claims` | `mock/insuranceClaims.ts` |

**Response shape:** `InsuranceClaim[]`
```ts
{ claim_id, hospital, patient_id, procedure, procedure_code,
  diagnosis_codes, service_date, status, submitted_at, updated_at, priority? }
```

---

### `/insurance/claims/:id` — Insurance Claim Details
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/insurance/claims/{id}` | `mock/claims.ts` → `mockClaimDetails` |
| POST | `/api/insurance/claims/{id}/decision` | `insuranceApi.ts` (in-memory) |

**GET response shape:** `ClaimDetails` (same as hospital side)

**POST /decision request:**
```ts
{ decision: "ACCEPT" | "REJECT" | "MORE_INFORMATION" | "HUMAN_REVIEW";
  reason_code: string;
  comments: string; }
```
**POST /decision response:**
```ts
{ success: boolean; claim_id: string; decision: string }
```

**Polling:** Same as hospital — every 5s while `status ∈ {SUBMITTED, PROCESSING, UNDER_REVIEW}`.

---

### `/insurance/review` — Review Queue
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/reviews` | `mock/reviews.ts` |

**Response shape:** `ReviewItem[]`
```ts
{ review_id, claim_id, hospital, patient_id, procedure,
  reason_for_review, assigned_at, status, priority }
```

---

### `/insurance/review/:id` — Review Detail
| Method | Endpoint | Mock File |
|--------|----------|-----------|
| GET | `/api/reviews/{id}` | `mock/reviews.ts` → `mockReviewDetails` |
| POST | `/api/reviews/{id}/decision` | `reviewApi.ts` (in-memory) |

**GET response shape:** `ReviewDetails`
```ts
ReviewItem & { claim_details: ClaimDetails; ai_recommendation: string; ai_confidence: number }
```

**POST /decision request:**
```ts
{ decision: "ACCEPT" | "REJECT" | "MORE_INFORMATION" | "HUMAN_REVIEW";
  reason_code: string;
  comments: string; }
```
**POST /decision response:**
```ts
{ success: boolean; review_id: string }
```

---

### `/insurance/notifications` — Insurance Notifications
Same as `/hospital/notifications` — `GET /api/notifications`.

---

## Endpoints NOT called by the frontend
The frontend **never** calls:
- `/api/rag/*`
- `/api/ml/*`
- `/api/vector-db/*`
- `/api/decision-engine/*`

---

## Swapping Mock → Real Backend
Each `src/services/*Api.ts` file reads from `src/mock/*`.  
To connect a real backend:
1. Set `VITE_API_BASE_URL=https://your-api.example.com` in `.env`
2. In each service file, replace `mockRequest(data)` with `apiFetch(endpoint, options)` from `src/services/api.ts`
3. No page or component code changes needed
