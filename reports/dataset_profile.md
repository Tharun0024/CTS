# Dataset Profile Report

## File Details
* **Source Path**: `E:/RAG/data/raw/ragdata.jsonl`
* **Format**: `JSONL`
* **Total Chunks/Records**: `24`

## Discovered Fields/Schema Keys
`criterion_id`, `policy_anticipated_review_date`, `policy_title`, `text`, `chunk_id`, `policy_status`, `clinical_domain`, `diagnosis_codes`, `criterion_type`, `text_status`, `procedure_codes`, `payer`, `policy_last_review_date`, `criterion_name`, `section`, `source_reference`, `policy_id`

## Entity Distributions
* **Unique Policies**: 8
  * `NCD-220.6.17`, `LCD-L36575`, `NCD-20.8.3`, `LCD-L36039`, `NCD-220.4`, `NCD-20.4`, `NCD-210.3`, `LCD-L33950`
* **Unique Payers**: 1
  * `CMS (Medicare)`
* **Clinical Domains**: 5
  * `oncology/radiology`, `radiology/imaging`, `cardiology`, `orthopedics`, `oncology/preventive screening`
* **Procedure Codes (CPT)**: 35
  * `27130`, `27132`, `27134`, `27137`, `27138`, `27445`, `27447`, `27486`, `27487`, `33202-33273`, `33206`, `33207`, `33208`, `33230`, `33231`, `33240`, `33241`, `33249`, `76641`, `76642`, `77049`, `77065`, `77066`, `77067`, `78811-78813`, `78814-78816`, `78815`, `78816`, `81528`, `82270`, `A9552`, `C7537-C7540`, `G0327`, `G0328`, `G0448`
* **Diagnosis Codes (ICD-10)**: 22
  * `C18-C20`, `C34`, `C50`, `C53`, `I25.2`, `I25.5`, `I42.0`, `I42.6-I42.8`, `I44.1`, `I44.2`, `I47.2`, `I49.01`, `I49.5`, `I50`, `M16.0-M16.9`, `M17.0-M17.9`, `N63`, `R92`, `Z12.11`, `Z12.31`, `Z76.82`, `Z85.3`
* **Sections**: 3
  * `Key Clinical Thresholds`, `Coding Reference`, `Coverage Criteria`

## Text-Based Attribute References
* **Documentation references in text**: 1 chunks
* **Exclusion references in text**: 3 chunks
* **Limitation references in text**: 1 chunks
* **Contraindication references in text**: 1 chunks
