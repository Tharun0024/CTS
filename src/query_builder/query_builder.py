from typing import Dict, Any
from src.schema.models import ClaimInput

class QueryBuilder:
    def __init__(self):
        pass
        
    def build_query(self, claim: ClaimInput) -> Dict[str, Any]:
        """
        Generate structured, exact, BM25, and semantic queries from a normalized ClaimInput.
        """
        # 1. Structured Query (contains exact values for quick field matching)
        structured = {
            "payer": claim.insurance.primary.payer,
            "policy_id": claim.insurance.primary.policy_id,
            "clinical_domain": claim.clinical_domain,
            "procedure_code": claim.procedure.code,
            "diagnosis_codes": [d.code for d in claim.diagnosis]
        }
        
        # 2. Exact Match Query Components (list of tokens for exact overlap)
        exact_tokens = [claim.insurance.primary.payer.lower()]
        if claim.insurance.primary.policy_id:
            exact_tokens.append(claim.insurance.primary.policy_id.lower())
        exact_tokens.append(claim.procedure.code.lower())
        for d in claim.diagnosis:
            exact_tokens.append(d.code.lower())
            
        # 3. BM25 Text Query (natural language text to match keyword frequencies)
        # Combine descriptions and codes
        diagnosis_desc = " ".join([d.description for d in claim.diagnosis])
        diagnosis_codes_str = " ".join([d.code for d in claim.diagnosis])
        
        bm25_text = (
            f"{claim.insurance.primary.payer} "
            f"{claim.clinical_domain} "
            f"{claim.procedure.code} {claim.procedure.description} "
            f"{diagnosis_codes_str} {diagnosis_desc}"
        )
        if claim.insurance.primary.policy_id:
            bm25_text = f"{claim.insurance.primary.policy_id} {bm25_text}"
            
        # Clean BM25 text
        bm25_text = " ".join(bm25_text.split())
        
        # 4. Semantic BGE Query (concise query for semantic embedding models)
        # Standard query prefix or format for asymmetric search
        semantic_text = (
            f"payer: {claim.insurance.primary.payer} | "
            f"clinical domain: {claim.clinical_domain} | "
            f"requested procedure: {claim.procedure.code} - {claim.procedure.description} | "
            f"patient diagnoses: {', '.join([f'{d.code} - {d.description}' for d in claim.diagnosis])}"
        )
        if claim.insurance.primary.policy_id:
            semantic_text = f"policy: {claim.insurance.primary.policy_id} | " + semantic_text
            
        return {
            "structured": structured,
            "exact_tokens": exact_tokens,
            "bm25_query": bm25_text,
            "semantic_query": semantic_text
        }
