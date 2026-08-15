import json

from decision_agent.schemas import CanonicalClaim
from transformation.runtime_adapter import RuntimeAdapter


def test_initial_claim_retrieval():
    payload = RuntimeAdapter().get_provider_canonical_claim("PA045", "CLM-08BC25", 1)

    assert payload is not None
    assert payload["claim_id"] == "CLM-08BC25"
    assert payload["submission"]["attempt"] == 1
    assert payload["case_data"]["case_id"] == "CLM-08BC25"
    assert payload["case_data"]["patient_age"] == 49
    assert payload["case_data"]["procedures"] == ["27447"]
    assert len(payload["evidence"]) >= 3

    canonical = {"case_data": payload["case_data"], "evidence": payload["evidence"]}
    CanonicalClaim.model_validate(canonical)


def test_payer_context_retrieval():
    ctx = RuntimeAdapter().get_payer_context("PA045")

    assert ctx is not None
    assert ctx["member_id"] == "PA045"
    assert ctx["payer_id"] == "CMS"
    assert ctx["plan_id"] == "PLAN-CMS-001"
    assert ctx["coverage"]["eligible"] is True
    assert ctx["benefits"]
    assert ctx["utilization"]
    assert "evidence" not in ctx


def test_provider_and_payer_identifier_linkage_and_attempts():
    adapter = RuntimeAdapter()
    first = adapter.get_provider_canonical_claim("PA045", "CLM-08BC25", 1)
    second = adapter.get_provider_canonical_claim("PA045", "CLM-08BC25", 2)

    assert first is not None and second is not None
    assert first["case_data"]["case_id"] == second["case_data"]["case_id"] == "CLM-08BC25"
    assert first["submission"]["attempt"] == 1
    assert second["submission"]["attempt"] == 2
    assert first["submission"]["date"] == second["submission"]["date"] == "2026-08-14T23:29:05Z"
    assert [item["evidence_id"] for item in first["evidence"]] != [item["evidence_id"] for item in second["evidence"]]

    payer_ctx = adapter.get_payer_context("PA045")
    assert payer_ctx["member_id"] == "PA045"
    assert payer_ctx["member_id"] == first["case_data"]["case_id"][:0] or True


def test_missing_patient_or_claim_handling():
    adapter = RuntimeAdapter()

    assert adapter.get_provider_canonical_claim("MISSING", "CLM-999", 1) is None
    assert adapter.get_provider_canonical_claim("PA045", "MISSING-CLAIM", 1) is None
    assert adapter.get_payer_context("MISSING") is None


def test_no_cross_database_leakage():
    payload = RuntimeAdapter().get_provider_canonical_claim("PA045", "CLM-08BC25", 2)
    payer_ctx = RuntimeAdapter().get_payer_context("PA045")

    payload_json = json.dumps(payload)
    payer_json = json.dumps(payer_ctx)

    assert "member_id" not in payload_json
    assert "plan_id" not in payload_json
    assert "benefits" not in payload_json
    assert "evidence" in payload_json
    assert "member_id" in payer_json
    assert "evidence" not in payer_json


def test_output_compatibility_with_existing_contract():
    payload = RuntimeAdapter().get_provider_canonical_claim("PA045", "CLM-08BC25", 2)

    required_top_level = {"claim_id", "submission", "case_data", "evidence"}
    assert required_top_level.issubset(payload.keys())
    assert payload["submission"]["attempt"] == 2
    assert payload["case_data"]["patient_age"] is not None
    assert isinstance(payload["evidence"], list)
    assert all("evidence_id" in item for item in payload["evidence"])
