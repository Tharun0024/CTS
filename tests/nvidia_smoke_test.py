import os
import sys

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def load_env():
    """
    Manually parses the local .env file and sets environment variables.
    Fulfills Phase 3 zero-dependency constraints.
    """
    # Systematically locate the root .env file relative to this source directory
    src_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(src_dir, "..", ".env"),
        ".env",
        "../.env",
        "y:\\cts-dca1\\.env",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            # Strip whitespace and wrapping quotes
                            val_str = v.strip().strip("'\"")
                            os.environ[k.strip()] = val_str
                break
            except Exception:
                pass


# Execute load_env immediately when this script is run
load_env()


from decision_agent import (
    DecisionAgent,
    CaseData,
    EvidenceItem,
    Policy,
    PolicyCriterion,
    Rule,
    EvidenceStatus,
    DecisionOutcome,
)
from decision_agent.llm_provider import NVIDIAProvider


def run_smoke_test():
    print("=== Running Live NVIDIA NIM Smoke Test ===")
    
    # Reload local env variables in case of updates
    load_env()

    # 1. Check for API key
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key or not api_key.strip():
        print("Error: NVIDIA_API_KEY environment variable is not configured.")
        print("Please check your .env file or export NVIDIA_API_KEY.")
        sys.exit(1)
        
    print("API Key presence verify: OK.")
    
    # 2. Create minimal testing policy
    policy = Policy(
        policy_id="POL-SMOKE",
        name="Smoke Test Policy",
        exclusions=[],
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-SMOKE",
                name="HbA1c Clinic Verification",
                description="Checks lab HbA1c",
                mandatory=True,
                required_evidence_keys=["hba1c_report"],
                clinical_rule=Rule(field="clinical_metrics.HbA1c", operator="gt", value=8.0),
                evidence_rule=Rule(field="hba1c", operator="gt", value=8.0)
            )
        ]
    )
    
    # 3. Create CaseData and Evidence (including unstructured text to force LLM invocation)
    case_data = CaseData(
        case_id="C-SMOKE",
        patient_age=40,
        clinical_metrics={"HbA1c": 8.5}
    )
    
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Smoke Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="The patient's lab sheet shows HbA1c is 8.5%."
        )
    ]
    
    # 4. Initialize agent with NVIDIAProvider
    provider = NVIDIAProvider(api_key=api_key)
    agent = DecisionAgent(policy, llm_provider=provider)
    
    print(f"Requesting completions from: {provider.endpoint}")
    print(f"Model ID: {provider.model}")
    
    # 5. Run evaluation
    try:
        res = agent.evaluate(case_data, evidence, use_llm=True)
        print("Success! Live response parsed successfully.")
        
        # Output info safely (do not expose credentials)
        print(f"NVIDIA API Response Success.")
        print(f"Model: {provider.model}")
        print(f"Decision Outcome: {res.outcome.value}")
        print(f"Reasoning summary: {res.reasoning}")
        
        if res.outcome == DecisionOutcome.APPROVE:
            print("=== Live NVIDIA NIM Smoke Test Passed ===")
            sys.exit(0)
        else:
            print(f"SMOKE TEST FAILED: expected APPROVE, got {res.outcome.value}")
            sys.exit(1)
            
    except Exception as ex:
        print(f"SMOKE TEST ERROR: call failed with exception: {str(ex)}")
        sys.exit(1)


if __name__ == "__main__":
    run_smoke_test()
