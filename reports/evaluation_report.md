# Prior Authorization Retrieval RAG Evaluation Report

Generated: 2026-08-14 15:28:49

## Summary Metrics

| Metric | Target Value | Measured Value | Status |
|---|---|---|---|
| **Recall@1** | >= 0.85 | 0.9524 | PASSED |
| **Recall@3** | >= 0.90 | 1.0000 | PASSED |
| **Recall@5** | >= 0.95 | 1.0000 | PASSED |
| **Mean Reciprocal Rank (MRR)** | >= 0.90 | 0.9762 | PASSED |
| **Policy Match Accuracy** | >= 0.95 | 1.0000 | PASSED |
| **Cross-Policy Contamination** | 0.00% | 0.00% | PASSED |

## Evaluation Test Cases Detail

| Case ID | Expected Policy | Selected Policy | Match? | Contaminated? | Score |
|---|---|---|---|---|---|
| `pacemaker_exact` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.9188 |
| `pacemaker_no_id` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.7136 |
| `pacemaker_semantic` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.6545 |
| `icd_exact` | `NCD-20.4` | `NCD-20.4` | ✅ Yes | ✅ No (0%) | 0.9415 |
| `icd_no_id` | `NCD-20.4` | `NCD-20.4` | ✅ Yes | ✅ No (0%) | 0.8929 |
| `mammogram_exact` | `NCD-220.4` | `NCD-220.4` | ✅ Yes | ✅ No (0%) | 0.9882 |
| `mammogram_no_id` | `NCD-220.4` | `NCD-220.4` | ✅ Yes | ✅ No (0%) | 0.9370 |
| `colorectal_exact` | `NCD-210.3` | `NCD-210.3` | ✅ Yes | ✅ No (0%) | 0.9424 |
| `colorectal_no_id` | `NCD-210.3` | `NCD-210.3` | ✅ Yes | ✅ No (0%) | 0.9580 |
| `pet_exact` | `NCD-220.6.17` | `NCD-220.6.17` | ✅ Yes | ✅ No (0%) | 0.9641 |
| `pet_no_id` | `NCD-220.6.17` | `NCD-220.6.17` | ✅ Yes | ✅ No (0%) | 0.9591 |
| `knee_exact` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.8785 |
| `knee_no_id` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.7656 |
| `hip_exact` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.8351 |
| `hip_no_id` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.8617 |
| `breast_imaging_exact` | `LCD-L33950` | `LCD-L33950` | ✅ Yes | ✅ No (0%) | 0.9139 |
| `breast_imaging_no_id` | `LCD-L33950` | `LCD-L33950` | ✅ Yes | ✅ No (0%) | 0.7679 |
| `hard_neg_knee_vs_hip` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.8266 |
| `hard_neg_hip_vs_knee` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.7939 |
| `conflict_case` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.6341 |
| `unknown_case` | `NO_RELIABLE_POLICY_MATCH` | `NO_RELIABLE_POLICY_MATCH` | ✅ Yes | ✅ No (0%) | 0.0000 |
