from typing import List, Dict, Any

class DeterministicAnalyzer:
    def __init__(self):
        pass
        
    def analyze_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the aggregated chunks of a selected policy.
        Extracts criteria, documentation requirements, and exclusions grounding them in sources.
        STRICT RULES: Does NOT make any approval or met/not-met decisions.
        """
        criteria = []
        documentation_requirements = []
        exclusions = []
        
        # Sort chunks by criterion_id to ensure order (C01, C02, C03...)
        sorted_chunks = sorted(chunks, key=lambda x: x.get("criterion_id", ""))
        
        for chunk in sorted_chunks:
            c_id = chunk.get("criterion_id", "")
            # Skip coding references or general non-clinical chunks for the main criteria output if necessary,
            # but keep them if they are part of the policy.
            if chunk.get("criterion_type") == "coding_reference":
                # We can still extract it or skip it based on needs. Let's include it if it contains requirements.
                pass
                
            # 1. Extract Criteria
            # Format text as policy_requirement. We clean and shorten the criterion name.
            section = chunk.get("section", "Coverage Criteria")
            criterion_name = chunk.get("criterion_name", "")
            
            # Formulate a user-friendly criterion title: e.g. "Key Clinical Thresholds" or "Coverage Criteria"
            criterion_title = section
            if "—" in criterion_name:
                parts = criterion_name.split("—")
                if len(parts) > 1:
                    criterion_title = parts[1].strip().capitalize()
                    
            criteria.append({
                "criterion_id": c_id,
                "criterion": criterion_title,
                "policy_requirement": chunk.get("text", ""),
                "source": {
                    "policy_id": chunk.get("policy_id"),
                    "section": section
                }
            })
            
            # 2. Extract Documentation
            doc_reqs = chunk.get("documentation_requirements", [])
            for req in doc_reqs:
                if req not in [r["requirement"] for r in documentation_requirements]:
                    documentation_requirements.append({
                        "requirement": req,
                        "source": chunk.get("policy_id")
                    })
                    
            # 3. Extract Exclusions
            excl_list = chunk.get("exclusions", [])
            for excl in excl_list:
                if excl not in exclusions:
                    exclusions.append(excl)
                    
            # 4. Extract Limitations & Contraindications into exclusions
            lim_list = chunk.get("limitations", [])
            for lim in lim_list:
                if f"Limitation: {lim}" not in exclusions:
                    exclusions.append(f"Limitation: {lim}")
                    
            contra_list = chunk.get("contraindications", [])
            for contra in contra_list:
                if f"Contraindication: {contra}" not in exclusions:
                    exclusions.append(f"Contraindication: {contra}")
                    
        return {
            "criteria": criteria,
            "documentation_requirements": documentation_requirements,
            "exclusions": exclusions
        }
