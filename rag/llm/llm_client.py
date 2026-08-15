import os
import json
import httpx
from typing import Dict, Any, List, Optional

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY


class LLMClient:
    def __init__(self):
        # Use NVIDIA API configuration (same working endpoint as Agent-1).
        self.api_key = os.getenv("NVIDIA_API_KEY", "") or os.getenv("LLM_API_KEY", "mock_api_key_for_testing")
        raw_url = os.getenv("NVIDIA_API_URL", "") or os.getenv("LLM_API_URL", "https://api.openai.com/v1")
        # Normalize endpoint to always end with /chat/completions
        base_stripped = raw_url.rstrip("/")
        if not base_stripped.endswith("/chat/completions"):
            self.api_url = base_stripped + "/chat/completions"
        else:
            self.api_url = base_stripped
        self.model = os.getenv("NVIDIA_MODEL", "") or os.getenv("LLM_MODEL", "meta/llama-3.1-8b-instruct")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.last_fallback_reason: Optional[str] = None
        
    def generate_claim_output(
        self,
        claim_id: str,
        policy_id: str,
        payer: str,
        relevance_score: float,
        evidence_object: Dict[str, Any],
        prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Generates the final claim output JSON using either the configured LLM or the deterministic fallback formatter.
        """
        self.last_fallback_reason = None

        # If it's a mock key or we are testing, use the deterministic fallback immediately.
        # This guarantees 100% schema compliance, 0% hallucinations, and no decision leakage.
        if self.api_key.lower().startswith("mock") or not self.api_key:
            return self._fallback(
                "mock_or_missing_api_key",
                claim_id,
                policy_id,
                payer,
                relevance_score,
                evidence_object,
            )
            
        # Try calling real LLM API (NVIDIA NIM / OpenAI-compatible)
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict healthcare policy data formatter. You output ONLY valid JSON. "
                            "You must NEVER make authorization or medical necessity decisions. "
                            "You must NEVER output words like 'approve', 'reject', 'deny', 'met', or 'not met'. "
                            "You must strictly ground all criteria and documentation in the provided context."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, headers=headers, json=data)
                if response.status_code == 200:
                    resp_json = response.json()
                    content = resp_json["choices"][0]["message"]["content"]
                    output_json = json.loads(content)
                    
                    # Post-processing / Validation checks
                    if self._validate_structure(output_json):
                        self.last_fallback_reason = None
                        return output_json
                    return self._fallback(
                        "llm_response_failed_structure_validation",
                        claim_id,
                        policy_id,
                        payer,
                        relevance_score,
                        evidence_object,
                    )

                reason = self._http_fallback_reason(response.status_code)
                return self._fallback(
                    reason,
                    claim_id,
                    policy_id,
                    payer,
                    relevance_score,
                    evidence_object,
                )
                    
        except Exception as e:
            return self._fallback(
                f"llm_request_exception:{type(e).__name__}",
                claim_id,
                policy_id,
                payer,
                relevance_score,
                evidence_object,
            )

    def _http_fallback_reason(self, status_code: int) -> str:
        if status_code == 401:
            return "llm_authentication_failed:http_401"
        if status_code == 403:
            return "llm_authorization_failed:http_403"
        if status_code == 429:
            return "llm_rate_limited:http_429"
        return f"llm_http_error:status_{status_code}"

    def _fallback(
        self,
        reason: str,
        claim_id: str,
        policy_id: str,
        payer: str,
        relevance_score: float,
        evidence_object: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deterministic fallback with a clear, non-secret reason (always logged)."""
        self.last_fallback_reason = reason
        print(f"[LLMClient] Deterministic fallback engaged. reason={reason}")
        return self._deterministic_formatter(
            claim_id, policy_id, payer, relevance_score, evidence_object
        )

    def _deterministic_formatter(
        self,
        claim_id: str,
        policy_id: str,
        payer: str,
        relevance_score: float,
        evidence_object: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Guaranteed fallback formatter that constructs the exact schema output.
        Populates clinical_rule from CRITERIA_RULES_REGISTRY when a matching
        (policy_id, criterion_id) entry exists. Unknown rules stay None (fail closed).
        """
        # Map criteria
        criteria_output = []
        for crit in evidence_object.get("criteria", []):
            crit_id = crit["criterion_id"]
            # Look up known structured rules from the registry
            registry_entry = CRITERIA_RULES_REGISTRY.get((policy_id, crit_id))

            criteria_output.append({
                "criterion_id": crit_id,
                "criterion": crit["criterion"],
                "policy_requirement": crit["policy_requirement"],
                "source": {
                    "policy_id": crit["source"]["policy_id"],
                    "section": crit["source"]["section"]
                },
                "clinical_rule": registry_entry["clinical_rule"] if registry_entry else None,
                "evidence_rule": registry_entry["evidence_rule"] if registry_entry else None,
                "required_evidence_keys": (
                    list(registry_entry["required_evidence_keys"]) if registry_entry else []
                ),
            })
            
        # Map documentation requirements
        doc_output = []
        for doc in evidence_object.get("documentation", []):
            doc_output.append({
                "requirement": doc["requirement"],
                "source": doc["source"]
            })
            
        # Return exactly the target public schema
        return {
            "claim_id": claim_id,
            "policy_matches": [
                {
                    "policy_id": policy_id,
                    "payer": payer,
                    "relevance_score": round(relevance_score, 4)
                }
            ] if policy_id != "NO_RELIABLE_POLICY_MATCH" else [],
            "criteria": criteria_output,
            "documentation_requirements": doc_output
        }

    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """
        Basic structural validation of generated JSON.
        """
        required_keys = {"claim_id", "policy_matches", "criteria", "documentation_requirements"}
        if not required_keys.issubset(data.keys()):
            return False
            
        # Check no decision tokens leaked
        forbidden_words = {"approve", "reject", "deny", "pend", "met", "not_met", "eligible", "covered"}
        dumped = json.dumps(data).lower()
        for word in forbidden_words:
            # Check for exact matches of forbidden words to avoid false positives
            if f'"{word}"' in dumped or f'": "{word}"' in dumped:
                return False
        return True
