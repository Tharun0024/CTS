"""
Runtime Adapter Module: Converts Simulation SQLite Records into CanonicalClaim and Payer Decision Context
"""
import sqlite3
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from simulation.scenarios import ClinicalScenario
from simulation.evidence import EvidenceRecord


@dataclass
class CanonicalClaim:
    claim_id: str
    patient_id: str
    payer_id: str
    plan_id: str
    requested_procedures: List[str]
    submitted_evidence: List[Dict[str, Any]]
    submission_date: str


@dataclass
class PayerDecisionContext:
    member_id: str
    patient_id: str
    payer_id: str
    plan_id: str
    policy_id: Optional[str]
    is_eligible: bool
    active_prior_auths: List[str] = field(default_factory=list)
    benefit_summary: Dict[str, Any] = field(default_factory=dict)


def build_canonical_claim_from_sqlite(db_path: str, claim_id: str) -> CanonicalClaim:
    """
    Constructs CanonicalClaim by directly querying SQLite big_patient_data.db records.
    Selects current claim request and currently submitted evidence for the claim.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query Claim Record
    cursor.execute("SELECT claim_id, patient_id, payer_id, plan_id, requested_procedure, created_at FROM claims WHERE claim_id = ?", (claim_id,))
    claim_row = cursor.fetchone()
    if not claim_row:
        conn.close()
        raise ValueError(f"Claim ID '{claim_id}' not found in SQLite database.")
    
    cid, pid, payer_id, plan_id, req_proc, created_at = claim_row
    cpt_list = [c.strip() for c in req_proc.split(",")]

    # Query latest submission to get submitted_evidence_ids
    cursor.execute("SELECT submitted_evidence_ids, submission_date FROM claim_submissions WHERE claim_id = ? ORDER BY attempt_number DESC LIMIT 1", (claim_id,))
    sub_row = cursor.fetchone()
    
    submitted_ev_dicts = []
    sub_date = created_at
    if sub_row:
        ev_ids_str, sub_date = sub_row
        ev_ids = [e.strip() for e in ev_ids_str.split(",") if e.strip()]
        if ev_ids:
            placeholders = ",".join(["?"] * len(ev_ids))
            cursor.execute(f"SELECT evidence_id, evidence_type, event_date, content_reference, provenance FROM evidence WHERE evidence_id IN ({placeholders})", ev_ids)
            for erow in cursor.fetchall():
                submitted_ev_dicts.append({
                    "evidence_id": erow[0],
                    "evidence_type": erow[1],
                    "event_date": erow[2],
                    "content_reference": erow[3],
                    "provenance": erow[4]
                })

    conn.close()

    return CanonicalClaim(
        claim_id=cid,
        patient_id=pid,
        payer_id=payer_id,
        plan_id=plan_id,
        requested_procedures=cpt_list,
        submitted_evidence=submitted_ev_dicts,
        submission_date=sub_date
    )


def build_payer_decision_context_from_sqlite(db_path: str, member_id: str, policy_id: Optional[str] = None) -> PayerDecisionContext:
    """
    Constructs PayerDecisionContext by directly querying SQLite payer_data.db records.
    Agent 1 receives this structured object; Agent 1 does NOT execute direct SQLite queries.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT member_id, patient_id, payer_id, plan_id, coverage_status FROM members WHERE member_id = ?", (member_id,))
    member_row = cursor.fetchone()
    if not member_row:
        conn.close()
        # Return fallback ineligible context for unlinked member (Scenario 5)
        return PayerDecisionContext(
            member_id=member_id,
            patient_id=member_id.replace("MEM_MISMATCH_", ""),
            payer_id="UNKNOWN_PAYER",
            plan_id="UNKNOWN_PLAN",
            policy_id=policy_id,
            is_eligible=False
        )

    mem_id, pid, payer_id, plan_id, status = member_row
    
    # Query eligibility
    cursor.execute("SELECT is_eligible FROM eligibility WHERE member_id = ?", (mem_id,))
    elig_row = cursor.fetchone()
    is_eligible = bool(elig_row[0]) if elig_row else (status == "ACTIVE")

    # Query active prior authorizations
    cursor.execute("SELECT authorization_id FROM prior_authorizations WHERE member_id = ? AND authorization_status = 'ACTIVE'", (mem_id,))
    auths = [r[0] for r in cursor.fetchall()]

    conn.close()

    return PayerDecisionContext(
        member_id=mem_id,
        patient_id=pid,
        payer_id=payer_id,
        plan_id=plan_id,
        policy_id=policy_id,
        is_eligible=is_eligible,
        active_prior_auths=auths,
        benefit_summary={"preauth_required": True, "copay": 50.0}
    )


def build_canonical_claim(scenario: ClinicalScenario, claim_id: Optional[str] = None) -> CanonicalClaim:
    """In-memory convenience wrapper."""
    cid = claim_id or f"CLM_{scenario.patient_id}"
    evidence_dicts = [
        {
            "evidence_id": e.evidence_id,
            "evidence_type": e.evidence_type,
            "event_date": e.event_date,
            "content_reference": e.content_reference,
            "provenance": e.provenance
        }
        for e in scenario.submitted_evidence
    ]
    
    return CanonicalClaim(
        claim_id=cid,
        patient_id=scenario.patient_id,
        payer_id=scenario.payer_linkage.payer_id,
        plan_id=scenario.payer_linkage.plan_id,
        requested_procedures=scenario.cpt_codes,
        submitted_evidence=evidence_dicts,
        submission_date="2026-07-01T09:00:00"
    )


def build_payer_decision_context(scenario: ClinicalScenario) -> PayerDecisionContext:
    """In-memory convenience wrapper."""
    is_eligible = not scenario.payer_linkage.is_mismatch_scenario and scenario.payer_linkage.payer_id != "UNKNOWN_PAYER_INC"
    return PayerDecisionContext(
        member_id=scenario.payer_linkage.member_id,
        patient_id=scenario.patient_id,
        payer_id=scenario.payer_linkage.payer_id,
        plan_id=scenario.payer_linkage.plan_id,
        policy_id=scenario.payer_linkage.policy_id,
        is_eligible=is_eligible,
        active_prior_auths=[],
        benefit_summary={"preauth_required": True, "copay": 50.0}
    )
