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
    is_jsonl = False
    
    # Check format (JSON or JSONL)
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            first_char = f.read(1)
            f.seek(0)
            if first_char == "[":
                records = json.load(f)
                is_jsonl = False
            else:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
                is_jsonl = True
    except Exception as e:
        print(f"Failed to read dataset: {e}")
        return

    total_records = len(records)
    
    # Discover keys
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())
        
    # Analyze records
    unique_policies = set()
    unique_payers = set()
    unique_domains = set()
    procedure_codes = set()
    diagnosis_codes = set()
    criterion_ids = set()
    sections = set()
    
    doc_req_count = 0
    exclusions_count = 0
    limitations_count = 0
    contraindications_count = 0

    for r in records:
        if "policy_id" in r:
            unique_policies.add(r["policy_id"])
        if "payer" in r:
            unique_payers.add(r["payer"])
        if "clinical_domain" in r:
            unique_domains.add(r["clinical_domain"])
        if "procedure_codes" in r:
            for code in r["procedure_codes"]:
                procedure_codes.add(code)
        if "diagnosis_codes" in r:
            for code in r["diagnosis_codes"]:
                diagnosis_codes.add(code)
        if "criterion_id" in r:
            criterion_ids.add(r["criterion_id"])
        if "section" in r:
            sections.add(r["section"])
            
        # Inspect for explicit list fields or text-based indicators
        text_lower = r.get("text", "").lower()
        if "documentation" in text_lower:
            doc_req_count += 1
        if "exclude" in text_lower or "exclusion" in text_lower:
            exclusions_count += 1
        if "limit" in text_lower or "limitation" in text_lower:
            limitations_count += 1
        if "contraindication" in text_lower or "contraindicated" in text_lower:
            contraindications_count += 1
            
    # Gather statistics
    profile_json = {
        "file_format": "JSONL" if is_jsonl else "JSON Array",
        "total_records": total_records,
        "unique_policies_count": len(unique_policies),
        "unique_policies": list(unique_policies),
        "unique_payers_count": len(unique_payers),
        "unique_payers": list(unique_payers),
        "unique_domains_count": len(unique_domains),
        "unique_domains": list(unique_domains),
        "procedure_codes_count": len(procedure_codes),
        "procedure_codes": list(procedure_codes),
        "diagnosis_codes_count": len(diagnosis_codes),
        "diagnosis_codes": list(diagnosis_codes),
        "unique_sections_count": len(sections),
        "unique_sections": list(sections),
        "criterion_ids_count": len(criterion_ids),
        "text_based_indicators": {
            "chunks_referencing_documentation": doc_req_count,
            "chunks_referencing_exclusions": exclusions_count,
            "chunks_referencing_limitations": limitations_count,
            "chunks_referencing_contraindications": contraindications_count
        },
        "fields_discovered": list(all_keys)
    }
    
    # Save JSON report
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "dataset_profile.json"), "w", encoding="utf-8") as out:
        json.dump(profile_json, out, indent=2)
        
    # Save Markdown report
    md_content = f"""# Dataset Profile Report

## File Details
* **Source Path**: `{dataset_path}`
* **Format**: `{profile_json["file_format"]}`
* **Total Chunks/Records**: `{profile_json["total_records"]}`

## Discovered Fields/Schema Keys
{", ".join([f"`{k}`" for k in profile_json["fields_discovered"]])}

## Entity Distributions
* **Unique Policies**: {profile_json["unique_policies_count"]}
  * {", ".join([f"`{p}`" for p in profile_json["unique_policies"]])}
* **Unique Payers**: {profile_json["unique_payers_count"]}
  * {", ".join([f"`{pay}`" for pay in profile_json["unique_payers"]])}
* **Clinical Domains**: {profile_json["unique_domains_count"]}
  * {", ".join([f"`{d}`" for d in profile_json["unique_domains"]])}
* **Procedure Codes (CPT)**: {profile_json["procedure_codes_count"]}
  * {", ".join([f"`{c}`" for c in sorted(profile_json["procedure_codes"])])}
* **Diagnosis Codes (ICD-10)**: {profile_json["diagnosis_codes_count"]}
  * {", ".join([f"`{c}`" for c in sorted(profile_json["diagnosis_codes"])])}
* **Sections**: {profile_json["unique_sections_count"]}
  * {", ".join([f"`{s}`" for s in profile_json["unique_sections"]])}

## Text-Based Attribute References
* **Documentation references in text**: {doc_req_count} chunks
* **Exclusion references in text**: {exclusions_count} chunks
* **Limitation references in text**: {limitations_count} chunks
* **Contraindication references in text**: {contraindications_count} chunks
"""
    with open(os.path.join("reports", "dataset_profile.md"), "w", encoding="utf-8") as out:
        out.write(md_content)
        
    print("Dataset profile reports successfully generated.")

if __name__ == "__main__":
    main()
