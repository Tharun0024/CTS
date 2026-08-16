"""Phase 4 focused tests: workflow control plane.

Verifies:
  - legal/illegal lifecycle transitions (frozen state machine),
  - HUMAN_REVIEW lifecycle (never directly into recovery; human resolution
    re-enters NORMAL Agent 1 routing),
  - provider accept/decline persistence,
  - correlation_id / evidence_request_id propagation,
  - immutable append-only audit events,
  - terminal REJECT/APPROVE and RMI recovery through the real pipeline.

All tests run offline (RAG + LLM layers mocked); Agent1 semantics are
exercised unchanged via services.run_agent2_v1_pipeline.
"""
import dataclasses

import pytest

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from services.integrated_pipeline import (
    reenter_after_human_resolution,
    run_agent2_v1_pipeline,
)
from decision.schemas import DecisionOutcome
from agent2.workflow.control_plane import (
    LEGAL_TRANSITIONS,
    TERMINAL_STATES,
    ClaimWorkflowState,
    IllegalWorkflowTransition,
    WorkflowControlPlane,
)

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)


@pytest.fixture
def p4_registry(monkeypatch):
    """Structured rules for the Phase-4 policies."""
    entries = {
        ("POL-P4-FLAG", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-P4-MISS", "C-MET"): {
            "required_evidence_keys": ["metformin_trial"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P4-HARD", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


@pytest.fixture
def workflow_db(monkeypatch, tmp_path):
    """Isolated agent2 SQLite DB for workflow persistence assertions."""
    import agent2.database.db_manager as db_manager

    db_file = tmp_path / "workflow_p4.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_file))
    db_manager.init_db()
    return db_file


def _states_after(cp, claim_id):
    return [event.state_after for event in cp.events(claim_id)]


# ---------------------------------------------------------------------------
# State machine: legal and illegal transitions
# ---------------------------------------------------------------------------

class TestStateMachineLegality:
    def test_full_legal_recovery_path(self):
        cp = WorkflowControlPlane()
        path = [
            ClaimWorkflowState.RECEIVED,
            ClaimWorkflowState.EVALUATING,
            ClaimWorkflowState.ROUTED_RECOVERY,
            ClaimWorkflowState.RECOVERING,
            ClaimWorkflowState.AWAITING_PROVIDER_DECISION,
            ClaimWorkflowState.RESUBMITTING,
            ClaimWorkflowState.EVALUATING,
            ClaimWorkflowState.APPROVED,
        ]
        for state in path:
            cp.transition("CLM-SM", state, "legal path step")
        assert cp.current_state("CLM-SM") == ClaimWorkflowState.APPROVED
        assert len(cp.events("CLM-SM")) == len(path)

    @pytest.mark.parametrize("to_state", [
        ClaimWorkflowState.EVALUATING,
        ClaimWorkflowState.APPROVED,
        ClaimWorkflowState.RECOVERING,
        ClaimWorkflowState.HUMAN_REVIEW,
    ])
    def test_illegal_transitions_raise(self, to_state):
        cp = WorkflowControlPlane()
        with pytest.raises(IllegalWorkflowTransition):
            cp.transition("CLM-SM2", to_state, "illegal jump")
        # State must not have moved on a rejected transition.
        assert cp.current_state("CLM-SM2") == ClaimWorkflowState.INIT
        assert cp.events("CLM-SM2") == ()

    def test_human_review_can_never_enter_recovery_directly(self):
        cp = WorkflowControlPlane()
        cp.transition("CLM-HR", ClaimWorkflowState.RECEIVED, "received")
        cp.transition("CLM-HR", ClaimWorkflowState.EVALUATING, "evaluated")
        cp.transition("CLM-HR", ClaimWorkflowState.HUMAN_REVIEW, "escalated")
        for forbidden in (
            ClaimWorkflowState.ROUTED_RECOVERY,
            ClaimWorkflowState.RECOVERING,
            ClaimWorkflowState.RESUBMITTING,
            ClaimWorkflowState.EVALUATING,
        ):
            with pytest.raises(IllegalWorkflowTransition):
                cp.transition("CLM-HR", forbidden, "forbidden recovery shortcut")

    @pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES, key=lambda s: s.value))
    def test_terminal_states_have_no_outgoing_transitions(self, terminal):
        assert LEGAL_TRANSITIONS[terminal] == set()

    def test_human_review_only_exits_via_resolution(self):
        assert LEGAL_TRANSITIONS[ClaimWorkflowState.HUMAN_REVIEW] == {
            ClaimWorkflowState.RESOLVED_REENTRY
        }
        assert LEGAL_TRANSITIONS[ClaimWorkflowState.RESOLVED_REENTRY] == {
            ClaimWorkflowState.RECEIVED
        }

    def test_resolve_human_review_requires_human_review_state(self):
        cp = WorkflowControlPlane()
        with pytest.raises(IllegalWorkflowTransition):
            cp.resolve_human_review("CLM-NEVER-SEEN")
        cp.transition("CLM-OTHER", ClaimWorkflowState.RECEIVED, "received")
        with pytest.raises(IllegalWorkflowTransition):
            cp.resolve_human_review("CLM-OTHER")


# ---------------------------------------------------------------------------
# Pipeline integration: terminal and recoverable outcomes drive legal states
# ---------------------------------------------------------------------------

class TestPipelineLifecycleStates:
    def test_rmi_recovery_reaches_approved_with_legal_trail(self, p4_registry):
        chunks = [_chunk("POL-P4-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-FLAG", "POL-P4-FLAG")
        pool = [_ev("ldl_report", "EV-P4-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), control_plane=cp
        )

        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.control_plane is cp
        assert cp.current_state("CLM-P4-FLAG") == ClaimWorkflowState.APPROVED
        assert _states_after(cp, "CLM-P4-FLAG") == [
            "RECEIVED", "EVALUATING", "ROUTED_RECOVERY", "RECOVERING",
            "AWAITING_PROVIDER_DECISION", "RESUBMITTING", "EVALUATING", "APPROVED",
        ]
        # Version consistency: the resubmission events carry V2.
        re_eval = [e for e in cp.events("CLM-P4-FLAG") if e.action.startswith("Agent1 re-evaluating")]
        assert len(re_eval) == 1 and re_eval[0].claim_version == 2

    def test_terminal_reject_never_enters_recovery_states(self, p4_registry):
        chunks = [_chunk("POL-P4-HARD", "C01", "Diagnosis documentation required.")]
        exclusions = [{
            "exclusion_id": "EX-AGE",
            "name": "Age exclusion",
            "rule": {"field": "patient_age", "operator": "gte", "value": 80},
            "required_evidence_keys": [],
        }]
        components = _build_components(chunks, exclusions=exclusions)
        claim = _scenario_claim("CLM-P4-HARD", "POL-P4-HARD", age=85)

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )

        assert result.final_outcome == DecisionOutcome.REJECT
        assert cp.current_state("CLM-P4-HARD") == ClaimWorkflowState.REJECTED
        states = _states_after(cp, "CLM-P4-HARD")
        assert states == ["RECEIVED", "EVALUATING", "REJECTED"]
        # No recovery state was ever recorded for a terminal REJECT.
        assert not {"ROUTED_RECOVERY", "RECOVERING", "RESUBMITTING"} & set(states)

    def test_missing_evidence_ends_in_human_review_hold(self, p4_registry):
        chunks = [_chunk("POL-P4-MISS", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-MISS", "POL-P4-MISS")

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert cp.current_state("CLM-P4-MISS") == ClaimWorkflowState.HUMAN_REVIEW
        assert _states_after(cp, "CLM-P4-MISS") == [
            "RECEIVED", "EVALUATING", "ROUTED_RECOVERY", "RECOVERING", "HUMAN_REVIEW",
        ]


# ---------------------------------------------------------------------------
# HUMAN_REVIEW lifecycle: resolution re-enters NORMAL Agent 1 routing
# ---------------------------------------------------------------------------

class TestHumanReviewLifecycle:
    def test_resolution_reenters_normal_routing_and_approves(self, p4_registry):
        chunks = [_chunk("POL-P4-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-RE", "POL-P4-FLAG")

        cp = WorkflowControlPlane()
        # V1: RMI; provider pool is empty -> genuinely MISSING -> HUMAN_REVIEW.
        first = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )
        assert first.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert cp.current_state("CLM-P4-RE") == ClaimWorkflowState.HUMAN_REVIEW

        # Agent2 can never resume recovery directly from HUMAN_REVIEW.
        with pytest.raises(IllegalWorkflowTransition):
            cp.transition("CLM-P4-RE", ClaimWorkflowState.RECOVERING, "illegal shortcut")

        # Human resolution attaches a REAL provider record and re-enters the
        # normal Agent 1 routing (no recovery shortcut).
        human_record = _ev(
            "ldl_report", "EV-P4-HUMAN", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"}
        )
        second = reenter_after_human_resolution(
            claim, components, control_plane=cp,
            attached_evidence=[human_record],
            recovery_source=_pool_source([]),
            resolution_note="Human reviewer located the LDL report in the provider record.",
        )

        assert second.final_outcome == DecisionOutcome.APPROVE
        assert cp.current_state("CLM-P4-RE") == ClaimWorkflowState.APPROVED
        states = _states_after(cp, "CLM-P4-RE")
        # Resolution path: HUMAN_REVIEW -> RESOLVED_REENTRY -> RECEIVED -> normal routing.
        assert "RESOLVED_REENTRY" in states
        assert states[states.index("RESOLVED_REENTRY") + 1] == "RECEIVED"
        assert states[-1] == "APPROVED"
        # The human-attached record entered as a new append-only version.
        assert second.versions[0]["claim"]["evidence"][-1]["evidence_id"] == "EV-P4-HUMAN"
        # The original caller claim was never mutated.
        assert all(e["evidence_id"] == "EV-DX-1" for e in claim["evidence"])

    def test_resolution_without_evidence_reruns_normal_routing(self, p4_registry):
        chunks = [_chunk("POL-P4-MISS", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-RE2", "POL-P4-MISS")

        cp = WorkflowControlPlane()
        first = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )
        assert first.final_outcome == DecisionOutcome.HUMAN_REVIEW

        # No new evidence: the resolution simply re-enters normal routing and
        # Agent 1 deterministically repeats its frozen routing (RMI -> recovery
        # -> still MISSING -> HUMAN_REVIEW). No shortcut, no fabrication.
        second = reenter_after_human_resolution(
            claim, components, control_plane=cp,
            recovery_source=_pool_source([]),
            resolution_note="Re-review requested; no new records available.",
        )
        assert second.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert cp.current_state("CLM-P4-RE2") == ClaimWorkflowState.HUMAN_REVIEW

    def test_fabricated_human_attachment_is_rejected(self, p4_registry):
        chunks = [_chunk("POL-P4-MISS", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-FAB", "POL-P4-MISS")

        cp = WorkflowControlPlane()
        run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )
        with pytest.raises(ValueError):
            reenter_after_human_resolution(
                claim, components, control_plane=cp,
                attached_evidence=[{"evidence_key": "metformin_trial"}],  # no evidence_id
                recovery_source=_pool_source([]),
            )


# ---------------------------------------------------------------------------
# Provider accept/decline persistence
# ---------------------------------------------------------------------------

class TestProviderDecisionPersistence:
    def test_accept_and_decline_are_persisted(self, p4_registry, workflow_db):
        chunks = [_chunk("POL-P4-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        pool = [_ev("ldl_report", "EV-P4-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]

        # ACCEPT run.
        cp_accept = WorkflowControlPlane(persist_db=True)
        run_agent2_v1_pipeline(
            _scenario_claim("CLM-P4-ACC", "POL-P4-FLAG"), components,
            recovery_source=_pool_source(pool), control_plane=cp_accept,
        )
        # DECLINE run.
        cp_decline = WorkflowControlPlane(persist_db=True)
        result = run_agent2_v1_pipeline(
            _scenario_claim("CLM-P4-DEC", "POL-P4-FLAG"), components,
            recovery_source=_pool_source(pool), control_plane=cp_decline,
            provider_decision="DECLINE",
        )
        assert result.provider_declined is True

        from agent2.database.repositories.workflow_repository import WorkflowRepository

        repo = WorkflowRepository()
        accept_rows = repo.get_provider_decisions("CLM-P4-ACC")
        decline_rows = repo.get_provider_decisions("CLM-P4-DEC")
        assert [row["decision"] for row in accept_rows] == ["ACCEPT"]
        assert [row["decision"] for row in decline_rows] == ["DECLINE"]
        # Consent records carry the contract IDs and the real evidence.
        assert accept_rows[0]["evidence_ids"] == ["EV-P4-LDL"]
        assert accept_rows[0]["evidence_request_id"].startswith("ERQ-")
        assert accept_rows[0]["correlation_id"] == "CORR-CLM-P4-ACC-V1"
        # In-memory view matches persistence and is append-only.
        assert [r.decision for r in cp_decline.provider_decisions("CLM-P4-DEC")] == ["DECLINE"]

    def test_illegal_provider_decision_value_is_rejected(self):
        cp = WorkflowControlPlane()
        with pytest.raises(ValueError):
            cp.record_provider_decision("CLM-X", "MAYBE", claim_version=1)


# ---------------------------------------------------------------------------
# Correlation / request ID propagation
# ---------------------------------------------------------------------------

class TestCorrelationPropagation:
    def test_contract_ids_flow_through_events_and_submission(self, p4_registry):
        chunks = [_chunk("POL-P4-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-ID", "POL-P4-FLAG")
        pool = [_ev("ldl_report", "EV-P4-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), control_plane=cp
        )

        request = result.evidence_request
        assert request is not None
        # Every post-routing event carries the same correlation/request IDs.
        post_routing = [
            event for event in cp.events("CLM-P4-ID")
            if event.state_before in {
                "ROUTED_RECOVERY", "RECOVERING", "AWAITING_PROVIDER_DECISION", "RESUBMITTING",
            }
            or event.state_after in {"RECOVERING", "AWAITING_PROVIDER_DECISION", "RESUBMITTING"}
        ]
        assert post_routing
        for event in post_routing:
            assert event.correlation_id == request.correlation_id == "CORR-CLM-P4-ID-V1"
            assert event.evidence_request_id == request.evidence_request_id
        # The submission package propagates both IDs as well.
        submission = result.submissions[0]
        assert submission["correlation_id"] == request.correlation_id
        assert submission["evidence_request_id"] == request.evidence_request_id
        # The recovery result echoes the same identity.
        assert result.recovery_result.correlation_id == request.correlation_id
        assert result.recovery_result.evidence_request_id == request.evidence_request_id


# ---------------------------------------------------------------------------
# Audit events are immutable and append-only
# ---------------------------------------------------------------------------

class TestAuditImmutability:
    def test_events_are_frozen_and_append_only(self):
        cp = WorkflowControlPlane()
        cp.transition("CLM-AUD", ClaimWorkflowState.RECEIVED, "received")
        first = cp.events("CLM-AUD")[0]

        # Frozen: recorded events can never be altered.
        with pytest.raises(dataclasses.FrozenInstanceError):
            first.action = "tampered"

        cp.transition("CLM-AUD", ClaimWorkflowState.EVALUATING, "evaluated")
        events = cp.events("CLM-AUD")
        # Append-only: the earlier event is preserved exactly, seq is monotonic.
        assert events[0] == first
        assert [e.seq for e in events] == [1, 2]
        # Returned view is a copy: callers cannot mutate the internal trail.
        assert isinstance(events, tuple)

    def test_workflow_events_persist_to_audit_table(self, p4_registry, workflow_db):
        chunks = [_chunk("POL-P4-MISS", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P4-DBAUD", "POL-P4-MISS")

        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), persist_workflow_db=True
        )
        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW

        from agent2.database.repositories.audit_repository import AuditRepository

        rows = AuditRepository().get_audit_trail("CLM-P4-DBAUD")
        assert len(rows) >= 5
        recorded_states = [row["state_after"] for row in rows]
        assert recorded_states[0] == "RECEIVED"
        assert recorded_states[-1] == "HUMAN_REVIEW"
        # Recovery events persisted with the contract correlation ID.
        recovering = [row for row in rows if row["state_after"] == "RECOVERING"]
        assert recovering and recovering[0]["correlation_id"] == "CORR-CLM-P4-DBAUD-V1"
