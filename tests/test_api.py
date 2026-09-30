import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture(scope="module")
def client():
    # Force loading environment variables and startup event
    with TestClient(app) as c:
        yield c

def test_api_triage_pacemaker(client):
    # Valid claim for cardiac pacemaker NCD-20.8.3
    claim_data = {
        "claim_id": "CLM-PACEMAKER-01",
        "insurance": {
            "primary": {
                "payer": "CMS",
                "policy_id": "NCD-20.8.3"
            }
        },
        "diagnosis": [
            {"code": "I49.5", "description": "Sick sinus syndrome"}
        ],
        "procedure": {
            "code": "33206",
            "description": "Insertion of pacemaker"
        },
        "clinical_domain": "cardiology"
    }
    
    response = client.post("/triage", json=claim_data)
    assert response.status_code == 200
    res_json = response.json()
    
    # Verify structure
    assert res_json["claim_id"] == "CLM-PACEMAKER-01"
    assert len(res_json["policy_matches"]) == 1
    assert res_json["policy_matches"][0]["policy_id"] == "NCD-20.8.3"
    
    # Check criteria list
    assert len(res_json["criteria"]) > 0
    assert res_json["criteria"][0]["source"]["policy_id"] == "NCD-20.8.3"
    
    # Ensure no decision variables are leaked in output root keys
    allowed_keys = {"claim_id", "policy_matches", "criteria", "documentation_requirements"}
    assert set(res_json.keys()).issubset(allowed_keys)

def test_api_validation_error(client):
    # Malformed claim (missing required procedure code)
    bad_claim = {
        "claim_id": "CLM-BAD-01",
        "insurance": {
            "primary": {
                "payer": "CMS"
            }
        },
        "diagnosis": [],
        "procedure": {}, # Missing code/description
        "clinical_domain": ""
    }
    
    response = client.post("/triage", json=bad_claim)
    assert response.status_code == 422


def test_api_evaluate_pacemaker(client):
    # Valid canonical claim for pacemaker NCD-20.8.3
    canonical_claim = {
        "claim_id": "CLM-PACEMAKER-02",
        "submission": {"attempt": 1, "date": "2026-08-14T23:29:05Z"},
        "case_data": {
            "case_id": "CLM-PACEMAKER-02",
            "patient_age": 70,
            "diagnoses": ["I49.5"],
            "procedures": ["33206"],
            "clinical_metrics": {
                "patient_gender": "Male",
                "claim_scenario_type": "COMPLETE",
                "claim_payer": "CMS",
                "claim_policy_id": "NCD-20.8.3"
            }
        },
        "evidence": [
            {
                "evidence_key": "clinical_information",
                "evidence_id": "clinical_info_02",
                "source": "Clinical Information",
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {}
            }
        ]
    }
    
    response = client.post("/evaluate", json=canonical_claim)
    assert response.status_code == 200
    res_json = response.json()
    
    # Verify structure
    assert res_json["case_id"] == "CLM-PACEMAKER-02"
    assert "outcome" in res_json
    assert "reasoning" in res_json
    assert isinstance(res_json["reasoning"], list)

