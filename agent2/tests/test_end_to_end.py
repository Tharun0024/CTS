import json
import os
import sys
from datetime import datetime
from ..database.db_manager import get_db_connection
from ..database.repositories.claim_repository import ClaimRepository
from ..database.repositories.audit_repository import AuditRepository
from ..workflow.orchestrator import PriorAuthOrchestrator

def print_banner(title):
    print("\n" + "="*80)
    print(f"  TEST SCENARIO: {title}")
    print("="*80)

def initialize_claim_in_db(claim_id, patient_id, drug_name, policy_id, payer_id="PAYER-AETNA", payer_type="COMMERCIAL"):
    """Seeds a test claim in the SQLite claims tables."""
    claim_repo = ClaimRepository()
    diagnosis = {"code": "166110001" if "repatha" in policy_id.lower() else "44054006", "description": "Hyperlipidemia (disorder)" if "repatha" in policy_id.lower() else "Diabetes mellitus type 2 (disorder)"}
    service = {"procedure_code": "J3490" if "repatha" in policy_id.lower() else "J1817", "procedure_name": drug_name}
    
    # 1. Create base claim record
    claim_repo.create_claim(
        claim_id=claim_id,
        patient_id=patient_id,
        provider_id="HOSP-CTS-HACK",
        payer_id=payer_id,
        payer_type=payer_type,
        policy_id=policy_id,
        status="RECEIVED"
    )
    
    # 2. Create version 1 record
    claim = claim_repo.get_claim(claim_id)
    canonical_claim_dict = {
        "claim_id": claim_id,
        "claim_version": 1,
        "patient_id": patient_id,
        "provider_id": "HOSP-CTS-HACK",
        "payer_id": payer_id,
        "payer_type": payer_type,
        "policy_id": policy_id,
        "diagnosis": diagnosis,
        "requested_service": service,
        "clinical_summary": f"Prior authorization request for {drug_name}.",
        "supporting_document_ids": [],
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    claim_repo.create_claim_version(
        claim_id=claim_id,
        version=1,
        canonical_claim_json=json.dumps(canonical_claim_dict),
        status="RECEIVED"
    )
    print(f"Initialized claim '{claim_id}' (V1) for patient '{patient_id}' in the database.")


def run_test_suite():
    orchestrator = PriorAuthOrchestrator()
    claim_repo = ClaimRepository()
    audit_repo = AuditRepository()
    
    # Verify Gemini API key is present
    # Try to import from config with fallback
    try:
        from config import GEMINI_API_KEY
    except ImportError:
        import os
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    if not GEMINI_API_KEY:
        print("\n[WARNING] GEMINI_API_KEY is not set in environment or .env! LLM mapping calls will fail.")
        sys.exit(1)

    print("\nStarting Agent 2 Prior Authorization Orchestrator Integration Test Suite...\n")

    # -------------------------------------------------------------------------
    # Scenario A: Approved Flow
    # -------------------------------------------------------------------------
    print_banner("Scenario A - APPROVED (Repatha)")
    claim_id_a = "CLAIM-A-APPROVED"
    initialize_claim_in_db(claim_id_a, "TEST-PATIENT-A", "Evolocumab (Repatha)", "repatha")
    
    result_a = orchestrator.process_claim(claim_id_a)
    
    print("\n--- RESULTS FOR SCENARIO A ---")
    print(f"Final Status:     {result_a.status}")
    print(f"Claim Version:    {result_a.version}")
    print(f"Human Escalated:  {result_a.human_review_required}")
    print(f"Evidence Count:   {len(result_a.supporting_evidence)}")
    assert result_a.status == "APPROVED", "Scenario A should be APPROVED!"
    assert result_a.version == 1, "Scenario A should be approved in version 1!"
    print("Scenario A PASSED!")

    # -------------------------------------------------------------------------
    # Scenario B: More Info Recovery Flow
    # -------------------------------------------------------------------------
    print_banner("Scenario B - MORE_INFO Recovery (Repatha)")
    claim_id_b = "CLAIM-B-MOREINFO"
    initialize_claim_in_db(claim_id_b, "TEST-PATIENT-B", "Evolocumab (Repatha)", "repatha")
    
    result_b = orchestrator.process_claim(claim_id_b, scenario_mode="Scenario_B")
    
    print("\n--- RESULTS FOR SCENARIO B ---")
    print(f"Final Status:     {result_b.status}")
    print(f"Claim Version:    {result_b.version}")
    print(f"Human Escalated:  {result_b.human_review_required}")
    print(f"Evidence Count:   {len(result_b.supporting_evidence)}")
    
    # Check submissions history
    submissions = claim_repo.get_submissions_for_claim(claim_id_b)
    print("Submission History:")
    for sub in reversed(submissions):
        resp = json.loads(sub["payer_response_json"]) if sub["payer_response_json"] else {}
        print(f"  - Version {sub['claim_version']} | Submitted At: {sub['submitted_at']} | Status: {sub['status']} | Payer Reason: {resp.get('reason')}")
        
    assert result_b.status == "APPROVED", "Scenario B should end in APPROVED!"
    assert result_b.version == 2, "Scenario B should be approved in version 2 after recovery!"
    print("Scenario B PASSED!")

    # -------------------------------------------------------------------------
    # Scenario C: Rejection Recovery Flow
    # -------------------------------------------------------------------------
    print_banner("Scenario C - REJECTED Recovery (Repatha)")
    claim_id_c = "CLAIM-C-REJECTED"
    initialize_claim_in_db(claim_id_c, "TEST-PATIENT-C", "Evolocumab (Repatha)", "repatha")
    
    result_c = orchestrator.process_claim(claim_id_c, scenario_mode="Scenario_C")
    
    print("\n--- RESULTS FOR SCENARIO C ---")
    print(f"Final Status:     {result_c.status}")
    print(f"Claim Version:    {result_c.version}")
    print(f"Human Escalated:  {result_c.human_review_required}")
    print(f"Evidence Count:   {len(result_c.supporting_evidence)}")
    
    submissions_c = claim_repo.get_submissions_for_claim(claim_id_c)
    print("Submission History:")
    for sub in reversed(submissions_c):
        resp = json.loads(sub["payer_response_json"]) if sub["payer_response_json"] else {}
        print(f"  - Version {sub['claim_version']} | Submitted At: {sub['submitted_at']} | Status: {sub['status']} | Payer Reason: {resp.get('reason')}")
        
    assert result_c.status == "APPROVED", "Scenario C should end in APPROVED!"
    assert result_c.version == 2, "Scenario C should be approved in version 2 after recovery!"
    print("Scenario C PASSED!")

    # -------------------------------------------------------------------------
    # Scenario D: Genuinely Missing Evidence Flow
    # -------------------------------------------------------------------------
    print_banner("Scenario D - Genuinely MISSING (Humulin)")
    claim_id_d = "CLAIM-D-MISSING"
    initialize_claim_in_db(claim_id_d, "TEST-PATIENT-D", "Humulin (Insulin)", "humulin")
    
    result_d = orchestrator.process_claim(claim_id_d)
    
    print("\n--- RESULTS FOR SCENARIO D ---")
    print(f"Final Status:     {result_d.status}")
    print(f"Human Escalated:  {result_d.human_review_required}")
    print(f"Missing Info:     {result_d.missing_information}")
    
    # Check human review database entries
    reviews = claim_repo.get_human_reviews(claim_id_d)
    if reviews:
        print(f"Logged Human Review: Reason: {reviews[0]['reason']} | Action Recommended: {reviews[0]['recommended_action']}")
        
    assert result_d.status == "HUMAN_REVIEW", "Scenario D should escalate to HUMAN_REVIEW!"
    assert result_d.human_review_required is True, "Scenario D should set human_review_required to True!"
    print("Scenario D PASSED!")

    # -------------------------------------------------------------------------
    # Scenario E: Ambiguous/Uncertain Evidence Flow
    # -------------------------------------------------------------------------
    print_banner("Scenario E - UNCERTAIN / Short Statin Trial (Repatha)")
    claim_id_e = "CLAIM-E-UNCERTAIN"
    initialize_claim_in_db(claim_id_e, "TEST-PATIENT-E", "Evolocumab (Repatha)", "repatha")
    
    result_e = orchestrator.process_claim(claim_id_e)
    
    print("\n--- RESULTS FOR SCENARIO E ---")
    print(f"Final Status:     {result_e.status}")
    print(f"Human Escalated:  {result_e.human_review_required}")
    print(f"Reason:           {result_e.missing_information}")
    
    reviews_e = claim_repo.get_human_reviews(claim_id_e)
    if reviews_e:
        print(f"Logged Human Review: Reason: {reviews_e[0]['reason']} | Action Recommended: {reviews_e[0]['recommended_action']}")
        
    assert result_e.status == "HUMAN_REVIEW", "Scenario E should escalate to HUMAN_REVIEW!"
    assert result_e.human_review_required is True, "Scenario E should set human_review_required to True!"
    print("Scenario E PASSED!")

    # Print overall Audit log transition summary for CLAIM-B-MOREINFO to demonstrate the visual timeline
    print("\n" + "="*80)
    print("  VISUAL TIMELINE AUDIT TRAIL (CLAIM-B-MOREINFO)")
    print("="*80)
    audit_trail = audit_repo.get_audit_trail(claim_id_b)
    for entry in audit_trail:
        print(f"[{entry['timestamp']}] {entry['state_before']:22} -> {entry['state_after']:22} | Action: {entry['action']}")
        if entry["error"]:
            print(f"    ERROR: {entry['error']}")

    print("\nALL SCENARIOS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test_suite()
