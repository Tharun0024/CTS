import json
import os
import requests
from typing import List, Dict
from ..schemas.payer_response import PayerResponse

try:
    from ..config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL
except ImportError:
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL") or os.getenv("NVIDIA_API_URL") or "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

class RejectionAnalyzer:
    """Analyzes payer responses (rejections or more-info requests) to identify missing/failed parameters.
    Uses NVIDIA LLM for interpreting clinical concepts from payer responses."""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key if api_key else NVIDIA_API_KEY
        self.base_url = base_url if base_url else NVIDIA_BASE_URL
        self.model = model if model else NVIDIA_MODEL

    def analyze_payer_response(self, response: PayerResponse) -> Dict[str, List[str]]:
        """
        Parses PayerResponse structured fields and extracts target search concepts.
        Returns a dict containing:
          - 'failed_criterion_ids': IDs of failed criteria.
          - 'requested_concepts': Clinical keywords to guide recovery search.
        """
        failed_ids = response.failed_criteria
        requested_info = response.requested_information
        
        target_concepts = []
        
        # Analyze requested information descriptions to map them to database concepts
        for info in requested_info:
            info_lower = info.lower()
            if "ldl" in info_lower or "cholesterol" in info_lower or "lipid" in info_lower:
                target_concepts.append("ldl")
            if "statin" in info_lower or "simvastatin" in info_lower or "atorvastatin" in info_lower or "rosuvastatin" in info_lower:
                target_concepts.append("statin")
            if "hemoglobin" in info_lower or "hb" in info_lower:
                target_concepts.append("hemoglobin")
            if "iron" in info_lower or "ferrous" in info_lower:
                target_concepts.append("iron")
            if "metformin" in info_lower:
                target_concepts.append("metformin")
            if "hba1c" in info_lower:
                target_concepts.append("hba1c")
            if "physical therapy" in info_lower or "pt" in info_lower or "conservative" in info_lower or "therapy" in info_lower:
                target_concepts.append("physical therapy")
            if "imaging" in info_lower or "x-ray" in info_lower or "xray" in info_lower or "radiography" in info_lower or "mri" in info_lower or "ct" in info_lower:
                target_concepts.append("imaging")
                
        # If no specific concepts found but there are failed criteria, map based on criterion IDs
        if not target_concepts and failed_ids:
            for fid in failed_ids:
                fid_lower = fid.lower()
                if "c03" in fid_lower:  # usually LDL in Repatha, or Hb in Epogen, or HbA1c in Humulin, or Pacemaker criteria
                    target_concepts.extend(["ldl", "hemoglobin", "hba1c"])
                elif "c04" in fid_lower: # Iron in Epogen
                    target_concepts.extend(["iron", "ldl"])
                elif "c02" in fid_lower: # Statin in Repatha, Metformin in Humulin, PT in TKA
                    target_concepts.extend(["statin", "metformin", "physical therapy"])

        # Fallback to general terms in the reason text if both lists are empty
        if not target_concepts:
            reason_lower = response.reason.lower()
            for kw in ["ldl", "statin", "iron", "metformin", "hba1c", "physical therapy", "imaging", "hemoglobin"]:
                if kw in reason_lower:
                    target_concepts.append(kw)

        # Use LLM to interpret clinical concepts if we have API key and no clear concepts found
        if self.api_key and (not target_concepts or len(failed_ids) > 0):
            llm_concepts = self._interpret_with_llm(response, failed_ids, requested_info)
            if llm_concepts:
                target_concepts.extend(llm_concepts)

        return {
            "failed_criterion_ids": failed_ids,
            "requested_concepts": list(set(target_concepts))
        }

    def _interpret_with_llm(self, response: PayerResponse, failed_ids: List[str], requested_info: List[str]) -> List[str]:
        """Use NVIDIA LLM to interpret clinical concepts from payer response."""
        try:
            if not self.api_key:
                return []

            system_prompt = """You are a clinical terminology expert. Extract specific clinical concepts 
            from payer response texts that would guide database searches for missing evidence.
            
            Return a JSON array of clinical search terms like: ["ldl", "statin", "hba1c", "hemoglobin", "iron", 
            "metformin", "physical therapy", "imaging", "age", "diagnosis", "lab_value", "medication_trial"]
            """

            user_prompt = f"""
Payer Decision: {response.decision}
Reason: {response.reason}
Failed Criteria IDs: {failed_ids}
Requested Information: {requested_info}

Extract specific clinical concepts that would be searched for in a patient database.
Return ONLY a JSON array of search terms.
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            result = response.json()
            llm_output = result["choices"][0]["message"]["content"]
            
            # Parse JSON array
            import re
            json_match = re.search(r'\[.*\]', llm_output)
            if json_match:
                concepts = json.loads(json_match.group(0))
                return [c.lower() for c in concepts if isinstance(c, str)]
                
        except Exception as e:
            print(f"[Warning] LLM interpretation failed: {e}")
        
        return []
