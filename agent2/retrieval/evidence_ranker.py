import re
from typing import List
from schemas.evidence import Evidence

class EvidenceRanker:
    def __init__(self):
        pass

    def filter_and_rank(self, evidence_list: List[Evidence], policy_id: str) -> List[Evidence]:
        """Filters the master evidence list based on policy keywords to yield relevant candidates."""
        policy_id_lower = policy_id.lower()
        keywords = []

        # Determine keywords based on policy
        if "epogen" in policy_id_lower:
            keywords = [
                r"\banemia\b", r"\biron\b", r"\bferrous\b", r"\bhemoglobin\b", r"\bhb\b",
                r"\bblood pressure\b", r"\bsystolic\b", r"\bdiastolic\b", r"\bhypertension\b",
                r"\b718-7\b", r"\b271737000\b"
            ]
        elif "humulin" in policy_id_lower:
            keywords = [
                r"\bdiabetes\b", r"\btype 2\b", r"\bmetformin\b", r"\bhba1c\b", 
                r"\bglycated hemoglobin\b", r"\b4548-4\b", r"\b44054006\b"
            ]
        elif "repatha" in policy_id_lower:
            keywords = [
                r"\bhyperlipidemia\b", r"\bldl\b", r"\bcholesterol\b", r"\bstatin\b",
                r"\bsimvastatin\b", r"\batorvastatin\b", r"\brosuvastatin\b",
                r"\bcardiolog\b", r"\bendocrinolog\b", r"\b18262-6\b", r"\b166110001\b"
            ]
        elif "l36575" in policy_id_lower or "knee" in policy_id_lower or "l36039" in policy_id_lower:
            keywords = [
                r"\bknee\b", r"\barthritis\b", r"\bosteoarthritis\b", r"\barthroplasty\b",
                r"\bjoint\b", r"\bphysical therapy\b", r"\btherapy\b", r"\bx-ray\b", r"\bxray\b",
                r"\bradiograph\b", r"\bmri\b", r"\bct\b", r"\binfection\b", r"\bwound\b",
                r"\bneurolog\b", r"\bm17\b", r"\b27447\b"
            ]
        else:
            # Fallback: keep all conditions and observations if policy is unknown
            return [ev for ev in evidence_list if ev.evidence_type in ["CLINICAL", "LAB", "MEDICATION"]]

        # Compiling regex patterns
        compiled_patterns = [re.compile(kw, re.IGNORECASE) for kw in keywords]

        filtered_evidence = []
        for ev in evidence_list:
            match = False
            for pattern in compiled_patterns:
                if pattern.search(ev.content):
                    match = True
                    break
            
            # Keep all documents as they might contain notes, but rank them
            if ev.source_type == "documents":
                ev.relevance_score = 0.5
                filtered_evidence.append(ev)
            elif match:
                ev.relevance_score = 1.0
                filtered_evidence.append(ev)

        # Sort by relevance score, and then by date descending
        filtered_evidence.sort(key=lambda x: (x.relevance_score, x.event_date), reverse=True)
        return filtered_evidence
