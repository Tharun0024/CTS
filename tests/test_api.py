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
