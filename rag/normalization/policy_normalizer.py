import os
import json
import re
from typing import List, Dict, Any
from rag.normalization.input_normalizer import normalize_payer_name, normalize_policy_id, normalize_code

def extract_documentation_requirements(text: str) -> List[str]:
    """
    Deterministic rule-based documentation requirements extraction from text.
    """
    reqs = []
    text_lower = text.lower()
    
    # Check for specific documentation requirements
    if "imaging evidence" in text_lower or "radiographic evidence" in text_lower or "mri/ct" in text_lower:
        reqs.append("Imaging documentation")
    if "conservative treatment" in text_lower or "history of unsuccessful conservative" in text_lower:
        reqs.append("Conservative treatment history documentation")
    if "order" in text_lower or "ordered by the treating physician" in text_lower:
        reqs.append("Physician order documentation")
    if "clinical documentation" in text_lower or "clinical justification" in text_lower or "documented history" in text_lower:
        reqs.append("Clinical documentation")
    
    # If it's a general documentation policy (like L33950 associated articles)
    if "documentation" in text_lower and not reqs:
        reqs.append("Clinical documentation")
        
    return reqs

def extract_exclusions(text: str) -> List[str]:
    """
    Deterministic rule-based exclusion extraction from text.
    """
    exclusions = []
    text_lower = text.lower()
    
    if "not medically necessary in the presence of" in text_lower:
        # e.g., active joint/systemic infection
        match = re.search(r"not medically necessary in the presence of (.*?)(?:\.|$)", text, re.IGNORECASE)
        if match:
            exclusions.append(match.group(1).strip())
    if "not reasonable and necessary where there is" in text_lower:
        match = re.search(r"not reasonable and necessary where there is (.*?)(?:\.|$)", text, re.IGNORECASE)
        if match:
            exclusions.append(match.group(1).strip())
    if "not covered under age" in text_lower or "under age 35" in text_lower:
        exclusions.append("Under age 35")
    if "excludes patients with personal history" in text_lower:
        match = re.search(r"excludes patients with (.*?)(?:\.|$)", text, re.IGNORECASE)
        if match:
            exclusions.append(match.group(1).strip())
    
    # Generic "not covered" items
    if "not covered for" in text_lower:
        match = re.search(r"not covered for (.*?)(?:\.|$)", text, re.IGNORECASE)
        if match:
            exclusions.append(match.group(1).strip())
            
    return exclusions

def normalize_policies_dataset(raw_path: str, output_path: str):
    """
    Load raw policy dataset and transform it into the canonical schema.
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw dataset not found at {raw_path}")
        
    normalized_records = []
    
    with open(raw_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            
            # Map canonical fields
            chunk_id = record.get("chunk_id", f"UNKNOWN-{idx}")
            policy_id = normalize_policy_id(record.get("policy_id", "UNKNOWN"))
            payer = normalize_payer_name(record.get("payer", "UNKNOWN"))
            policy_title = record.get("policy_title", "").strip()
            clinical_domain = record.get("clinical_domain", "").strip().lower()
            
            procedure_codes = [normalize_code(c) for c in record.get("procedure_codes", [])]
            diagnosis_codes = [normalize_code(c) for c in record.get("diagnosis_codes", [])]
            
            section = record.get("section", "").strip()
            criterion_id = record.get("criterion_id", "").strip()
            criterion_type = record.get("criterion_type", "medical_necessity").strip().lower()
            criterion_name = record.get("criterion_name", "").strip()
            text = record.get("text", "").strip()
            
            # Rule-based extractors
            doc_reqs = extract_documentation_requirements(text)
            exclusions = extract_exclusions(text)
            
            # Additional keys
            limitations = []
            if "limit" in text.lower():
                # Simple heuristic extraction
                match = re.search(r"(?:limit|limitation)s?:?\s*(.*?)(?:\.|$)", text, re.IGNORECASE)
                if match:
                    limitations.append(match.group(1).strip())
                    
            contraindications = []
            if "contraindication" in text.lower() or "contraindicated" in text.lower():
                match = re.search(r"(?:contraindication|contraindicated)s?:?\s*(.*?)(?:\.|$)", text, re.IGNORECASE)
                if match:
                    contraindications.append(match.group(1).strip())
            
            source_ref = record.get("source_reference", {})
            policy_status = record.get("policy_status", "active").strip().lower()
            
            # Normalize dates
            effective_date = record.get("policy_last_review_date") or record.get("effective_date")
            revision_date = record.get("policy_anticipated_review_date") or record.get("revision_date")
            
            canonical_record = {
                "chunk_id": chunk_id,
                "policy_id": policy_id,
                "payer": payer,
                "policy_title": policy_title,
                "clinical_domain": clinical_domain,
                "procedure_codes": procedure_codes,
                "diagnosis_codes": diagnosis_codes,
                "section": section,
                "criterion_id": criterion_id,
                "criterion_type": criterion_type,
                "criterion_name": criterion_name,
                "text": text,
                "documentation_requirements": doc_reqs,
                "exclusions": exclusions,
                "limitations": limitations,
                "contraindications": contraindications,
                "source_reference": source_ref,
                "policy_status": policy_status,
                "effective_date": effective_date,
                "revision_date": revision_date
            }
            
            normalized_records.append(canonical_record)
            
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(normalized_records, out, indent=2)
        
    print(f"Policy normalization complete. Wrote {len(normalized_records)} records to {output_path}")
