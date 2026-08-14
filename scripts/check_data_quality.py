import os
import json
import yaml

def main():
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    dataset_path = config["paths"]["raw_data"]
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    records = []
    malformed_lines = []
    
    # Read and check JSON structures
    with open(dataset_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append((idx, json.loads(line)))
            except Exception as e:
                malformed_lines.append({"line_number": idx, "error": str(e)})

    # Initialize quality metrics
    missing_policy_id = []
    missing_chunk_id = []
    empty_text = []
    missing_section = []
    duplicate_chunks = {}
    chunk_counts = {}
    inconsistent_payers = []
    malformed_codes = []
    
    for idx, r in records:
        chunk_id = r.get("chunk_id")
        policy_id = r.get("policy_id")
        text = r.get("text")
        section = r.get("section")
        payer = r.get("payer")
        proc_codes = r.get("procedure_codes", [])
        diag_codes = r.get("diagnosis_codes", [])
        
        # Missing critical fields
        if not chunk_id:
            missing_chunk_id.append(idx)
        else:
            chunk_counts[chunk_id] = chunk_counts.get(chunk_id, 0) + 1
            
        if not policy_id:
            missing_policy_id.append(idx)
            
        if not text or not str(text).strip():
            empty_text.append(chunk_id or f"Line {idx}")
            
        if not section:
            missing_section.append(chunk_id or f"Line {idx}")
            
        # Payer name validation (check for inconsistencies, expected 'CMS (Medicare)' or similar)
        if payer and payer not in ["CMS (Medicare)", "Aetna"]:
            # If there's some slight spelling variation
            inconsistent_payers.append({"chunk_id": chunk_id, "payer": payer})
            
        # Code format validation
        # CPT codes are typically 5-digit numbers or ranges/lists. Let's flag empty lists or empty strings.
        if not proc_codes:
            malformed_codes.append({"chunk_id": chunk_id, "type": "procedure_codes", "issue": "Empty list"})
        for code in proc_codes:
            if not isinstance(code, str) or not code.strip():
                malformed_codes.append({"chunk_id": chunk_id, "type": "procedure_codes", "issue": f"Invalid code format: {code}"})
                
        if not diag_codes:
            malformed_codes.append({"chunk_id": chunk_id, "type": "diagnosis_codes", "issue": "Empty list"})
        for code in diag_codes:
            if not isinstance(code, str) or not code.strip():
                malformed_codes.append({"chunk_id": chunk_id, "type": "diagnosis_codes", "issue": f"Invalid code format: {code}"})

    # Duplicate chunk ID calculations
    for cid, count in chunk_counts.items():
        if count > 1:
            duplicate_chunks[cid] = count

    quality_json = {
        "total_lines_read": len(records) + len(malformed_lines),
        "valid_json_records": len(records),
        "malformed_json_lines": malformed_lines,
        "missing_chunk_ids": missing_chunk_id,
        "missing_policy_ids": missing_policy_id,
        "empty_text_chunks": empty_text,
        "missing_sections": missing_section,
        "duplicate_chunk_ids": duplicate_chunks,
        "inconsistent_payers": inconsistent_payers,
        "malformed_codes": malformed_codes,
        "overall_health_status": "PASSED" if not (malformed_lines or missing_chunk_id or missing_policy_id or empty_text or duplicate_chunks) else "WARNING"
    }

    # Save reports
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "data_quality_report.json"), "w", encoding="utf-8") as out:
        json.dump(quality_json, out, indent=2)
        
    md_content = f"""# Data Quality Report

## Summary
* **Total Lines Analyzed**: {quality_json["total_lines_read"]}
* **Valid JSON Lines**: {quality_json["valid_json_records"]}
* **Malformed JSON Lines**: {len(malformed_json_lines := quality_json["malformed_json_lines"])}
* **Overall Status**: **{quality_json["overall_health_status"]}**

## Detailed Quality Issues

### 1. Missing Core Identifiers
* **Missing Chunk IDs**: {len(quality_json["missing_chunk_ids"])} lines {quality_json["missing_chunk_ids"]}
* **Missing Policy IDs**: {len(quality_json["missing_policy_ids"])} lines {quality_json["missing_policy_ids"]}

### 2. Duplicate Check
* **Duplicate Chunk IDs**: {len(quality_json["duplicate_chunk_ids"])}
{chr(10).join([f"  * `{cid}`: occurs {count} times" for cid, count in quality_json["duplicate_chunk_ids"].items()]) or "  * None"}

### 3. Missing Content
* **Empty Policy Text**: {len(quality_json["empty_text_chunks"])} chunks {quality_json["empty_text_chunks"]}
* **Missing Section Name**: {len(quality_json["missing_sections"])} chunks {quality_json["missing_sections"]}

### 4. Payer Consistency
* **Payer Inconsistencies**: {len(quality_json["inconsistent_payers"])}
{chr(10).join([f"  * Chunk `{item['chunk_id']}` has payer `{item['payer']}`" for item in quality_json["inconsistent_payers"]]) or "  * None"}

### 5. Clinical Codes Quality
* **Malformed CPT/ICD Codes**: {len(quality_json["malformed_codes"])} issues
{chr(10).join([f"  * Chunk `{item['chunk_id']}`: {item['type']} contains {item['issue']}" for item in quality_json["malformed_codes"]]) or "  * None"}
"""
    with open(os.path.join("reports", "data_quality_report.md"), "w", encoding="utf-8") as out:
        out.write(md_content)
        
    print("Data quality reports successfully generated.")

if __name__ == "__main__":
    main()
