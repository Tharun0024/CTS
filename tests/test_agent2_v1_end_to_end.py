"""End-to-end scenarios A-K for the real V1 pipeline with Agent 2 integrated.

Flow under test:
    Provider data -> CanonicalClaim -> RAG -> Agent 1 -> DecisionResponse
    -> routing -> Agent 2 (when appropriate) -> provider evidence recovery
    -> release gate -> SubmissionPackage -> Agent 1 again -> final outcome.

All tests run fully offline: RAG retrieval/reranking/embedding and both LLM
layers are mocked. Agent 1 decision semantics (decision/decision_logic.py) are
exercised unchanged; Agent 2 routing/recovery/release-gate/versioning from
services/integrated_pipeline.py is what these scenarios verify.
"""
import json
import pytest
from typing import Any, Dict, List, Optional

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from rag.aggregation.policy_aggregator import PolicyAggregator
from services.integrated_pipeline import (
    run_agent2_v1_pipeline,
    classify_decision_for_agent2,
)
from decision.schemas import DecisionOutcome
from decision.llm_provider import MockLLMProvider


# ---------------------------------------------------------------------------
# Fixture: scenario-specific structured rules (test-only registry entries)
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_registry(monkeypatch):
    entries = {
        ("POL-SCEN-B", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-SCEN-C", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
        ("POL-SCEN-D", "C-MET"): {
            "required_evidence_keys": ["metformin_trial"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-E", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
        ("POL-SCEN-F", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-G", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-H", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-I", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-J", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-K", "C-A"): {
            "required_evidence_keys": ["extra_doc_a"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-SCEN-K", "C-B"): {
            "required_evidence_keys": ["extra_doc_b"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ev(key, ev_id, facts=None, status="verified", confidence=0.96, ambiguous=False, sensitivity="ROUTINE"):
    extracted = dict(facts or {})
    extracted.setdefault("sensitivity", sensitivity)
    extracted.setdefault("provenance", f"PROV-DB:{ev_id}")
    return {
        "evidence_key": key,
        "evidence_id": ev_id,
        "source": "Clinical Information",
        "status": status,
        "confidence_score": confidence,
        "is_ambiguous": ambiguous,
        "extracted_facts": extracted,
        "unstructured_text": extracted.get("content_reference"),
    }


def _scenario_claim(
    claim_id,
    policy_id,
    payer="Aetna",
    evidence=None,
    metrics_extra=None,
    age=55,
    procedures=("27447",),
    diagnoses=("M17.11",),
):
    metrics = {
        "patient_gender": "Female",
        "claim_scenario_type": "COMPLETE",
        "claim_payer": payer,
        "claim_policy_id": policy_id,
    }
    metrics.update(metrics_extra or {})
    return {
        "claim_id": claim_id,
        "patient_id": "PA-TEST",
        "submission": {"attempt": 1, "date": "2026-08-16T00:00:00Z"},
        "case_data": {
            "case_id": claim_id,
            "patient_age": age,
            "diagnoses": list(diagnoses),
            "procedures": list(procedures),
            "clinical_metrics": metrics,
        },
        "evidence": [_ev("diagnosis", "EV-DX-1", {"verified_facts": True})] if evidence is None else evidence,
    }


def _chunk(policy_id, criterion_id, text, payer="Aetna", procedure="27447", name="Coverage Criterion"):
    return {
        "chunk_id": f"{policy_id}-{criterion_id}",
        "policy_id": policy_id,
        "payer": payer,
        "policy_title": "Scenario Policy",
        "clinical_domain": "orthopedics",
        "procedure_codes": [procedure],
        "diagnosis_codes": ["M17.11"],
        "section": "Coverage Criteria",
        "criterion_id": criterion_id,
        "criterion_type": "medical_necessity",
        "criterion_name": name,
        "text": text,
    }


def _response_gen(prompt, _system):
    """Mock criterion-assessment LLM: SUPPORTED only when candidates exist."""
    payload = json.loads(prompt)
    entries = payload.get("candidate_paths", [])
    if not entries:
        return json.dumps({
            "status": "MISSING",
            "selected_paths": [],
            "reason": ["Required evidence is not present in the canonical claim."],
        })
    selected = []
    for entry in entries:
        try:
            selected.append(int(str(entry).split(":", 1)[0]))
        except Exception:
            pass
    return json.dumps({
        "status": "SUPPORTED",
        "selected_paths": selected,
        "reason": ["Evidence is present and verified."],
    })


def _build_components(chunks: List[Dict[str, Any]], exclusions: Optional[List[Dict[str, Any]]] = None):
    from tests.test_rag_contract_adapter import GlobalMockRetriever
    from rag.query_builder.query_builder import QueryBuilder
    from rag.retrieval.candidate_pool import CandidatePool
    from rag.analyzer.deterministic_analyzer import DeterministicAnalyzer
    from rag.evidence.evidence_builder import EvidenceBuilder
    from rag.llm.prompt_builder import PromptBuilder
    from rag.validation.output_validator import OutputValidator

    all_chunks_dict = {c["chunk_id"]: c for c in chunks}

    class MockReranker:
        def rerank(self, query, candidates):
            for cand in candidates:
                cand["rerank_score"] = 0.95
            return candidates

    class MockLLMClient:
        def generate_claim_output(self, claim_id, policy_id, payer, relevance_score, evidence_object, prompt=""):
            criteria = []
            for item in evidence_object.get("criteria", []):
                criteria.append({
                    "criterion_id": item.get("criterion_id"),
                    "criterion": item.get("criterion"),
                    "policy_requirement": item.get("policy_requirement", ""),
                    "source": item.get("source") or {"policy_id": policy_id, "section": "Coverage Criteria"},
                })
            return {
                "claim_id": claim_id,
                "policy_matches": [{"policy_id": policy_id, "payer": payer, "relevance_score": relevance_score}],
                "criteria": criteria,
                "documentation_requirements": [],
                "exclusions": exclusions or [],
            }

        def _deterministic_formatter(self, claim_id, policy_id, payer, relevance_score, evidence_object):
            return self.generate_claim_output(claim_id, policy_id, payer, relevance_score, evidence_object)

    return {
        "config": {"candidate_pool_size": 10},
        "all_chunks": chunks,
        "all_chunks_dict": all_chunks_dict,
        "exact_matcher": GlobalMockRetriever([]),
        "bge_embedder": GlobalMockRetriever(None),
        "faiss_retriever": GlobalMockRetriever(
            [{"chunk_id": c["chunk_id"], "policy_id": c["policy_id"], "score": 0.9} for c in chunks]
        ),
        "bm25_retriever": GlobalMockRetriever([]),
        "candidate_pool": CandidatePool(),
        "bge_reranker": MockReranker(),
        "policy_aggregator": PolicyAggregator(),
        "deterministic_analyzer": DeterministicAnalyzer(),
        "evidence_builder": EvidenceBuilder(),
        "llm_client": MockLLMClient(),
        "prompt_builder": PromptBuilder(),
        "output_validator": OutputValidator(),
        "query_builder": QueryBuilder(),
        "llm_provider": MockLLMProvider(response_generator=_response_gen),
    }


def _pool_source(pool: List[Dict[str, Any]]):
    def source(requested_keys, concepts, claim):
        return list(pool)
    return source


def _all_claim_evidence_ids(result):
    ids = []
    for version in result.versions:
        for item in version["claim"].get("evidence", []):
            ids.append(item.get("evidence_id"))
    return ids


# ---------------------------------------------------------------------------
# Scenario A: Full evidence -> Agent1 -> APPROVE (terminal, no Agent2)
# ---------------------------------------------------------------------------

class TestScenarioAFullEvidenceApprove:
    def test_full_evidence_approves_without_agent2(self):
        chunks = [
            _chunk("CPB-0660", "C01", "Total knee replacement is medically necessary for adults age >= 18."),
            _chunk("CPB-0660", "C02", "At least 3 months of conservative treatment such as physical therapy."),
        ]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-SCEN-A", "CPB-0660",
            evidence=[
                _ev("diagnosis", "EV-A-DX", {"verified_facts": True}),
                _ev("conservative_treatment", "EV-A-PT", {"months": 4}),
            ],
        )
        result = run_agent2_v1_pipeline(claim, components)
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert len(result.versions) == 1
        assert result.agent2_invoked is False
        assert result.resubmissions == 0


# ---------------------------------------------------------------------------
# Scenario B: Missing LDL -> MORE_INFO -> Agent2 retrieves LDL -> V2 -> APPROVE
# ---------------------------------------------------------------------------

class TestScenarioBMissingLdlRecovered:
    def test_missing_ldl_recovered_and_approved(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-B", "C-LDL", "Documented LDL cholesterol level below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-SCEN-B", "POL-SCEN-B")

        pool = [
            _ev("ldl_report", "EV-LDL-001", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"}),
        ]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.final_decision.outcome == DecisionOutcome.APPROVE
        assert result.agent2_invoked is True
        assert result.resubmissions == 1
        assert len(result.versions) == 2
        # V1 decision preserved immutably
        assert result.versions[0]["decision"].outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert len(result.versions[0]["claim"]["evidence"]) == 1
        # V2 carries exactly the recovered record as new_evidence_delta
        assert result.versions[1]["new_evidence_delta"] == ["EV-LDL-001"]
        v2_ids = [e["evidence_id"] for e in result.versions[1]["claim"]["evidence"]]
        assert v2_ids == ["EV-DX-1", "EV-LDL-001"]
        assert result.versions[1]["claim"]["case_data"]["clinical_metrics"]["ldl_value"] == 55
        # Submission package released with provenance
        assert len(result.submissions) == 1
        assert result.submissions[0]["new_evidence_delta"] == ["EV-LDL-001"]
        assert result.submissions[0]["released"] is True


# ---------------------------------------------------------------------------
# Scenario C: Documentation insufficiency (statin step therapy undocumented)
# -> REQUEST_MORE_INFORMATION -> Agent2 retrieves valid 120-day statin
# evidence -> V2 -> APPROVE.
#
# Frozen routing: this is represented as REQUEST_MORE_INFORMATION, never as a
# recoverable REJECT. A documented hard failure (metric present but failing)
# would be a terminal REJECT with no Agent2 (see TestScenarioF).
# ---------------------------------------------------------------------------

class TestScenarioCDocumentationInsufficiencyStatin:
    def test_undocumented_statin_trial_is_rmi_recovered_and_approved(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-C", "C-ST", "At least 120 days of statin step therapy documented.")]
        components = _build_components(chunks)
        # No statin duration is documented in V1 (metric absent -> MISSING,
        # not a definitive FAIL), and no statin_trial evidence was submitted.
        claim = _scenario_claim("CLM-SCEN-C", "POL-SCEN-C")

        pool = [
            _ev("statin_trial", "EV-STATIN-150",
                {"statin_duration_days": 150, "content_reference": "Atorvastatin 150-day trial"}),
        ]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        # V1 must be REQUEST_MORE_INFORMATION (documentation insufficiency is
        # never a recoverable REJECT), and it is the only recoverable route.
        v1 = result.versions[0]["decision"]
        assert v1.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert v1.agent2_recoverable is True
        assert classify_decision_for_agent2(v1) == "RECOVERABLE"
        # V2 flips to APPROVE via real recovered evidence
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.resubmissions == 1
        assert result.versions[1]["new_evidence_delta"] == ["EV-STATIN-150"]
        assert result.versions[1]["claim"]["case_data"]["clinical_metrics"]["statin_duration_days"] == 150
        # Immutability: the V1 snapshot never carried the recovered metric.
        assert result.versions[0]["claim"]["case_data"]["clinical_metrics"].get("statin_duration_days") is None


# ---------------------------------------------------------------------------
# Scenario D: Missing Metformin -> MISSING -> HUMAN_REVIEW, no fabrication
# ---------------------------------------------------------------------------

class TestScenarioDMissingMetforminNoFabrication:
    def test_missing_metformin_escalates_without_fabrication(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-D", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-SCEN-D", "POL-SCEN-D")

        # Pool contains records, but none of them is metformin evidence.
        pool = [_ev("ldl_report", "EV-LDL-001", {"ldl_value": 55})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.human_review_required is True
        assert result.resubmissions == 0
        assert len(result.versions) == 1  # no V2 was fabricated
        # Anti-fabrication: every evidence id present anywhere existed in V1 or the pool
        allowed = {"EV-DX-1", "EV-LDL-001"}
        assert set(_all_claim_evidence_ids(result)) <= allowed
        joined = " ".join(result.human_review_reasons)
        assert "fabricated" in joined.lower() or "no recoverable" in joined.lower()


# ---------------------------------------------------------------------------
# Scenario E: Statin found but duration undocumented -> UNCERTAIN -> HUMAN_REVIEW
# ---------------------------------------------------------------------------

class TestScenarioEUncertainDurationHumanReview:
    def test_found_but_undocumented_duration_is_not_satisfied(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-E", "C-ST", "At least 120 days of statin step therapy documented.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-SCEN-E", "POL-SCEN-E")

        # FOUND statin record, but its duration is undocumented (ambiguous).
        pool = [
            _ev("statin_trial", "EV-STATIN-AMBIG",
                {"content_reference": "Statin mentioned; duration undocumented"},
                ambiguous=True),
        ]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        # FOUND != SATISFIED: evidence was recovered (V2 exists) but the final
        # outcome is HUMAN_REVIEW, never APPROVE.
        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert len(result.versions) == 2
        assert result.versions[1]["new_evidence_delta"] == ["EV-STATIN-AMBIG"]
        final_states = [ev.state for ev in result.final_decision.criteria_evaluations.values()]
        assert "CONFLICTING" in final_states


# ---------------------------------------------------------------------------
# Scenario F: Hard coverage exclusion -> no Agent2 recovery
# ---------------------------------------------------------------------------

class TestScenarioFHardExclusionNoRecovery:
    def test_hard_exclusion_is_terminal(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-F", "C01", "Diagnosis documentation required.")]
        exclusions = [{
            "exclusion_id": "EX-AGE",
            "name": "Age exclusion",
            "rule": {"field": "patient_age", "operator": "gte", "value": 80},
            "required_evidence_keys": [],
        }]
        components = _build_components(chunks, exclusions=exclusions)
        claim = _scenario_claim("CLM-SCEN-F", "POL-SCEN-F", age=85)

        pool = [_ev("diagnosis", "EV-EXTRA-DX", {"verified_facts": True})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.agent2_invoked is False
        assert result.resubmissions == 0
        assert len(result.versions) == 1


# ---------------------------------------------------------------------------
# Scenario G: Lapsed eligibility -> terminal REJECT, no Agent2
# ---------------------------------------------------------------------------

class TestScenarioGLapsedEligibility:
    def test_lapsed_eligibility_blocks_recovery(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-G", "C-LDL", "Documented LDL report required.")]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-SCEN-G", "POL-SCEN-G",
            metrics_extra={"eligibility_eligible": False, "coverage_status": "INACTIVE"},
        )

        pool = [_ev("ldl_report", "EV-LDL-001", {"ldl_value": 55})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.agent2_invoked is False
        assert result.resubmissions == 0
        assert len(result.versions) == 1
        assert result.human_review_required is False
        joined = " ".join(result.audit_trail).lower()
        assert "eligibility" in joined


# ---------------------------------------------------------------------------
# Scenario H: Filing deadline -> terminal REJECT, no Agent2
# ---------------------------------------------------------------------------

class TestScenarioHFilingDeadline:
    def test_filing_deadline_blocks_recovery(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-H", "C-LDL", "Documented LDL report required.")]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-SCEN-H", "POL-SCEN-H",
            metrics_extra={"filing_deadline_exceeded": True},
        )

        pool = [_ev("ldl_report", "EV-LDL-001", {"ldl_value": 55})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.agent2_invoked is False
        assert result.resubmissions == 0
        assert len(result.versions) == 1
        assert result.human_review_required is False
        joined = " ".join(result.audit_trail).lower()
        assert "filing deadline" in joined


# ---------------------------------------------------------------------------
# Scenario I: HUMAN_REVIEW -> no direct Agent2 recovery
# ---------------------------------------------------------------------------

class TestScenarioIHumanReviewNoDirectRecovery:
    def test_human_review_is_terminal_for_agent2(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-I", "C01", "Diagnosis documentation required.")]
        components = _build_components(chunks)
        # Two conflicting diagnosis records -> deterministic HUMAN_REVIEW.
        claim = _scenario_claim(
            "CLM-SCEN-I", "POL-SCEN-I",
            evidence=[
                _ev("diagnosis", "EV-DX-A", {"verified_facts": True, "note": "OA right knee"}),
                _ev("diagnosis", "EV-DX-B", {"verified_facts": False, "note": "contradicting note"}),
            ],
        )

        pool = [_ev("diagnosis", "EV-DX-C", {"verified_facts": True})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.agent2_invoked is False  # no direct recovery from HUMAN_REVIEW
        assert result.resubmissions == 0
        assert len(result.versions) == 1


# ---------------------------------------------------------------------------
# Scenario J: Sensitive evidence -> release blocked -> HUMAN_REVIEW
# ---------------------------------------------------------------------------

class TestScenarioJSensitiveEvidenceBlocked:
    def test_sensitive_evidence_blocked_by_release_gate(self, scenario_registry):
        chunks = [_chunk("POL-SCEN-J", "C-LDL", "Documented LDL report required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-SCEN-J", "POL-SCEN-J")

        pool = [
            _ev("ldl_report", "EV-LDL-SENS", {"ldl_value": 60}, sensitivity="PROTECTED_HIV"),
        ]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.sensitive_blocked is True
        assert result.resubmissions == 0
        assert len(result.versions) == 1
        # The protected record must never enter any claim version.
        assert "EV-LDL-SENS" not in _all_claim_evidence_ids(result)


# ---------------------------------------------------------------------------
# Scenario K: Maximum resubmission limit -> stop safely
# ---------------------------------------------------------------------------

class TestScenarioKMaxResubmissionLimit:
    def test_resubmission_cap_stops_safely(self, scenario_registry):
        chunks = [
            _chunk("POL-SCEN-K", "C-A", "Extra documentation A required."),
            _chunk("POL-SCEN-K", "C-B", "Extra documentation B required."),
        ]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-SCEN-K", "POL-SCEN-K")

        # Only doc A exists in the provider pool; doc B is never available, so
        # every version still lacks doc B. The cap must stop the loop safely.
        pool = [_ev("extra_doc_a", "EV-DOC-A", {"verified_facts": True})]
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), max_resubmissions=1
        )

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.resubmissions == 1
        assert len(result.versions) == 2  # V1 + exactly one resubmission (V2)
        assert result.versions[0]["decision"].outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert result.versions[1]["decision"].outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        joined = " ".join(result.human_review_reasons)
        assert "MAX_RESUBMISSION_ATTEMPTS" in joined
        # History intact: both versions preserved, V1 untouched
        assert result.versions[0]["version"] == "V1"
        assert result.versions[1]["version"] == "V2"
        assert len(result.versions[0]["claim"]["evidence"]) == 1
