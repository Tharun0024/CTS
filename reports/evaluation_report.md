# Prior Authorization Retrieval RAG Evaluation Report

Generated: 2026-08-15 00:19:01

## Summary Metrics

| Metric | Target Value | Measured Value | Status |
|---|---|---|---|
| **Recall@1** | >= 0.85 | 0.9048 | PASSED |
| **Recall@3** | >= 0.90 | 1.0000 | PASSED |
| **Recall@5** | >= 0.95 | 1.0000 | PASSED |
| **Mean Reciprocal Rank (MRR)** | >= 0.90 | 0.9444 | PASSED |
| **Policy Match Accuracy** | >= 0.95 | 1.0000 | PASSED |
| **Cross-Policy Contamination** | 0.00% | 0.00% | PASSED |

## Evaluation Test Cases Detail

| Case ID | Expected Policy | Selected Policy | Match? | Contaminated? | Score |
|---|---|---|---|---|---|
| `pacemaker_exact` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.9525 |
| `pacemaker_no_id` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.9628 |
| `pacemaker_semantic` | `NCD-20.8.3` | `NCD-20.8.3` | ✅ Yes | ✅ No (0%) | 0.5356 |
| `icd_exact` | `NCD-20.4` | `NCD-20.4` | ✅ Yes | ✅ No (0%) | 0.9468 |
| `icd_no_id` | `NCD-20.4` | `NCD-20.4` | ✅ Yes | ✅ No (0%) | 0.8925 |
| `mammogram_exact` | `NCD-220.4` | `NCD-220.4` | ✅ Yes | ✅ No (0%) | 0.9908 |
| `mammogram_no_id` | `NCD-220.4` | `NCD-220.4` | ✅ Yes | ✅ No (0%) | 0.9743 |
| `colorectal_exact` | `NCD-210.3` | `NCD-210.3` | ✅ Yes | ✅ No (0%) | 0.9902 |
| `colorectal_no_id` | `NCD-210.3` | `NCD-210.3` | ✅ Yes | ✅ No (0%) | 0.8942 |
| `pet_exact` | `NCD-220.6.17` | `NCD-220.6.17` | ✅ Yes | ✅ No (0%) | 0.9940 |
| `pet_no_id` | `NCD-220.6.17` | `NCD-220.6.17` | ✅ Yes | ✅ No (0%) | 0.9769 |
| `knee_exact` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.9901 |
| `knee_no_id` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.7491 |
| `hip_exact` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.9681 |
| `hip_no_id` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.8822 |
| `breast_imaging_exact` | `LCD-L33950` | `LCD-L33950` | ✅ Yes | ✅ No (0%) | 0.9683 |
| `breast_imaging_no_id` | `LCD-L33950` | `LCD-L33950` | ✅ Yes | ✅ No (0%) | 0.8665 |
| `hard_neg_knee_vs_hip` | `LCD-L36575` | `LCD-L36575` | ✅ Yes | ✅ No (0%) | 0.8760 |
| `hard_neg_hip_vs_knee` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.7482 |
| `conflict_case` | `LCD-L36039` | `LCD-L36039` | ✅ Yes | ✅ No (0%) | 0.3476 |
| `unknown_case` | `NO_RELIABLE_POLICY_MATCH` | `NO_RELIABLE_POLICY_MATCH` | ✅ Yes | ✅ No (0%) | 0.0000 |
