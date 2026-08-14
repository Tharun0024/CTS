from typing import List, Dict, Any, Tuple

class PolicyAggregator:
    def __init__(self):
        pass
        
    def aggregate(
        self,
        candidates: List[Dict[str, Any]],
        all_chunks: List[Dict[str, Any]],
        query_payer: str,
        query_proc: str,
        query_domain: str
    ) -> Tuple[str, List[Dict[str, Any]], float]:
        """
        Determine the single best-matching policy ID, aggregate all chunks belonging to that policy,
        and apply the Consistency Gate to prevent cross-policy contamination.
        """
        if not candidates:
            return "NO_RELIABLE_POLICY_MATCH", [], 0.0
            
        # Determine specificity keywords based on CPT procedure code
        specificity_keywords = []
        q_proc_clean = query_proc.strip().upper()
        
        # Check range matching helper for specificity
        def is_code_in_any_range(code: str, ranges: List[str]) -> bool:
            if code in ranges:
                return True
            for r in ranges:
                if "-" in r and self._is_cpt_in_range(code, r):
                    return True
            return False

        if is_code_in_any_range(q_proc_clean, ["27447", "27445", "27486", "27487"]):
            specificity_keywords = ["knee"]
        elif is_code_in_any_range(q_proc_clean, ["27130", "27132", "27134", "27137", "27138"]):
            specificity_keywords = ["hip", "joint"]
        elif is_code_in_any_range(q_proc_clean, ["33206", "33207", "33208"]):
            specificity_keywords = ["pacemaker"]
        elif is_code_in_any_range(q_proc_clean, ["33249", "33230", "33231", "33240", "33241"]):
            specificity_keywords = ["defibrillator", "icd"]
        elif is_code_in_any_range(q_proc_clean, ["77067", "77066", "77065", "76641", "76642", "77049"]):
            specificity_keywords = ["breast", "mammography", "mammogram", "sonography"]
        elif is_code_in_any_range(q_proc_clean, ["81528", "82270", "G0328", "G0327"]):
            specificity_keywords = ["colorectal", "colon"]
        elif is_code_in_any_range(q_proc_clean, ["78811", "78812", "78813", "78814", "78815", "78816", "A9552"]):
            specificity_keywords = ["pet", "tomography", "oncologic"]
            
        policy_scores = {}
        
        for cand in candidates:
            chunk = cand["chunk"]
            chunk_payer = chunk.get("payer", "")
            chunk_procs = chunk.get("procedure_codes", [])
            chunk_domain = chunk.get("clinical_domain", "")
            policy_id = chunk["policy_id"]
            policy_title = chunk.get("policy_title", "").lower()
            
            # Payer compatibility check
            payer_compat = False
            if query_payer.lower() in chunk_payer.lower() or chunk_payer.lower() in query_payer.lower():
                payer_compat = True
                
            # Procedure code or domain compatibility check
            proc_compat = False
            if query_proc in chunk_procs:
                proc_compat = True
            else:
                # Range check
                for cp in chunk_procs:
                    if "-" in cp and self._is_cpt_in_range(query_proc, cp):
                        proc_compat = True
                        break
                        
            domain_compat = (query_domain.lower() == chunk_domain.lower())
            
            # If compatible, track and boost based on specificity keywords
            if payer_compat and (proc_compat or domain_compat):
                base_score = cand.get("rerank_score", cand.get("combined_score", 0.0))
                
                # Apply specificity boost if title matches clinical specificity keywords
                boost = 0.0
                for kw in specificity_keywords:
                    if kw in policy_title:
                        boost += 0.15
                        break
                        
                boosted_score = base_score + boost
                
                if policy_id not in policy_scores or boosted_score > policy_scores[policy_id]["boosted_score"]:
                    policy_scores[policy_id] = {
                        "boosted_score": boosted_score,
                        "original_score": base_score
                    }
                    
        if not policy_scores:
            return "NO_RELIABLE_POLICY_MATCH", [], 0.0
            
        # Select the policy with the highest boosted score
        selected_policy_id = max(policy_scores.keys(), key=lambda k: policy_scores[k]["boosted_score"])
        best_score = policy_scores[selected_policy_id]["original_score"]
        
        # Aggregate ALL chunks belonging to selected_policy_id
        aggregated_chunks = []
        for chunk in all_chunks:
            # Policy Consistency Gate: STRICT check to prevent cross-contamination
            if chunk["policy_id"] == selected_policy_id:
                aggregated_chunks.append(chunk)
                
        return selected_policy_id, aggregated_chunks, best_score

    def _is_cpt_in_range(self, cpt: str, cpt_range: str) -> bool:
        try:
            parts = cpt_range.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                val = int(cpt.strip())
                return start <= val <= end
        except ValueError:
            pass
        return False

