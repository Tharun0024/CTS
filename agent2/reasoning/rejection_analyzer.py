from typing import List, Dict
from schemas.payer_response import PayerResponse

class RejectionAnalyzer:
    """Analyzes payer responses (rejections or more-info requests) to identify missing/failed parameters."""
    
    def __init__(self):
        pass

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

        return {
            "failed_criterion_ids": failed_ids,
            "requested_concepts": list(set(target_concepts))
        }
