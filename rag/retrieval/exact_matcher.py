from typing import List, Dict, Any

class ExactMatcher:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        
    def match_code(self, code_pattern: str, code_list: List[str]) -> bool:
        """
        Check if a code pattern (like 'M17.0-M17.9' or '33202-33273') matches the target code list.
        Or if a specific code in the target list falls within the range/pattern.
        """
        for code in code_list:
            # Direct match
            if code == code_pattern:
                return True
            # Check range if pattern contains a dash (e.g. 'M17.0-M17.9' or '33202-33273')
            if "-" in code_pattern:
                try:
                    # Check if it's an ICD-10 range (alphanumeric prefix + number)
                    # e.g., 'M17.0-M17.9' vs 'M17.11'
                    match_range = re_parse_range(code_pattern)
                    if match_range and is_code_in_range(code, match_range):
                        return True
                except:
                    pass
            # Reverse check: if the chunk code contains a dash/range, does the claim code fall inside it?
            for chunk_code in code_list:
                if "-" in chunk_code:
                    try:
                        match_range = re_parse_range(chunk_code)
                        if match_range and is_code_in_range(code_pattern, match_range):
                            return True
                    except:
                        pass
        return False

    def retrieve(self, structured_query: Dict[str, Any], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Calculate exact match overlap scores for all chunks.
        Returns list of chunks with exact match score.
        """
        query_payer = structured_query.get("payer")
        query_policy_id = structured_query.get("policy_id")
        query_domain = structured_query.get("clinical_domain")
        query_proc = structured_query.get("procedure_code")
        query_diags = structured_query.get("diagnosis_codes", [])
        
        matches = []
        
        for chunk in self.chunks:
            score = 0.0
            
            # 1. Payer Match
            chunk_payer = chunk.get("payer")
            if chunk_payer and query_payer:
                # Case insensitive substring check or exact check after normalization
                if query_payer.lower() in chunk_payer.lower() or chunk_payer.lower() in query_payer.lower():
                    score += 1.0
            
            # 2. Policy ID Match (if provided in claim)
            chunk_policy_id = chunk.get("policy_id")
            if query_policy_id and chunk_policy_id:
                if query_policy_id.lower() == chunk_policy_id.lower():
                    score += 3.0
                    
            # 3. Clinical Domain Match
            chunk_domain = chunk.get("clinical_domain")
            if chunk_domain and query_domain:
                if query_domain.lower() == chunk_domain.lower():
                    score += 0.5
                    
            # 4. Procedure Code Match
            chunk_procs = chunk.get("procedure_codes", [])
            proc_matched = False
            if query_proc:
                if query_proc in chunk_procs:
                    score += 2.0
                    proc_matched = True
                else:
                    # Range check
                    for chunk_proc in chunk_procs:
                        if "-" in chunk_proc:
                            if self._is_cpt_in_range(query_proc, chunk_proc):
                                score += 2.0
                                proc_matched = True
                                break
                                
            # 5. Diagnosis Code Match
            chunk_diags = chunk.get("diagnosis_codes", [])
            diag_matched = False
            for query_diag in query_diags:
                if query_diag in chunk_diags:
                    score += 1.5
                    diag_matched = True
                else:
                    # Range check
                    for chunk_diag in chunk_diags:
                        if "-" in chunk_diag:
                            if self._is_icd_in_range(query_diag, chunk_diag):
                                score += 1.5
                                diag_matched = True
                                break
            
            # Normalize score
            # Max possible score = 1.0 (payer) + 3.0 (policy) + 0.5 (domain) + 2.0 (proc) + 1.5 (diag) = 8.0
            # If policy ID is not provided, max possible score = 5.0
            max_score = 8.0 if query_policy_id else 5.0
            normalized_score = min(score / max_score, 1.0)
            
            if normalized_score > 0:
                matches.append({
                    "chunk": chunk,
                    "score": normalized_score,
                    "proc_matched": proc_matched,
                    "diag_matched": diag_matched
                })
                
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_k]

    def _is_cpt_in_range(self, cpt: str, cpt_range: str) -> bool:
        """
        Checks if a CPT code falls in a range e.g., '33202-33273'.
        """
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

    def _is_icd_in_range(self, icd: str, icd_range: str) -> bool:
        """
        Checks if an ICD code matches a range e.g., 'M17.0-M17.9' for 'M17.11'.
        """
        # Strip dots for comparison
        icd_clean = icd.replace(".", "").strip().upper()
        parts = icd_range.split("-")
        if len(parts) == 2:
            start_prefix = re_get_alpha_prefix(parts[0])
            end_prefix = re_get_alpha_prefix(parts[1])
            icd_prefix = re_get_alpha_prefix(icd)
            
            if start_prefix == end_prefix == icd_prefix:
                try:
                    start_num = float(re_get_digits(parts[0]))
                    end_num = float(re_get_digits(parts[1]))
                    # Pad/truncate ICD to match precision
                    icd_num_str = re_get_digits(icd)
                    if len(icd_num_str) > len(str(int(start_num))) + 1:
                        # truncate if subcode
                        icd_num = float(icd_num_str[:len(str(int(start_num)))+1])
                    else:
                        icd_num = float(icd_num_str)
                    return start_num <= icd_num <= end_num
                except:
                    pass
        return False

def re_get_alpha_prefix(s: str) -> str:
    """Extract alphabetical prefix, e.g., 'M17.0' -> 'M'"""
    match = re.match(r"^([a-zA-Z]+)", s.strip())
    return match.group(1).upper() if match else ""

def re_get_digits(s: str) -> str:
    """Extract numeric part, e.g., 'M17.0' -> '170'"""
    cleaned = s.replace(".", "").strip()
    match = re.search(r"(\d+)", cleaned)
    return match.group(1) if match else "0"

import re
