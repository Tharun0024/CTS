import pytest
from rag.aggregation.policy_aggregator import PolicyAggregator
from rag.validation.output_validator import OutputValidator

def test_cross_policy_contamination_prevention():
    agg = PolicyAggregator()
    validator = OutputValidator()
    
    # Aggregated chunks for Aetna CPB-0660
    all_chunks = [
        {"chunk_id": "A-C01", "policy_id": "AETNA-CPB-0660", "payer": "Aetna", "section": "Medical Necessity", "procedure_codes": ["27447"], "clinical_domain": "orthopedics"},
        {"chunk_id": "A-C02", "policy_id": "AETNA-CPB-0660", "payer": "Aetna", "section": "Medical Necessity", "procedure_codes": ["27447"], "clinical_domain": "orthopedics"},
        {"chunk_id": "B-C01", "policy_id": "AETNA-CPB-0287", "payer": "Aetna", "section": "Exclusions", "procedure_codes": ["33206"], "clinical_domain": "cardiology"}
    ]
    
    # Candidates with B-C01 and A-C01
    candidates = [
        {"policy_id": "AETNA-CPB-0660", "chunk": all_chunks[0], "combined_score": 0.9},
        {"policy_id": "AETNA-CPB-0287", "chunk": all_chunks[2], "combined_score": 0.8}
    ]
    
    selected_policy, aggregated_chunks, score = agg.aggregate(
        candidates,
        all_chunks,
        query_payer="Aetna",
        query_proc="27447",
        query_domain="orthopedics"
    )
    
    # The aggregator should pick AETNA-CPB-0660
    assert selected_policy == "AETNA-CPB-0660"
    
    # Ensure chunk B-C01 (from CPB-0287) was NOT aggregated (0% contamination rate)
    for chunk in aggregated_chunks:
        assert chunk["policy_id"] == "AETNA-CPB-0660"
        assert chunk["chunk_id"] != "B-C01"
        
    # Output check validation
    output_data = {
        "claim_id": "CLM-100",
        "policy_matches": [
            {"policy_id": "AETNA-CPB-0660", "payer": "Aetna", "relevance_score": 0.9}
        ],
        "criteria": [
            {
                "criterion_id": "C01",
                "criterion": "Pain",
                "policy_requirement": "Must have pain",
                "source": {"policy_id": "AETNA-CPB-0660", "section": "Medical Necessity"}
            },
            # Contaminated item inserted by bad LLM:
            {
                "criterion_id": "C02",
                "criterion": "Exclude",
                "policy_requirement": "Not covered",
                "source": {"policy_id": "AETNA-CPB-0287", "section": "Exclusions"}
            }
        ],
        "documentation_requirements": []
    }
    
    # Validator must reject because of cross-policy contamination (C02 source policy is CPB-0287)
    is_valid = validator.validate(output_data, selected_policy)
    assert is_valid is False, "Validator failed to flag cross-policy contamination!"
