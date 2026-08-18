"""Workflow control plane for Agent 2 (Phase 4).

Defines and enforces the legal claim lifecycle states and transitions for the
Agent 2 side of the prior authorization workflow, keeps claim / version /
submission / evidence-request state consistent, and records an immutable,
append-only audit event for every important state/action transition.

Frozen V1 routing is encoded structurally here:
  - REQUEST_MORE_INFORMATION is the ONLY outcome that may route into recovery
    (EVALUATING -> ROUTED_RECOVERY).
  - REJECT and APPROVE are terminal states with NO outgoing transitions.
  - HUMAN_REVIEW is a hold state: Agent 2 can NEVER enter recovery directly
    from it. The only way out is a human resolution (HUMAN_REVIEW ->
    RESOLVED_REENTRY -> RECEIVED), which re-enters NORMAL Agent 1 routing --
    never a recovery shortcut.

Provider accept/decline decisions on recovered evidence are first-class
persisted events (in-memory always; SQLite when persistence is enabled).
Correlation IDs and evidence_request_id are carried through every event so
the full workflow remains traceable end-to-end.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ClaimWorkflowState(str, Enum):
    """Legal claim lifecycle states on the Agent 2 control plane."""

    INIT = "INIT"
    RECEIVED = "RECEIVED"
    EVALUATING = "EVALUATING"                     # Agent 1 decision run (any version)
    ROUTED_RECOVERY = "ROUTED_RECOVERY"           # RMI routed to Agent 2
    RECOVERING = "RECOVERING"                     # EvidenceRequest retrieval (FOUND/MISSING)
    AWAITING_PROVIDER_DECISION = "AWAITING_PROVIDER_DECISION"
    RESUBMITTING = "RESUBMITTING"                 # building immutable V(n+1)
    APPROVED = "APPROVED"                         # terminal
    REJECTED = "REJECTED"                         # terminal (every REJECT is terminal)
    HUMAN_REVIEW = "HUMAN_REVIEW"                 # hold: human resolution required
    RESOLVED_REENTRY = "RESOLVED_REENTRY"         # human resolution -> normal routing
    FAILED = "FAILED"                             # terminal system failure


# States from which no further transition is ever legal.
TERMINAL_STATES: Set[ClaimWorkflowState] = {
    ClaimWorkflowState.APPROVED,
    ClaimWorkflowState.REJECTED,
    ClaimWorkflowState.FAILED,
}

# The ONLY legal transitions. Anything not listed here is illegal and raises.
# Note deliberately absent:
#   * HUMAN_REVIEW -> ROUTED_RECOVERY / RECOVERING / RESUBMITTING
#     (Agent 2 must never directly enter recovery from HUMAN_REVIEW)
#   * any outgoing transition from APPROVED / REJECTED / FAILED
LEGAL_TRANSITIONS: Dict[ClaimWorkflowState, Set[ClaimWorkflowState]] = {
    ClaimWorkflowState.INIT: {ClaimWorkflowState.RECEIVED},
    ClaimWorkflowState.RECEIVED: {
        ClaimWorkflowState.EVALUATING,
        ClaimWorkflowState.FAILED,
    },
    ClaimWorkflowState.EVALUATING: {
        ClaimWorkflowState.APPROVED,                     # terminal approval
        ClaimWorkflowState.REJECTED,                     # terminal denial (any REJECT)
        ClaimWorkflowState.HUMAN_REVIEW,                 # Agent 1 escalation
        ClaimWorkflowState.ROUTED_RECOVERY,              # RMI -> Agent 2 (only recoverable route)
        ClaimWorkflowState.FAILED,
    },
    ClaimWorkflowState.ROUTED_RECOVERY: {
        ClaimWorkflowState.RECOVERING,
        ClaimWorkflowState.REJECTED,                     # administrative terminal block
        ClaimWorkflowState.HUMAN_REVIEW,                 # resubmission cap reached
    },
    ClaimWorkflowState.RECOVERING: {
        ClaimWorkflowState.AWAITING_PROVIDER_DECISION,   # FOUND candidates -> provider consent
        ClaimWorkflowState.HUMAN_REVIEW,                 # all MISSING / sensitive blocked
    },
    ClaimWorkflowState.AWAITING_PROVIDER_DECISION: {
        ClaimWorkflowState.RESUBMITTING,                 # provider ACCEPT
        ClaimWorkflowState.HUMAN_REVIEW,                 # provider DECLINE
    },
    ClaimWorkflowState.RESUBMITTING: {
        ClaimWorkflowState.EVALUATING,                   # V(n+1) re-decided by Agent 1
    },
    ClaimWorkflowState.HUMAN_REVIEW: {
        ClaimWorkflowState.RESOLVED_REENTRY,             # human resolution ONLY
    },
    ClaimWorkflowState.RESOLVED_REENTRY: {
        ClaimWorkflowState.RECEIVED,                     # re-enter NORMAL Agent 1 routing
    },
    ClaimWorkflowState.FAILED: set(),
    ClaimWorkflowState.APPROVED: set(),
    ClaimWorkflowState.REJECTED: set(),
}

# Provider consent decisions on recovered evidence.
PROVIDER_DECISION_ACCEPT = "ACCEPT"
PROVIDER_DECISION_DECLINE = "DECLINE"
_LEGAL_PROVIDER_DECISIONS = {PROVIDER_DECISION_ACCEPT, PROVIDER_DECISION_DECLINE}


class IllegalWorkflowTransition(Exception):
    """Raised when a lifecycle transition violates the frozen state machine."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class WorkflowEvent:
    """One immutable audit event for a state/action transition.

    Frozen by construction: once recorded, an event can never be altered.
    Carries correlation_id / evidence_request_id so the event is traceable
    across the EvidenceRequest boundary.
    """

    seq: int
    claim_id: str
    claim_version: int
    state_before: str
    state_after: str
    action: str
    correlation_id: Optional[str] = None
    evidence_request_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class ProviderDecisionRecord:
    """One persisted provider accept/decline decision on recovered evidence."""

    decision_id: str
    claim_id: str
    claim_version: int
    decision: str                                   # ACCEPT | DECLINE
    evidence_ids: Tuple[str, ...] = ()
    evidence_request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    reason: Optional[str] = None
    decided_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class PriorAuthPrecheckRecord:
    """Phase 1: deterministic prior-auth pre-check outcome for one claim run.

    Recorded on the control plane BEFORE Agent 1 evaluation. It never alters
    the frozen lifecycle states/transitions: it is an explicit, immutable,
    explainable representation of whether the claim/procedure requires prior
    authorization (requires_prior_auth, matched_rule, reason,
    policy_reference, source).
    """

    precheck_id: str
    claim_id: str
    claim_version: int
    requires_prior_auth: bool
    matched_rule: str
    reason: str
    policy_reference: Optional[str] = None
    source: Optional[str] = None
    recorded_at: str = field(default_factory=_utc_now_iso)


class WorkflowControlPlane:
    """Enforces legal state transitions and records immutable audit events.

    The control plane is the single source of truth for a claim's workflow
    state. Every transition is validated against LEGAL_TRANSITIONS and
    appended to an audit trail that is never mutated after recording.

    With ``persist_db=True`` every event and provider decision is also
    persisted to the agent2 SQLite database (agent2_audit /
    provider_decisions tables).
    """

    def __init__(self, persist_db: bool = False):
        self._persist_db = persist_db
        self._states: Dict[str, ClaimWorkflowState] = {}
        self._versions: Dict[str, int] = {}
        self._events: List[WorkflowEvent] = []      # append-only
        self._provider_decisions: List[ProviderDecisionRecord] = []  # append-only
        self._prior_auth_prechecks: List[PriorAuthPrecheckRecord] = []  # append-only

    # -- state access ------------------------------------------------------

    def current_state(self, claim_id: str) -> ClaimWorkflowState:
        """Current lifecycle state; a never-seen claim starts in INIT."""
        if claim_id in self._states:
            return self._states[claim_id]
        if self._persist_db:
            from ..database.repositories.audit_repository import AuditRepository
            trail = AuditRepository().get_audit_trail(claim_id)
            if trail:
                state_str = trail[-1]["state_after"]
                try:
                    return ClaimWorkflowState(state_str)
                except ValueError:
                    return ClaimWorkflowState.INIT
        return ClaimWorkflowState.INIT

    def current_version(self, claim_id: str) -> int:
        if claim_id in self._versions:
            return self._versions[claim_id]
        if self._persist_db:
            from ..database.repositories.audit_repository import AuditRepository
            trail = AuditRepository().get_audit_trail(claim_id)
            if trail:
                return trail[-1]["claim_version"] or 1
        return 1

    # -- transitions -------------------------------------------------------

    def transition(
        self,
        claim_id: str,
        to_state: ClaimWorkflowState,
        action: str,
        claim_version: Optional[int] = None,
        correlation_id: Optional[str] = None,
        evidence_request_id: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> WorkflowEvent:
        """Validate and record one state transition.

        Raises IllegalWorkflowTransition when the transition violates the
        frozen state machine (including any attempt to enter recovery from
        HUMAN_REVIEW or to leave a terminal state).
        """
        from_state = self.current_state(claim_id)
        allowed = LEGAL_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise IllegalWorkflowTransition(
                f"Illegal workflow transition for claim '{claim_id}': "
                f"{from_state.value} -> {to_state.value} (action='{action}'). "
                "Frozen routing: only REQUEST_MORE_INFORMATION routes to Agent 2 "
                "recovery; REJECT/APPROVE are terminal; HUMAN_REVIEW can only be "
                "left via human resolution re-entering normal Agent 1 routing."
            )

        if claim_version is None:
            claim_version = self._versions.get(claim_id, 1)
        event = WorkflowEvent(
            seq=len(self._events) + 1,
            claim_id=claim_id,
            claim_version=claim_version,
            state_before=from_state.value,
            state_after=to_state.value,
            action=action,
            correlation_id=correlation_id,
            evidence_request_id=evidence_request_id,
            detail=detail,
        )
        self._states[claim_id] = to_state
        self._versions[claim_id] = claim_version
        self._events.append(event)
        self._persist_event(event)
        return event

    def resolve_human_review(
        self,
        claim_id: str,
        resolution_note: str = "",
        correlation_id: Optional[str] = None,
    ) -> WorkflowEvent:
        """Human resolution of a HUMAN_REVIEW hold.

        This is the ONLY way out of HUMAN_REVIEW. It never resumes recovery
        directly: the claim re-enters normal Agent 1 routing afterwards.
        """
        state = self.current_state(claim_id)
        if state != ClaimWorkflowState.HUMAN_REVIEW:
            raise IllegalWorkflowTransition(
                f"Claim '{claim_id}' is not in HUMAN_REVIEW (current: {state.value}); "
                "nothing to resolve."
            )
        return self.transition(
            claim_id,
            ClaimWorkflowState.RESOLVED_REENTRY,
            "Human resolution recorded; re-entering normal Agent 1 routing",
            correlation_id=correlation_id,
            detail=resolution_note or None,
        )

    # -- Phase 1 prior-auth pre-check ----------------------------------------

    def record_prior_auth_precheck(
        self,
        claim_id: str,
        precheck: Any,
        claim_version: Optional[int] = None,
    ) -> PriorAuthPrecheckRecord:
        """Record the deterministic prior-auth pre-check outcome (Phase 1).

        Legal ONLY while the claim is in RECEIVED, i.e. before Agent 1
        evaluation starts (including after HUMAN_REVIEW resolution re-entry,
        which returns the claim to RECEIVED). The record is explicit and
        immutable but introduces NO new lifecycle state and NO new
        transition, so the frozen state machine and the exact event trail are
        preserved unchanged.
        """
        state = self.current_state(claim_id)
        if state != ClaimWorkflowState.RECEIVED:
            raise IllegalWorkflowTransition(
                f"Illegal prior-auth pre-check recording for claim '{claim_id}': "
                f"current state is {state.value}; the pre-check may only be "
                "recorded in RECEIVED, before Agent 1 evaluation."
            )
        if claim_version is None:
            claim_version = self._versions.get(claim_id, 1)
        record = PriorAuthPrecheckRecord(
            precheck_id=f"PAPC-{uuid.uuid4().hex[:10].upper()}",
            claim_id=claim_id,
            claim_version=claim_version,
            requires_prior_auth=bool(getattr(precheck, "requires_prior_auth", False)),
            matched_rule=str(getattr(precheck, "matched_rule", "") or ""),
            reason=str(getattr(precheck, "reason", "") or ""),
            policy_reference=getattr(precheck, "policy_reference", None),
            source=getattr(precheck, "source", None),
        )
        self._prior_auth_prechecks.append(record)
        return record

    def prior_auth_precheck(self, claim_id: str) -> Optional[PriorAuthPrecheckRecord]:
        """Latest recorded prior-auth pre-check for the claim (None if none)."""
        for record in reversed(self._prior_auth_prechecks):
            if record.claim_id == claim_id:
                return record
        return None

    # -- provider consent ----------------------------------------------------

    def record_provider_decision(
        self,
        claim_id: str,
        decision: str,
        claim_version: int,
        evidence_ids: Optional[List[str]] = None,
        evidence_request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> ProviderDecisionRecord:
        """Persist the provider's ACCEPT/DECLINE decision on recovered evidence."""
        normalized = str(decision).strip().upper()
        if normalized not in _LEGAL_PROVIDER_DECISIONS:
            raise ValueError(
                f"Illegal provider decision '{decision}'; must be one of "
                f"{sorted(_LEGAL_PROVIDER_DECISIONS)}."
            )
        record = ProviderDecisionRecord(
            decision_id=f"PRV-{uuid.uuid4().hex[:10].upper()}",
            claim_id=claim_id,
            claim_version=claim_version,
            decision=normalized,
            evidence_ids=tuple(evidence_ids or ()),
            evidence_request_id=evidence_request_id,
            correlation_id=correlation_id,
            reason=reason,
        )
        self._provider_decisions.append(record)
        self._persist_provider_decision(record)
        return record

    # -- immutable views -----------------------------------------------------

    def events(self, claim_id: Optional[str] = None) -> Tuple[WorkflowEvent, ...]:
        """Append-only audit trail (tuple copy: callers can never mutate it)."""
        if claim_id is None:
            return tuple(self._events)
            
        if self._persist_db:
            from ..database.repositories.audit_repository import AuditRepository
            trail = AuditRepository().get_audit_trail(claim_id)
            events_list = []
            for i, row in enumerate(trail):
                action_str = row["action"] or ""
                erq_id = None
                detail = None
                
                if " [erq=" in action_str:
                    try:
                        erq_part = action_str.split(" [erq=")[1].split("]")[0]
                        erq_id = erq_part
                    except Exception:
                        pass
                
                if " | " in action_str:
                    try:
                        detail = action_str.split(" | ")[1]
                    except Exception:
                        pass
                        
                events_list.append(
                    WorkflowEvent(
                        seq=i + 1,
                        claim_id=row["claim_id"],
                        claim_version=row["claim_version"],
                        state_before=row["state_before"],
                        state_after=row["state_after"],
                        action=row["action"],
                        correlation_id=row["correlation_id"] or None,
                        evidence_request_id=erq_id,
                        detail=detail,
                        timestamp=row["timestamp"],
                    )
                )
            return tuple(events_list)
            
        return tuple(e for e in self._events if e.claim_id == claim_id)

    def provider_decisions(
        self, claim_id: Optional[str] = None
    ) -> Tuple[ProviderDecisionRecord, ...]:
        if claim_id is None:
            return tuple(self._provider_decisions)
            
        if self._persist_db:
            import json
            from ..database.repositories.workflow_repository import WorkflowRepository
            rows = WorkflowRepository().get_provider_decisions(claim_id)
            decisions_list = []
            for row in rows:
                ev_ids = []
                if row.get("evidence_ids"):
                    try:
                        ev_ids = json.loads(row["evidence_ids"])
                    except Exception:
                        pass
                decisions_list.append(
                    ProviderDecisionRecord(
                        decision_id=row["decision_id"],
                        claim_id=row["claim_id"],
                        claim_version=row["claim_version"],
                        decision=row["decision"],
                        evidence_ids=tuple(ev_ids),
                        evidence_request_id=row.get("evidence_request_id"),
                        correlation_id=row.get("correlation_id"),
                        reason=row.get("reason"),
                        decided_at=row["decided_at"],
                    )
                )
            return tuple(decisions_list)
            
        return tuple(r for r in self._provider_decisions if r.claim_id == claim_id)

    # -- persistence ---------------------------------------------------------

    def _persist_event(self, event: WorkflowEvent) -> None:
        if not self._persist_db:
            return
        from ..database.repositories.audit_repository import AuditRepository

        AuditRepository().log_audit(
            audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            correlation_id=event.correlation_id or "",
            claim_id=event.claim_id,
            claim_version=event.claim_version,
            state_before=event.state_before,
            state_after=event.state_after,
            action=(
                event.action
                + (f" [erq={event.evidence_request_id}]" if event.evidence_request_id else "")
                + (f" | {event.detail}" if event.detail else "")
            ),
        )

    def _persist_provider_decision(self, record: ProviderDecisionRecord) -> None:
        if not self._persist_db:
            return
        from ..database.repositories.workflow_repository import WorkflowRepository

        WorkflowRepository().record_provider_decision(
            decision_id=record.decision_id,
            claim_id=record.claim_id,
            claim_version=record.claim_version,
            decision=record.decision,
            evidence_ids=list(record.evidence_ids),
            evidence_request_id=record.evidence_request_id,
            correlation_id=record.correlation_id,
            reason=record.reason,
            decided_at=record.decided_at,
        )
