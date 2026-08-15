from typing import List, Dict, Any

class EvidenceBuilder:
    def __init__(self):
        pass
        
    def build_evidence(
        self,
        policy_id: str,
        payer: str,
        analyzer_output: Dict[str, Any],
        source_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assemble the internal Evidence Object using only grounded information.
        STRICT RULES: No decisions (approval, reject, deny, met, not-met) are allowed.
        """
        # Assemble standard internal evidence container
        evidence_object = {
            "policy_id": policy_id,
            "payer": payer,
            "criteria": analyzer_output.get("criteria", []),
            "documentation": analyzer_output.get("documentation_requirements", []),
            "exclusions": analyzer_output.get("exclusions", []),
            "source_chunks": [
                {
                    "chunk_id": c.get("chunk_id"),
                    "section": c.get("section"),
                    "text": c.get("text")
                } for c in source_chunks
            ]
        }
        return evidence_object
