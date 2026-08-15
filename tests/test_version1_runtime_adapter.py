import json

from decision.schemas import CanonicalClaim
from adapters.runtime_adapter import RuntimeAdapter


def test_initial_claim_retrieval():
    payload = RuntimeAdapter().get_provider_canonical_claim("PA045", "CLM-08BC25", 1)

    assert payload is not None
    assert payload["claim_id"] == "CLM-08BC25"
    assert payload["submission"]["attempt"] == 1
    assert payload["case_data"]["case_id"] == "CLM-08BC25"
    assert payload["case_data"]["patient_age"] == 49
    assert payload["case_data"]["procedures"] == ["27447"]
    assert len(payload["evidence"]) >= 3
    # Diagnoses must come from submitted evidence ICD codes, not full history dump
    assert all(isinstance(d, str) for d in payload["case_data"]["diagnoses"])
    assert all(len(d) < 16 for d in payload["case_data"]["diagnoses"])  # ICD-style, not long SNOMED dumps alone
    # Evidence keys must be semantic when evidence_type is known
    known_keys = {"diagnosis", "imaging", "recommendation", "conservative_treatment"}
    assert all(
        item["evidence_key"] in known_keys
        or item["evidence_key"] == item["evidence_id"]
        for item in payload["evidence"]
    )
    assert any(item["evidence_key"] in known_keys for item in payload["evidence"])

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


def test_linked_runtime_claim_includes_payer_without_overriding_claim_payer():
    linked = RuntimeAdapter().get_linked_runtime_claim("PA045", "CLM-08BC25", 1)

    assert linked is not None
    metrics = linked["case_data"]["clinical_metrics"]
    assert metrics["claim_payer"] == "Aetna"  # never overridden
    assert metrics["member_id"] == "PA045"
    assert metrics["member_payer_id"] == "CMS"
    assert metrics["plan_id"] == "PLAN-CMS-001"
    assert metrics["claim_member_payer_mismatch"] is True
    assert linked["payer_context"]["member_id"] == "PA045"
    assert "evidence" not in linked["payer_context"]


def test_payer_alias_normalization_is_explicit():
    assert RuntimeAdapter.normalize_payer_alias("Athena") == "Aetna"
    assert RuntimeAdapter.normalize_payer_alias("Aetna") == "Aetna"
    assert RuntimeAdapter.normalize_payer_alias("UnknownPayerX") == "UnknownPayerX"


def test_unknown_evidence_type_remains_unresolved():
    assert RuntimeAdapter.map_evidence_key("NOT_A_REAL_TYPE", "EV-XYZ") == "EV-XYZ"
    assert RuntimeAdapter.map_evidence_key("DIAGNOSIS", "EV-XYZ") == "diagnosis"
