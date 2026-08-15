"""
Scenarios Module: Data Generators for the 8 V1 Clinical Scenarios
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from simulation.evidence import EvidenceRecord, create_evidence
from simulation.linkage import PayerLinkage, create_patient_payer_linkage


@dataclass
class ClinicalScenario:
    scenario_id: int
    name: str
    patient_id: str
    payer_linkage: PayerLinkage
    cpt_codes: List[str]
    description: str
    expected_decision: str
    available_evidence: List[EvidenceRecord] = field(default_factory=list)
    submitted_evidence: List[EvidenceRecord] = field(default_factory=list)
    failed_criterion_details: Optional[Dict[str, Any]] = None
    resubmission_attempt: int = 1


def generate_8_scenarios() -> List[ClinicalScenario]:
    """
    Construct the 8 genuine V1 clinical scenarios using actual clinical conditions and structured evidence metrics.
    """
    scenarios = []

    # 1. Eligible -> APPROVE
    p1_linkage = create_patient_payer_linkage("PA001", payer_id="Aetna", plan_id="AETNA_GOLD_PPO", policy_id="AETNA_POL_KNEE_01")
    e1_1 = create_evidence("EV_001_1", "PA001", "Imaging", "2026-06-01T10:00:00", "X-ray Knee: Kellgren-Lawrence Grade 4 severe OA", auth_request_date="2026-07-01T09:00:00", kl_grade=4)
    e1_2 = create_evidence("EV_001_2", "PA001", "Treatment history", "2026-05-15T14:30:00", "PT Notes: 8 weeks completed physical therapy", auth_request_date="2026-07-01T09:00:00", pt_weeks_completed=8)
    scenarios.append(ClinicalScenario(
        scenario_id=1,
        name="Eligible",
        patient_id="PA001",
        payer_linkage=p1_linkage,
        cpt_codes=["27447"],
        description="Patient PA001 meets all criteria for Total Knee Arthroplasty (KL Grade 4 OA, 8 wks PT).",
        expected_decision="APPROVE",
        available_evidence=[e1_1, e1_2],
        submitted_evidence=[e1_1, e1_2]
    ))

    # 2. Failed criterion -> REJECT
    p2_linkage = create_patient_payer_linkage("PA002", payer_id="Aetna", plan_id="AETNA_GOLD_PPO", policy_id="AETNA_POL_KNEE_01")
    e2_1 = create_evidence("EV_002_1", "PA002", "Imaging", "2026-06-01T10:00:00", "X-ray: Kellgren-Lawrence Grade 3 OA", auth_request_date="2026-07-01T09:00:00", kl_grade=3)
    e2_2 = create_evidence("EV_002_2", "PA002", "Treatment history", "2026-06-20T11:00:00", "PT Notes: 1 week completed physical therapy (discontinued)", auth_request_date="2026-07-01T09:00:00", pt_weeks_completed=1)
    failed_details = {
        "policy_id": "AETNA_POL_KNEE_01",
        "criterion": "Failed conservative therapy (>= 6 weeks PT required)",
        "required_value": ">= 6 weeks PT",
        "actual_patient_value": "1 week PT",
        "supporting_evidence_id": "EV_002_2",
        "reason": "Patient completed only 1 week of physical therapy, failing the 6-week conservative therapy requirement."
    }
    scenarios.append(ClinicalScenario(
        scenario_id=2,
        name="Failed criterion",
        patient_id="PA002",
        payer_linkage=p2_linkage,
        cpt_codes=["27447"],
        description="Patient PA002 failed conservative therapy requirement (1 week completed vs 6 weeks required).",
        expected_decision="REJECT",
        available_evidence=[e2_1, e2_2],
        submitted_evidence=[e2_1, e2_2],
        failed_criterion_details=failed_details
    ))

    # 3. Missing documentation -> REQUEST_MORE_INFORMATION
    p3_linkage = create_patient_payer_linkage("PA003", payer_id="CMS", plan_id="CMS_MEDICARE_ADVANTAGE", policy_id="CMS_POL_MRI_02")
    e3_1 = create_evidence("EV_003_1", "PA003", "Imaging", "2026-06-10T09:00:00", "Lumbar X-ray report completed; progressive neurological deficit noted", auth_request_date="2026-07-01T09:00:00", is_submitted=True, neurological_deficit=True)
    e3_2 = create_evidence("EV_003_2", "PA003", "Treatment history", "2026-05-01T10:00:00", "6 weeks physical therapy notes", auth_request_date="2026-07-01T09:00:00", is_submitted=False, pt_weeks_completed=6)
    scenarios.append(ClinicalScenario(
        scenario_id=3,
        name="Missing documentation",
        patient_id="PA003",
        payer_linkage=p3_linkage,
        cpt_codes=["72148"],
        description="Lumbar MRI policy requires 6 weeks PT documentation; PT notes exist in patient DB but were omitted from submission.",
        expected_decision="REQUEST_MORE_INFORMATION",
        available_evidence=[e3_1, e3_2],
        submitted_evidence=[e3_1]
    ))

    # 4. Conflicting evidence -> HUMAN_REVIEW
    p4_linkage = create_patient_payer_linkage("PA004", payer_id="Aetna", plan_id="AETNA_GOLD_PPO", policy_id="AETNA_POL_KNEE_01")
    e4_1 = create_evidence("EV_004_1", "PA004", "Imaging Report Doc A", "2026-06-01T10:00:00", "Radiology Report A: Severe Kellgren-Lawrence Grade 4 Osteoarthritis", auth_request_date="2026-07-01T09:00:00", kl_grade=4)
    e4_2 = create_evidence("EV_004_2", "PA004", "Imaging Report Doc B", "2026-06-05T14:00:00", "Radiology Report B: Mild joint space loss, Grade 1 No OA", auth_request_date="2026-07-01T09:00:00", kl_grade=1)
    scenarios.append(ClinicalScenario(
        scenario_id=4,
        name="Conflicting evidence",
        patient_id="PA004",
        payer_linkage=p4_linkage,
        cpt_codes=["27447"],
        description="Submitted radiology report A says Grade 4 OA, while submitted radiology report B says Grade 1 No OA.",
        expected_decision="HUMAN_REVIEW",
        available_evidence=[e4_1, e4_2],
        submitted_evidence=[e4_1, e4_2]
    ))

    # 5. Unknown payer -> HUMAN_REVIEW
    p5_linkage = create_patient_payer_linkage("PA005", payer_id="UNKNOWN_PAYER_INC", plan_id="UNKNOWN_PLAN", policy_id=None, mismatch=True)
    e5_1 = create_evidence("EV_005_1", "PA005", "Clinical Document", "2026-06-01T10:00:00", "General consultation record", auth_request_date="2026-07-01T09:00:00")
    scenarios.append(ClinicalScenario(
        scenario_id=5,
        name="Unknown payer",
        patient_id="PA005",
        payer_linkage=p5_linkage,
        cpt_codes=["27447"],
        description="Payer record cannot be resolved or linked for member PA005.",
        expected_decision="HUMAN_REVIEW",
        available_evidence=[e5_1],
        submitted_evidence=[e5_1]
    ))

    # 6. Multiple procedures -> STRUCTURAL_VALIDATION_PASS
    p6_linkage = create_patient_payer_linkage("PA006", payer_id="Aetna", plan_id="AETNA_GOLD_PPO", policy_id="AETNA_POL_KNEE_01")
    e6_1 = create_evidence("EV_006_1", "PA006", "Consultation", "2026-06-01T10:00:00", "Surgical plan detailing multi-procedure intervention", auth_request_date="2026-07-01T09:00:00")
    scenarios.append(ClinicalScenario(
        scenario_id=6,
        name="Multiple procedures",
        patient_id="PA006",
        payer_linkage=p6_linkage,
        cpt_codes=["27447", "27487"],
        description="Claim requests multiple procedure codes (27447 and 27487) which must all be preserved under the single claim.",
        expected_decision="STRUCTURAL_VALIDATION_PASS",
        available_evidence=[e6_1],
        submitted_evidence=[e6_1]
    ))

    # 7. RAG failure -> HUMAN_REVIEW (Executes real RAGRetrievalError failure path)
    p7_linkage = create_patient_payer_linkage(
        "PA007",
        payer_id="Aetna",
        plan_id="AETNA_GOLD_PPO",
        policy_id="AETNA_POL_KNEE_01",
        policy_lookup_mode="intentional_rag_failure",
        failure_reason="Policy retrieval failed due to corrupted index query"
    )
    e7_1 = create_evidence("EV_007_1", "PA007", "Clinical Document", "2026-06-01T10:00:00", "Note for rare experimental procedure", auth_request_date="2026-07-01T09:00:00")
    scenarios.append(ClinicalScenario(
        scenario_id=7,
        name="RAG failure",
        patient_id="PA007",
        payer_linkage=p7_linkage,
        cpt_codes=["99999"],
        description="RAG policy retrieval pipeline fails due to corrupted index query.",
        expected_decision="HUMAN_REVIEW",
        available_evidence=[e7_1],
        submitted_evidence=[e7_1]
    ))

    # 8. No policy constraint -> HUMAN_REVIEW
    p8_linkage = create_patient_payer_linkage(
        "PA008",
        payer_id="Aetna",
        plan_id="AETNA_GOLD_PPO",
        policy_id=None,
        policy_lookup_mode="no_policy_established"
    )
    e8_1 = create_evidence("EV_008_1", "PA008", "Consultation", "2026-06-01T10:00:00", "Specialized pediatric procedure request", auth_request_date="2026-07-01T09:00:00")
    scenarios.append(ClinicalScenario(
        scenario_id=8,
        name="No policy constraint",
        patient_id="PA008",
        payer_linkage=p8_linkage,
        cpt_codes=["0001T"],
        description="Legitimate claim request where no applicable policy can safely be established from existing RAG dataset.",
        expected_decision="HUMAN_REVIEW",
        available_evidence=[e8_1],
        submitted_evidence=[e8_1]
    ))

    return scenarios
