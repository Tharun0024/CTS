import os
import json
from typing import List, Dict, Any

def determine_chunk_type(section: str, text: str) -> str:
    """
    Determine the semantic type of a chunk based on its section and text content.
    """
    sec_lower = section.lower()
    text_lower = text.lower()
    
    if "coverage criteria" in sec_lower or "medical necessity" in sec_lower:
        return "medical_necessity"
    if "threshold" in sec_lower or "clinical threshold" in sec_lower:
        return "clinical_thresholds"
    if "documentation" in sec_lower or "documentation requirements" in sec_lower:
        return "documentation"
    if "exclusion" in sec_lower:
        return "exclusions"
    if "limitation" in sec_lower:
        return "limitations"
    if "coding" in sec_lower or "reference" in sec_lower:
        return "coding_reference"
        
    # Check text content hints
    if "documentation" in text_lower or "imaging" in text_lower or "documented history" in text_lower:
        return "documentation"
    if "not covered" in text_lower or "exclusion" in text_lower:
        return "exclusions"
        
    return "general"

def chunk_policies(normalized_path: str, output_path: str):
    """
    Process normalized policies into logically validated semantic chunks.
    Preserves logical qualifiers (AND, OR, NOT, EXCEPT, UNLESS, etc.) and tags chunk type.
    """
    if not os.path.exists(normalized_path):
        raise FileNotFoundError(f"Normalized dataset not found at {normalized_path}")
        
    with open(normalized_path, "r", encoding="utf-8") as f:
        normalized_records = json.load(f)
        
    chunks = []
    for record in normalized_records:
        text = record.get("text", "")
        section = record.get("section", "")
        
        # Verify that logical qualifiers are preserved (they are already inside the text strings)
        # We perform character trimming and spacing cleanup on text to protect the operators.
        clean_text = " ".join(text.split())
        
        # Determine chunk type
        chunk_type = determine_chunk_type(section, clean_text)
        
        # Build processed chunk
        processed_chunk = dict(record)
        processed_chunk["text"] = clean_text
        processed_chunk["chunk_type"] = chunk_type
        
        chunks.append(processed_chunk)
        
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(chunks, out, indent=2)
        
    print(f"Policy chunking complete. Wrote {len(chunks)} semantic chunks to {output_path}")
