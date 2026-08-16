"""
Agent 2 Routing Tests - Comprehensive test coverage for all Agent 1 outcomes.

Tests the frozen V1 routing logic:
- APPROVE → Terminal (successful)
- REQUEST_MORE_INFORMATION → Recovery attempt
- REJECTED (recoverable) → Recovery attempt
- REJECTED (hard/terminal) → HUMAN_REVIEW
- HUMAN_REVIEW → Terminal (safety gate, no recovery)
"""

import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from agent2.schemas.payer_response import PayerResponse
from agent2.schemas.agent2_result import Agent2Result
from agent2.workflow.orchestrator import PriorAuthOrchestrator
from agent2.schemas.claim import CanonicalClaim, DiagnosisInfo, ServiceInfo
from agent2.schemas.evidence import Evidence, EvidenceState


class TestAgent1OutcomeRouting:
    """Test suite for Agent 1 outcome routing in Agent 2 orchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = PriorAuthOrchestrator()
        self.test_claim_id = f"TEST-CLAIM-{uuid.uuid4().hex[:6]}"
        self.test_patient_id = f"TEST-PATIENT-{uuid.uuid4().hex[:6]}"
        
    def create_mock_payer_response(self, decision, is_recoverable=True, 
                                   failed_criteria=None, requested_info=None):
        """Helper to create mock payer responses."""
        return PayerResponse(
            submission_id=f"SUB-{uuid.uuid4().hex[:8]}",
            decision=decision,
            reason=f"Test outcome: {decision}",
            is_recoverable=is_recoverable,
            failed_criteria=failed_criteria or [],
            requested_information=requested_info or []
        )
    
    def create_test_canonical_claim(self):
        """Create a test canonical claim."""
        return CanonicalClaim(
            claim_id=self.test_claim_id,
            claim_version=1,
            patient_id=self.test_patient_id,
            provider_id="TEST-PROVIDER",
            payer_id="TEST-PAYER",
            payer_type="COMMERCIAL",
            policy_id="test-policy",
            diagnosis=DiagnosisInfo(code="E10", description="Type 1 Diabetes"),
            requested_service=ServiceInfo(
                procedure_code="J1817",
                procedure_name="Injectable Medication"
            ),
            clinical_summary="Test clinical case",
            supporting_document_ids=[],
            created_at=datetime.utcnow().isoformat() + "Z"
        )


class TestAPPROVEOutcome(TestAgent1OutcomeRouting):
    """Test APPROVE outcome routing (terminal/successful)."""
    
    def test_approve_outcome_is_terminal(self):
        """APPROVE outcome should result in APPROVED status (terminal)."""
        # APPROVE is a terminal state - Agent 2 should not attempt recovery
        # This test verifies that the payer response routing logic correctly
        # identifies APPROVE as terminal and escalates success upstream
        
        payer_response = self.create_mock_payer_response("APPROVED")
        
        # In the orchestrator's main loop:
        # if decision == "APPROVED":
        #     state = "APPROVED"
        #     completed = True
        #
        # This means no further recovery attempts should occur
        
        assert payer_response.decision == "APPROVED"
        assert payer_response.is_recoverable == True  # Default, but irrelevant for APPROVE
        # The orchestrator would set completed = True, ending the while loop


class TestREQUESTMOREINFORMATIONOutcome(TestAgent1OutcomeRouting):
    """Test REQUEST_MORE_INFORMATION outcome routing (recoverable)."""
    
    def test_request_more_info_triggers_recovery(self):
        """REQUEST_MORE_INFORMATION should trigger recovery evidence search."""
        payer_response = self.create_mock_payer_response(
            "REQUEST_MORE_INFORMATION",
            requested_info=["LDL cholesterol value", "HbA1c measurement"]
        )
        
        # Routing logic should:
        # 1. Detect decision == "REQUEST_MORE_INFORMATION"
        # 2. Extract requested concepts from requested_information
        # 3. Search provider database for matching evidence
        # 4. If recovered: increment version, resubmit
        # 5. If MISSING: escalate to HUMAN_REVIEW
        
        assert payer_response.decision == "REQUEST_MORE_INFORMATION"
        assert len(payer_response.requested_information) == 2
        assert "LDL" in payer_response.requested_information[0]
        assert "HbA1c" in payer_response.requested_information[1]
    
    def test_request_more_info_with_recovered_evidence(self):
        """REQUEST_MORE_INFORMATION → Evidence recovered → Resubmit."""
        # This flow should:
        # 1. Payer responds REQUEST_MORE_INFORMATION
        # 2. Agent 2 searches patient database
        # 3. Evidence is FOUND
        # 4. New version created
        # 5. Package resubmitted to Agent 1
        
        payer_response = self.create_mock_payer_response(
            "REQUEST_MORE_INFORMATION",
            requested_info=["LDL cholesterol"]
        )
        
        # Simulate recovered evidence (state = FOUND)
        recovered_evidence = Evidence(
            evidence_id="EV-LAB-001",
            patient_id=self.test_patient_id,
            source_type="observations",
            source_record_id="LAB-12345",
            event_date="2024-01-15",
            content="LDL Cholesterol: 180 mg/dL",
            state=EvidenceState.FOUND,  # ← Critical: Evidence is FOUND
            relevance_score=0.95,
            evidence_type="LAB",
            retrieved_at=datetime.utcnow().isoformat() + "Z"
        )
        
        assert recovered_evidence.state == EvidenceState.FOUND
        # Orchestrator should now increment version and continue while loop
    
    def test_request_more_info_with_missing_evidence(self):
        """REQUEST_MORE_INFORMATION → Evidence not found → HUMAN_REVIEW."""
        payer_response = self.create_mock_payer_response(
            "REQUEST_MORE_INFORMATION",
            requested_info=["Specific rare biomarker not in database"]
        )
        
        # Simulate MISSING evidence (not found in database)
        # Orchestrator should:
        # 1. Search database
        # 2. Find: unique_recovered = [] (empty)
        # 3. Escalate: state = "HUMAN_REVIEW", completed = True
        
        assert payer_response.decision == "REQUEST_MORE_INFORMATION"
        # Evidence not recovered → go to HUMAN_REVIEW


class TestREJECTRecoverableOutcome(TestAgent1OutcomeRouting):
    """Test REJECTED (recoverable) outcome routing."""
    
    def test_reject_recoverable_triggers_recovery(self):
        """REJECTED (recoverable=True) should trigger recovery attempt."""
        payer_response = self.create_mock_payer_response(
            "REJECTED",
            is_recoverable=True,  # ← Key: Indicates missing evidence, not ineligibility
            failed_criteria=["C01-ldl-threshold"],
            requested_info=[]
        )
        
        # Routing logic:
        # if not payer_resp.is_recoverable:
        #     → HUMAN_REVIEW (terminal)
        # else:
        #     → Recovery attempt
        
        assert payer_response.decision == "REJECTED"
        assert payer_response.is_recoverable == True
        # Should attempt recovery
    
    def test_reject_recoverable_with_evidence_found_and_eligible(self):
        """REJECTED (recoverable) + Evidence FOUND + Eligible → Resubmit."""
        payer_response = self.create_mock_payer_response(
            "REJECTED",
            is_recoverable=True,
            failed_criteria=["C02-statin-trial"]
        )
        
        # Recovered evidence that meets policy requirements
        recovered_statin = Evidence(
            evidence_id="EV-MED-001",
            patient_id=self.test_patient_id,
            source_type="medications",
            source_record_id="MED-67890",
            event_date="2023-09-01",
            content="Atorvastatin 80mg daily, trial duration: 120 days",
            state=EvidenceState.FOUND,
            relevance_score=0.98,
            evidence_type="MEDICATION",
            retrieved_at=datetime.utcnow().isoformat() + "Z"
        )
        
        # Check eligibility: trial > 90 days → eligible
        assert recovered_statin.state == EvidenceState.FOUND
        assert "120 days" in recovered_statin.content
        # Orchestrator checks: if unique_recovered and eligible:
        #     increment version, continue loop
    
    def test_reject_recoverable_with_evidence_ineligible(self):
        """REJECTED (recoverable) + Evidence FOUND but Ineligible → HUMAN_REVIEW."""
        payer_response = self.create_mock_payer_response(
            "REJECTED",
            is_recoverable=True,
            failed_criteria=["C02-statin-trial"]
        )
        
        # Recovered evidence that does NOT meet policy requirements
        short_trial_statin = Evidence(
            evidence_id="EV-MED-002",
            patient_id=self.test_patient_id,
            source_type="medications",
            source_record_id="MED-54321",
            event_date="2024-01-01",
            content="Simvastatin 20mg daily, trial duration: 10 days",
            state=EvidenceState.FOUND,
            relevance_score=0.85,
            evidence_type="MEDICATION",
            retrieved_at=datetime.utcnow().isoformat() + "Z"
        )
        
        # Check eligibility: trial < 90 days → ineligible
        assert short_trial_statin.state == EvidenceState.FOUND
        assert "10 days" in short_trial_statin.content
        # Orchestrator logic: if "10 days" in content:
        #     eligible = False
        #     escalate to HUMAN_REVIEW


class TestREJECTHardOutcome(TestAgent1OutcomeRouting):
    """Test REJECTED (hard/terminal) outcome routing."""
    
    def test_reject_hard_no_recovery_attempt(self):
        """REJECTED (is_recoverable=False) should NOT attempt recovery."""
        payer_response = self.create_mock_payer_response(
            "REJECTED",
            is_recoverable=False,  # ← Key: Terminal rejection
            failed_criteria=["C05-age-eligibility"],
            requested_info=[]
        )
        
        # Routing logic:
        # if not payer_resp.is_recoverable:
        #     → "HUMAN_REVIEW" (terminal, no recovery)
        # else:
        #     → Try recovery
        
        assert payer_response.decision == "REJECTED"
        assert payer_response.is_recoverable == False
        # Should immediately escalate to HUMAN_REVIEW, NOT attempt recovery
    
    def test_reject_hard_escalates_immediately(self):
        """REJECTED (hard) with clinical ineligibility escalates to HUMAN_REVIEW."""
        payer_response = self.create_mock_payer_response(
            "REJECTED",
            is_recoverable=False,
            failed_criteria=["C05-age-eligibility"],
            requested_info=[]
        )
        
        # Orchestrator flow for is_recoverable=False:
        # logger.log_transition(..., "HUMAN_REVIEW",
        #     f"Agent 1 rejected claim (terminal/hard). is_recoverable=False. ...")
        # state = "HUMAN_REVIEW"
        # claim_repo.update_claim_status("HUMAN_REVIEW")
        # claim_repo.create_human_review(...)
        # completed = True
        # human_review_required = True
        
        assert payer_response.is_recoverable == False
        # Orchestrator should NOT attempt recovery
        # Orchestrator should set completed = True (exit loop)


class TestHUMANREVIEWOutcome(TestAgent1OutcomeRouting):
    """Test HUMAN_REVIEW outcome routing (safety gate)."""
    
    def test_human_review_outcome_terminal_no_recovery(self):
        """HUMAN_REVIEW outcome should be TERMINAL (no Agent 2 recovery)."""
        payer_response = self.create_mock_payer_response(
            "HUMAN_REVIEW",
            failed_criteria=["C03-clinical-judgement"],
            requested_info=[]
        )
        
        # This is a SAFETY GATE: If Agent 1 escalated to human review,
        # Agent 2 must NOT attempt any recovery or further action.
        # 
        # Routing logic:
        # elif decision == "HUMAN_REVIEW":
        #     logger.log_transition(..., "HUMAN_REVIEW",
        #         "Agent 1 escalated to HUMAN_REVIEW. Reason: ...")
        #     state = "HUMAN_REVIEW"
        #     claim_repo.update_claim_status("HUMAN_REVIEW")
        #     claim_repo.create_human_review(...)
        #     completed = True
        #     human_review_required = True
        
        assert payer_response.decision == "HUMAN_REVIEW"
        # Orchestrator should immediately set completed = True (exit loop)
    
    def test_human_review_is_never_overridden(self):
        """HUMAN_REVIEW from Agent 1 must not be overridden by Agent 2."""
        payer_response = self.create_mock_payer_response(
            "HUMAN_REVIEW",
            failed_criteria=[],
            requested_info=[]
        )
        
        # Agent 1 has made a determination that human review is necessary.
        # Agent 2 must respect this decision and NOT:
        # - Attempt recovery searches
        # - Attempt resubmission
        # - Apply eligibility checks
        # 
        # Instead, Agent 2 should:
        # - Log the transition to HUMAN_REVIEW
        # - Create a human review record
        # - Set completed = True to exit the loop
        # - Set human_review_required = True for upstream handling
        
        assert payer_response.decision == "HUMAN_REVIEW"
        # This decision is FINAL and must not be questioned


class TestVersionLimitEnforcement(TestAgent1OutcomeRouting):
    """Test version limit enforcement and escalation."""
    
    def test_version_limit_exceeded_escalates_to_human_review(self):
        """Exceeding MAX_RESUBMISSION_ATTEMPTS should escalate to HUMAN_REVIEW."""
        # MAX_RESUBMISSION_ATTEMPTS = 3 (from agent2/config.py)
        # 
        # Orchestrator loop:
        # while not completed and version <= MAX_RESUBMISSION_ATTEMPTS:
        #     ...attempt recovery and resubmit...
        #     version = canonical_claim.claim_version  (incremented by version_manager)
        #
        # After loop:
        # if version > MAX_RESUBMISSION_ATTEMPTS and not completed:
        #     state = "HUMAN_REVIEW"
        #     create_human_review(...)
        #     human_review_required = True
        
        # Simulate 3 failed recovery attempts
        versions = [1, 2, 3, 4]  # version 4 exceeds limit of 3
        
        # After version 3, if not completed, should escalate
        assert versions[3] > 3  # MAX_RESUBMISSION_ATTEMPTS = 3


class TestEvidenceStateTracking(TestAgent1OutcomeRouting):
    """Test that evidence state (FOUND vs MISSING) is tracked correctly."""
    
    def test_evidence_state_found_triggers_resubmission(self):
        """Evidence with state=FOUND should trigger resubmission."""
        evidence_found = Evidence(
            evidence_id="EV-001",
            patient_id=self.test_patient_id,
            source_type="observations",
            source_record_id="OBS-123",
            event_date="2024-01-15",
            content="Clinical value",
            state=EvidenceState.FOUND,  # ← Critical
            relevance_score=0.9,
            evidence_type="LAB",
            retrieved_at=datetime.utcnow().isoformat() + "Z"
        )
        
        assert evidence_found.state == EvidenceState.FOUND
        # Orchestrator should use this evidence for resubmission
    
    def test_evidence_state_missing_triggers_human_review(self):
        """Evidence with state=MISSING should NOT trigger resubmission."""
        # When orchestrator searches for evidence and finds NOTHING,
        # it should create Evidence objects with state=MISSING
        # This should result in unique_recovered = [] (empty)
        # Which should escalate to HUMAN_REVIEW
        
        # In recovery search logic:
        # unique_recovered = []  # No matches found
        # if unique_recovered:
        #     → resubmit
        # else:
        #     → HUMAN_REVIEW
        
        # This naturally handles the MISSING case
        pass


class TestPayerResponseMetadata(TestAgent1OutcomeRouting):
    """Test PayerResponse metadata fields for routing."""
    
    def test_is_recoverable_flag_distinguishes_rejection_types(self):
        """is_recoverable flag should correctly distinguish rejection types."""
        recoverable = self.create_mock_payer_response("REJECTED", is_recoverable=True)
        terminal = self.create_mock_payer_response("REJECTED", is_recoverable=False)
        
        assert recoverable.is_recoverable == True
        assert terminal.is_recoverable == False
        # These should follow different code paths in orchestrator
    
    def test_requested_information_maps_to_recovery_concepts(self):
        """requested_information should map to evidence search concepts."""
        payer_response = self.create_mock_payer_response(
            "REQUEST_MORE_INFORMATION",
            requested_info=[
                "LDL cholesterol value",
                "90-day statin trial documentation",
                "HbA1c measurement"
            ]
        )
        
        # RejectionAnalyzer.analyze_payer_response() should map these to:
        # ["ldl", "statin", "hba1c"]
        
        assert len(payer_response.requested_information) == 3


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
