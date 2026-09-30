from typing import List, Dict, Any, Tuple, Optional

class PolicyAggregator:
    def __init__(self):
        pass
        
    def aggregate(
        self,
        candidates: List[Dict[str, Any]],
        all_chunks: List[Dict[str, Any]],
        query_payer: str,
        query_proc: str,
        query_domain: str,
        requested_policy_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], float]:
        """
        Determine the single best-matching policy ID, aggregate all chunks belonging to that policy,
        and apply the Consistency Gate to prevent cross-policy contamination.

        Procedure compatibility is required (domain-only matches are rejected).
        When requested_policy_id is provided, that policy must be available and procedure-
        compatible; otherwise return NO_RELIABLE_POLICY_MATCH (no silent substitution).
        """
        if not candidates and not requested_policy_id:
            return "NO_RELIABLE_POLICY_MATCH", [], 0.0

        q_proc_clean = (query_proc or "").strip().upper()
        q_payer = (query_payer or "").strip()
        requested = (requested_policy_id or "").strip() or None

        # When a claim policy_id is present, only that policy may be selected.
        if requested:
            policy_chunks = [c for c in all_chunks if c.get("policy_id") == requested]
            if not policy_chunks:
                return "NO_RELIABLE_POLICY_MATCH", [], 0.0

            # Prefer scored candidates for this policy; fall back to direct chunk check.
            best_score = 0.0
            found_compat = False
            for cand in candidates:
                chunk = cand.get("chunk") or {}
                if chunk.get("policy_id") != requested:
                    continue
                if self._is_compatible(chunk, q_payer, q_proc_clean):
                    found_compat = True
                    best_score = max(
                        best_score,
                        float(cand.get("rerank_score", cand.get("combined_score", 0.0))),
                    )
            if not found_compat:
                for chunk in policy_chunks:
                    if self._is_compatible(chunk, q_payer, q_proc_clean):
                        found_compat = True
                        break
            if not found_compat:
                return "NO_RELIABLE_POLICY_MATCH", [], 0.0

            aggregated_chunks = [c for c in all_chunks if c.get("policy_id") == requested]
            return requested, aggregated_chunks, best_score

        if not candidates:
            return "NO_RELIABLE_POLICY_MATCH", [], 0.0

        specificity_keywords = self._specificity_keywords(q_proc_clean)
        policy_scores = {}

        for cand in candidates:
            chunk = cand["chunk"]
            policy_id = chunk["policy_id"]
            policy_title = chunk.get("policy_title", "").lower()

            if not self._is_compatible(chunk, q_payer, q_proc_clean):
                continue

            exact_proc_match = q_proc_clean in [
                str(p).strip().upper() for p in (chunk.get("procedure_codes") or [])
            ]
            base_score = cand.get("rerank_score", cand.get("combined_score", 0.0))
            boost = 0.0
            for kw in specificity_keywords:
                if kw in policy_title:
                    boost += 0.15
                    break
            if exact_proc_match:
                boost += 0.10
            boosted_score = base_score + boost

            if policy_id not in policy_scores or boosted_score > policy_scores[policy_id]["boosted_score"]:
                policy_scores[policy_id] = {
                    "boosted_score": boosted_score,
                    "original_score": base_score,
                }

        if not policy_scores:
            return "NO_RELIABLE_POLICY_MATCH", [], 0.0

        selected_policy_id = max(policy_scores.keys(), key=lambda k: policy_scores[k]["boosted_score"])
        best_score = policy_scores[selected_policy_id]["original_score"]
        aggregated_chunks = [c for c in all_chunks if c.get("policy_id") == selected_policy_id]
        return selected_policy_id, aggregated_chunks, best_score

    def _is_compatible(self, chunk: Dict[str, Any], query_payer: str, query_proc: str) -> bool:
        chunk_payer = chunk.get("payer", "") or ""
        payer_compat = False
        if query_payer and chunk_payer:
            if query_payer.lower() in chunk_payer.lower() or chunk_payer.lower() in query_payer.lower():
                payer_compat = True
        if not payer_compat:
            return False

        # Procedure compatibility is mandatory (domain-only is insufficient).
        return self._procedure_compatible(query_proc, chunk.get("procedure_codes") or [])

    def _procedure_compatible(self, query_proc: str, chunk_procs: List[Any]) -> bool:
        if not query_proc:
            return False
        for cp in chunk_procs:
            cp_str = str(cp).strip()
            if query_proc == cp_str.upper() or query_proc == cp_str:
                return True
            if "-" in cp_str and self._is_cpt_in_range(query_proc, cp_str):
                return True
        return False

    def _specificity_keywords(self, q_proc_clean: str) -> List[str]:
        def is_code_in_any_range(code: str, ranges: List[str]) -> bool:
            if code in ranges:
                return True
            for r in ranges:
                if "-" in r and self._is_cpt_in_range(code, r):
                    return True
            return False

        if is_code_in_any_range(q_proc_clean, ["27447", "27445", "27486", "27487"]):
            return ["knee"]
        if is_code_in_any_range(q_proc_clean, ["27130", "27132", "27134", "27137", "27138"]):
            return ["hip", "joint"]
        if is_code_in_any_range(q_proc_clean, ["33206", "33207", "33208"]):
            return ["pacemaker"]
        if is_code_in_any_range(q_proc_clean, ["33249", "33230", "33231", "33240", "33241"]):
            return ["defibrillator", "icd"]
        if is_code_in_any_range(q_proc_clean, ["77067", "77066", "77065", "76641", "76642", "77049"]):
            return ["breast", "mammography", "mammogram", "sonography"]
        if is_code_in_any_range(q_proc_clean, ["81528", "82270", "G0328", "G0327"]):
            return ["colorectal", "colon"]
        if is_code_in_any_range(q_proc_clean, ["78811", "78812", "78813", "78814", "78815", "78816", "A9552"]):
            return ["pet", "tomography", "oncologic"]
        return []

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
