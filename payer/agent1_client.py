import json
from agent1.payer_engine import PayerEngine
from schemas.submission import SubmissionPackage
from schemas.payer_response import PayerResponse

class Agent1Client:
    """Adapter for Agent 2 to communicate with Agent 1 (Payer).
    Enforces a strict trust boundary by serializing data to JSON strings.
    """
    
    def __init__(self, payer_engine: PayerEngine = None):
        # In a real environment, this would point to a HTTP URL.
        # For the hackathon, we reference the logically isolated PayerEngine instance.
        self.payer_engine = payer_engine if payer_engine else PayerEngine()

    def submit_package(self, package: SubmissionPackage) -> PayerResponse:
        """Transmits the SubmissionPackage across the trust boundary."""
        # 1. Serialize package to JSON (enforces that no live objects or db connections leak)
        package_json = package.model_dump_json()
        
        # 2. Transmit to Payer (represented as parsing JSON on the other side)
        payer_package = SubmissionPackage.model_validate_json(package_json)
        
        # 3. Payer reviews package
        payer_response = self.payer_engine.process_submission(payer_package)
        
        # 4. Serialize payer response back
        response_json = payer_response.model_dump_json()
        
        # 5. Return deserialized response to Agent 2
        return PayerResponse.model_validate_json(response_json)
