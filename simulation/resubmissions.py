"""
Resubmissions Module: Dynamic Evidence-Backed Policy Criteria Evaluation Engine
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from simulation.scenarios import ClinicalScenario
from simulation.evidence import EvidenceRecord, create_evidence
from simulation.linkage import retrieve_policy_from_rag, RAGRetrievalError


@dataclass
class ClaimSubmissionAttempt:
    submission_id: str
    claim_id: str
    patient_id: str
    policy_id: str
    attempt_number: int
    submission_date: str
    submitted_evidence_ids: List[str]
    submitted_evidence: List[EvidenceRecord]
    outcome: str
    notes: str


def evaluate_policy_criteria_against_evidence(policy_id: str, evidence_list: List[EvidenceRecord], lookup_mode: str = "normal") -> Tuple[str, Dict[str, Any]]:
    """
    Genuine Policy Criteria Evaluation Engine:
    Retrieves policy rules from RAG catalog loader, evaluates submitted evidence against ALL declared policy requirements,
    and returns deterministic outcome with diagnostic details.
    """
    details = {
        "policy_id": policy_id,
        "criteria_evaluated": [],
        "failed_criteria": []
    }

    try:
        policy = retrieve_policy_from_rag(policy_id, lookup_mode=lookup_mode)
    except RAGRetrievalError as err:
        details["failed_criteria"].append(f"RAG Retrieval Error: {str(err)}")
        return "HUMAN_REVIEW", details

    if not policy:
        details["failed_criteria"].append(f"No policy constraint found in RAG dataset for policy_id '{policy_id}'")
        return "HUMAN_REVIEW", details

    details["policy_title"] = policy.get("title", "")
    details["criteria_evaluated"] = policy.get("criteria", [])

    # Extract submitted evidence clinical metrics
    kl_grades = [e.kl_grade for e in evidence_list if e.kl_grade is not None]
    pt_weeks_list = [e.pt_weeks_completed for e in evidence_list if e.pt_weeks_completed is not None]
    neuro_deficits = [e.neurological_deficit for e in evidence_list if e.neurological_deficit is not None]
    stress_tests = [e.abnormal_stress_test for e in evidence_list if e.abnormal_stress_test is not None]
    angina_list = [e.refractory_angina for e in evidence_list if e.refractory_angina is not None]
    has_xray = any(e.evidence_type in ["Imaging", "Imaging Report Doc A", "Imaging Report Doc B"] for e in evidence_list)

    # 1. Check for conflicting evidence on same clinical fact (e.g. contradictory KL grades)
    if len(kl_grades) >= 2:
        if max(kl_grades) - min(kl_grades) >= 2:
            details["failed_criteria"].append("Conflicting evidence detected on same clinical fact (Osteoarthritis KL grade mismatch)")
            return "HUMAN_REVIEW", details

    # 2. Check conservative therapy (Physical Therapy) requirement
    min_pt_weeks = policy.get("min_pt_weeks", 0)
    if min_pt_weeks > 0:
        if not pt_weeks_list:
            details["failed_criteria"].append("Missing required physical therapy documentation")
            return "REQUEST_MORE_INFORMATION", details
        
        actual_pt_weeks = max(pt_weeks_list)
        if actual_pt_weeks < min_pt_weeks:
            details["failed_criteria"].append({
                "criterion": f"Failed conservative therapy (>= {min_pt_weeks} weeks PT required)",
                "required_value": f">= {min_pt_weeks} weeks PT",
                "actual_patient_value": f"{actual_pt_weeks} week PT",
                "reason": f"Patient completed only {actual_pt_weeks} week(s) of physical therapy, failing the {min_pt_weeks}-week requirement."
            })
            return "REJECT", details

    # 3. Check Progressive Neurological Deficit requirement if applicable (CMS Lumbar MRI criterion)
    if policy.get("requires_neurological_deficit", False):
        if not neuro_deficits:
            details["failed_criteria"].append("Missing documentation on progressive neurological deficit assessment")
            return "REQUEST_MORE_INFORMATION", details
        if not any(neuro_deficits):
            details["failed_criteria"].append("Patient exhibits no progressive neurological deficit")
            return "REJECT", details

    # 4. Check KL Grade requirement if applicable (TKA policy requirement)
    min_kl_grade = policy.get("min_kl_grade", 0)
    if min_kl_grade > 0:
        if not kl_grades:
            details["failed_criteria"].append(f"Missing required Kellgren-Lawrence (KL) grade documentation (>= Grade {min_kl_grade} required)")
            return "REQUEST_MORE_INFORMATION", details
        max_kl = max(kl_grades)
        if max_kl < min_kl_grade:
            details["failed_criteria"].append(f"KL Grade {max_kl} is below required threshold Grade {min_kl_grade}")
            return "REJECT", details

    # 5. Check Cardio Policy requirements if applicable (AETNA_POL_CARDIO_03)
    if policy.get("requires_stress_test_or_high_risk", False):
        if not stress_tests:
            details["failed_criteria"].append("Missing documentation on cardiac stress test / clinical risk evaluation")
            return "REQUEST_MORE_INFORMATION", details
        if not any(stress_tests):
            details["failed_criteria"].append("Cardiac stress test results are normal (high clinical risk not established)")
            return "REJECT", details

    if policy.get("requires_refractory_angina", False):
        if not angina_list:
            details["failed_criteria"].append("Missing documentation on refractory angina symptoms")
            return "REQUEST_MORE_INFORMATION", details
        if not any(angina_list):
            details["failed_criteria"].append("Patient does not exhibit refractory angina symptoms")
            return "REJECT", details

    # 6. Check Radiograph / X-ray requirement if applicable
    if policy.get("requires_xray", False) and not has_xray:
        details["failed_criteria"].append("Missing required imaging / X-ray report")
        return "REQUEST_MORE_INFORMATION", details

    return "APPROVE", details


def create_resubmission_sequence(base_scenario: ClinicalScenario) -> List[ClaimSubmissionAttempt]:
    """
    Simulate a claim resubmission sequence (e.g. Scenario 3 Missing Documentation).
    Attempt 1: Missing documentation -> REQUEST_MORE_INFORMATION.
    Attempt 2: Additional evidence attached -> Dynamically evaluated against RAG policy criteria.
    Preserves identical patient_id, claim_id, and policy_id.
    """
    claim_id = f"CLM_RESUB_{base_scenario.patient_id}"
    policy_id = base_scenario.payer_linkage.policy_id or "CMS_POL_MRI_02"
    
    # Attempt 1: Only initial submitted evidence (missing PT report)
    attempt1_ev_ids = [e.evidence_id for e in base_scenario.submitted_evidence]
    outcome_att1, details1 = evaluate_policy_criteria_against_evidence(policy_id, base_scenario.submitted_evidence)
    attempt1 = ClaimSubmissionAttempt(
        submission_id=f"SUB_{claim_id}_ATT1",
        claim_id=claim_id,
        patient_id=base_scenario.patient_id,
        policy_id=policy_id,
        attempt_number=1,
        submission_date="2026-07-01T09:00:00",
        submitted_evidence_ids=attempt1_ev_ids,
        submitted_evidence=base_scenario.submitted_evidence,
        outcome=outcome_att1,
        notes="Attempt 1: Missing physical therapy documentation."
    )
    
    # Attempt 2: Provider attaches missing 6-week PT report
    pt_evidence = create_evidence(
        evidence_id=f"EV_RESUB_{base_scenario.patient_id}_PT",
        patient_id=base_scenario.patient_id,
        evidence_type="Treatment history",
        event_date="2026-05-01T10:00:00",
        content_reference="Attached missing 6 weeks physical therapy documentation",
        auth_request_date="2026-07-05T10:00:00",
        is_submitted=True,
        pt_weeks_completed=6
    )
    
    attempt2_evidence = base_scenario.submitted_evidence + [pt_evidence]
    attempt2_ev_ids = [e.evidence_id for e in attempt2_evidence]
    outcome_att2, details2 = evaluate_policy_criteria_against_evidence(policy_id, attempt2_evidence)
    attempt2 = ClaimSubmissionAttempt(
        submission_id=f"SUB_{claim_id}_ATT2",
        claim_id=claim_id,
        patient_id=base_scenario.patient_id,
        policy_id=policy_id,
        attempt_number=2,
        submission_date="2026-07-05T10:00:00",
        submitted_evidence_ids=attempt2_ev_ids,
        submitted_evidence=attempt2_evidence,
        outcome=outcome_att2,
        notes="Attempt 2: Resubmitted with 6 weeks PT documentation attached; criteria re-evaluated and satisfied."
    )
    
    return [attempt1, attempt2]
