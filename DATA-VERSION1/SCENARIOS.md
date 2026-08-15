# CTS V1 Clinical Scenarios Documentation

| # | Scenario | Patient ID | Payer | Plan | Policy ID | Expected Result | Description |
|---|---|---|---|---|---|---|---|
| 1 | Eligible | PA001 | Aetna | AETNA_GOLD_PPO | AETNA_POL_KNEE_01 | `APPROVE` | Patient PA001 meets all criteria for Total Knee Arthroplasty (KL Grade 4 OA, 8 wks PT). |
| 2 | Failed criterion | PA002 | Aetna | AETNA_GOLD_PPO | AETNA_POL_KNEE_01 | `REJECT` | Patient PA002 failed conservative therapy requirement (1 week completed vs 6 weeks required). |
| 3 | Missing documentation | PA003 | CMS | CMS_MEDICARE_ADVANTAGE | CMS_POL_MRI_02 | `REQUEST_MORE_INFORMATION` | Lumbar MRI policy requires 6 weeks PT documentation; PT notes exist in patient DB but were omitted from submission. |
| 4 | Conflicting evidence | PA004 | Aetna | AETNA_GOLD_PPO | AETNA_POL_KNEE_01 | `HUMAN_REVIEW` | Submitted radiology report A says Grade 4 OA, while submitted radiology report B says Grade 1 No OA. |
| 5 | Unknown payer | PA005 | UNKNOWN_PAYER_INC | UNKNOWN_PLAN | N/A (No Policy Established) | `HUMAN_REVIEW` | Payer record cannot be resolved or linked for member PA005. |
| 6 | Multiple procedures | PA006 | Aetna | AETNA_GOLD_PPO | AETNA_POL_KNEE_01 | `STRUCTURAL_VALIDATION_PASS` | Claim requests multiple procedure codes (27447 and 27487) which must all be preserved under the single claim. |
| 7 | RAG failure | PA007 | Aetna | AETNA_GOLD_PPO | AETNA_POL_KNEE_01 | `HUMAN_REVIEW` | RAG policy retrieval pipeline fails due to corrupted index query. |
| 8 | No policy constraint | PA008 | Aetna | AETNA_GOLD_PPO | N/A (No Policy Established) | `HUMAN_REVIEW` | Legitimate claim request where no applicable policy can safely be established from existing RAG dataset. |


## Resubmission Handling
Scenario 3 (PA003) supports multi-attempt resubmissions persisted in `big_patient_data.db`:
- **Attempt 1 (`SUB_CLM_RESUB_PA003_ATT1`)**: Missing physical therapy documentation -> `REQUEST_MORE_INFORMATION`
- **Attempt 2 (`SUB_CLM_RESUB_PA003_ATT2`)**: Provider attaches missing 6-week PT report (`EV_RESUB_PA003_PT`) under same claim ID (`CLM_RESUB_PA003`) -> `APPROVE`
