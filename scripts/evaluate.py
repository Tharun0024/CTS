import os
import time
import json
import yaml
import numpy as np
from typing import List, Dict, Any

from src.schema.models import ClaimInput
from src.normalization.input_normalizer import normalize_claim_input
from src.query_builder.query_builder import QueryBuilder
from src.retrieval.exact_matcher import ExactMatcher
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.faiss_retriever import FAISSRetriever
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.candidate_pool import CandidatePool
from src.reranking.bge_reranker import BGEReranker
from src.aggregation.policy_aggregator import PolicyAggregator

def main():
    print("Initializing components for evaluation...")
    
    # 1. Load config
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    # 2. Load chunk database
    processed_chunks_path = config["paths"]["processed_chunks"]
    with open(processed_chunks_path, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)
    all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}
    
    # 3. Instantiate pipeline elements
    qb = QueryBuilder()
    em = ExactMatcher(all_chunks)
    embedder = BGEEmbedder(
        model_name=config["embedding_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    faiss_ret = FAISSRetriever(index_dir=config["paths"]["vector_store"])
    faiss_ret.load()
    
    bm25_ret = BM25Retriever(index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl"))
    bm25_ret.load()
    
    pool = CandidatePool()
    reranker = BGEReranker(
        model_name=config["reranker_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    agg = PolicyAggregator()
    
    # 4. Define evaluation cases
    eval_cases = [
        # Pacemaker - NCD-20.8.3
        {
            "id": "pacemaker_exact",
            "claim": {
                "claim_id": "VAL-PM-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-20.8.3"}},
                "diagnosis": [{"code": "I49.5", "description": "Sick sinus syndrome"}],
                "procedure": {"code": "33206", "description": "Insertion of permanent pacemaker"},
                "clinical_domain": "cardiology"
            },
            "expected_policy": "NCD-20.8.3"
        },
        {
            "id": "pacemaker_no_id",
            "claim": {
                "claim_id": "VAL-PM-02",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "I49.5", "description": "Sick sinus syndrome"}],
                "procedure": {"code": "33206", "description": "Insertion of permanent pacemaker"},
                "clinical_domain": "cardiology"
            },
            "expected_policy": "NCD-20.8.3"
        },
        {
            "id": "pacemaker_semantic",
            "claim": {
                "claim_id": "VAL-PM-03",
                "insurance": {"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
                "diagnosis": [{"code": "I44.2", "description": "Atrioventricular block, complete"}],
                "procedure": {"code": "33207", "description": "Implantation of cardiac battery and lead generator for bradycardia"},
                "clinical_domain": "cardiology"
            },
            "expected_policy": "NCD-20.8.3"
        },
        
        # ICD - NCD-20.4
        {
            "id": "icd_exact",
            "claim": {
                "claim_id": "VAL-ICD-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-20.4"}},
                "diagnosis": [{"code": "I47.2", "description": "Ventricular tachycardia"}],
                "procedure": {"code": "33249", "description": "Insertion or replacement of electrode lead for defibrillator"},
                "clinical_domain": "cardiology"
            },
            "expected_policy": "NCD-20.4"
        },
        {
            "id": "icd_no_id",
            "claim": {
                "claim_id": "VAL-ICD-02",
                "insurance": {"primary": {"payer": "CMS Medicare", "policy_id": None}},
                "diagnosis": [{"code": "I49.01", "description": "Ventricular fibrillation"}],
                "procedure": {"code": "33249", "description": "Placement of cardiorhythmical defibrillator device"},
                "clinical_domain": "cardiology"
            },
            "expected_policy": "NCD-20.4"
        },
        
        # Mammogram - NCD-220.4
        {
            "id": "mammogram_exact",
            "claim": {
                "claim_id": "VAL-MAM-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-220.4"}},
                "diagnosis": [{"code": "Z12.31", "description": "Encounter for screening mammogram for malignant neoplasm of breast"}],
                "procedure": {"code": "77067", "description": "Screening mammography, bilateral"},
                "clinical_domain": "radiology/imaging"
            },
            "expected_policy": "NCD-220.4"
        },
        {
            "id": "mammogram_no_id",
            "claim": {
                "claim_id": "VAL-MAM-02",
                "insurance": {"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
                "diagnosis": [{"code": "Z12.31", "description": "Screening for breast cancer"}],
                "procedure": {"code": "77067", "description": "Bilateral screening mammography"},
                "clinical_domain": "radiology/imaging"
            },
            "expected_policy": "NCD-220.4"
        },
        
        # Colorectal Cancer Screening - NCD-210.3
        {
            "id": "colorectal_exact",
            "claim": {
                "claim_id": "VAL-COL-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-210.3"}},
                "diagnosis": [{"code": "Z12.11", "description": "Encounter for screening for malignant neoplasm of colon"}],
                "procedure": {"code": "81528", "description": "Oncology (colorectal) screening (e.g. Cologuard)"},
                "clinical_domain": "oncology/preventive screening"
            },
            "expected_policy": "NCD-210.3"
        },
        {
            "id": "colorectal_no_id",
            "claim": {
                "claim_id": "VAL-COL-02",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "Z12.11", "description": "Screening colon neoplasm"}],
                "procedure": {"code": "81528", "description": "Stool DNA test for colorectal screening"},
                "clinical_domain": "oncology/preventive screening"
            },
            "expected_policy": "NCD-210.3"
        },
        
        # Positron Emission Tomography (FDG) - NCD-220.6.17
        {
            "id": "pet_exact",
            "claim": {
                "claim_id": "VAL-PET-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-220.6.17"}},
                "diagnosis": [{"code": "C34", "description": "Malignant neoplasm of bronchus and lung"}],
                "procedure": {"code": "78815", "description": "Positron emission tomography (PET) with concurrently acquired computed tomography (CT)"},
                "clinical_domain": "oncology/radiology"
            },
            "expected_policy": "NCD-220.6.17"
        },
        {
            "id": "pet_no_id",
            "claim": {
                "claim_id": "VAL-PET-02",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "C50", "description": "Malignant neoplasm of breast"}],
                "procedure": {"code": "78815", "description": "FDG PET scan for tumor imaging"},
                "clinical_domain": "oncology/radiology"
            },
            "expected_policy": "NCD-220.6.17"
        },
        
        # Knee Arthroplasty - LCD-L36575
        {
            "id": "knee_exact",
            "claim": {
                "claim_id": "VAL-KNEE-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "LCD-L36575"}},
                "diagnosis": [{"code": "M17.11", "description": "Unilateral primary osteoarthritis, right knee"}],
                "procedure": {"code": "27447", "description": "Arthroplasty, knee, condyle and plateau; medial and lateral compartments (total knee arthroplasty)"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36575"
        },
        {
            "id": "knee_no_id",
            "claim": {
                "claim_id": "VAL-KNEE-02",
                "insurance": {"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
                "diagnosis": [{"code": "M17.11", "description": "Degenerative osteoarthritis of the right knee joint"}],
                "procedure": {"code": "27447", "description": "Surgical replacement of right knee joint"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36575"
        },
        
        # Hip/Joint Arthroplasty - LCD-L36039
        {
            "id": "hip_exact",
            "claim": {
                "claim_id": "VAL-HIP-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "LCD-L36039"}},
                "diagnosis": [{"code": "M16.11", "description": "Unilateral primary osteoarthritis, right hip"}],
                "procedure": {"code": "27130", "description": "Arthroplasty, acetabular and proximal femoral prosthetic replacement (total hip arthroplasty)"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36039"
        },
        {
            "id": "hip_no_id",
            "claim": {
                "claim_id": "VAL-HIP-02",
                "insurance": {"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
                "diagnosis": [{"code": "M16.11", "description": "Right hip joint osteoarthritis"}],
                "procedure": {"code": "27130", "description": "Total hip joint replacement surgery"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36039"
        },
        
        # Breast Imaging Sonography/MRI/Mammography - LCD-L33950
        {
            "id": "breast_imaging_exact",
            "claim": {
                "claim_id": "VAL-BI-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "LCD-L33950"}},
                "diagnosis": [{"code": "N63", "description": "Unspecified breast lump"}],
                "procedure": {"code": "76641", "description": "Ultrasound, breast, unilateral, real time with image documentation, complete"},
                "clinical_domain": "radiology/imaging"
            },
            "expected_policy": "LCD-L33950"
        },
        {
            "id": "breast_imaging_no_id",
            "claim": {
                "claim_id": "VAL-BI-02",
                "insurance": {"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
                "diagnosis": [{"code": "N63", "description": "Breast mass found on clinical exam"}],
                "procedure": {"code": "76641", "description": "Unilateral breast ultrasound"},
                "clinical_domain": "radiology/imaging"
            },
            "expected_policy": "LCD-L33950"
        },
        
        # Hard Negatives
        {
            "id": "hard_neg_knee_vs_hip",
            "claim": {
                "claim_id": "VAL-HN-KNEE",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "M17.11", "description": "Knee osteoarthritis"}],
                "procedure": {"code": "27447", "description": "Total knee replacement"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36575" # Ortho Knee (L36575) and NOT General Arthroplasty (L36039)
        },
        {
            "id": "hard_neg_hip_vs_knee",
            "claim": {
                "claim_id": "VAL-HN-HIP",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "M16.11", "description": "Hip osteoarthritis"}],
                "procedure": {"code": "27130", "description": "Total hip replacement"},
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36039" # General Joint (covers hip)
        },
        
        # Conflict cases (policy ID mismatch but clinical parameters override or reject)
        {
            "id": "conflict_case",
            "claim": {
                "claim_id": "VAL-CONF-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": "NCD-20.8.3"}}, # Mismatch policy id (pacemaker)
                "diagnosis": [{"code": "M16.11", "description": "Hip osteoarthritis"}],
                "procedure": {"code": "27130", "description": "Total hip replacement"}, # Ortho procedure
                "clinical_domain": "orthopedics"
            },
            "expected_policy": "LCD-L36039" # Correct policy matching clinical parameters
        },
        
        # Unknown case
        {
            "id": "unknown_case",
            "claim": {
                "claim_id": "VAL-UNK-01",
                "insurance": {"primary": {"payer": "CMS", "policy_id": None}},
                "diagnosis": [{"code": "ZZ999", "description": "Unknown disease code"}],
                "procedure": {"code": "99999", "description": "Unknown procedure code"},
                "clinical_domain": "neurology"
            },
            "expected_policy": "NO_RELIABLE_POLICY_MATCH"
        }
    ]
    
    results = []
    
    recalls_1 = 0
    recalls_3 = 0
    recalls_5 = 0
    mrr_sum = 0.0
    accuracy_count = 0
    contamination_failures = 0
    
    total_cases = len(eval_cases)
    
    for case in eval_cases:
        case_id = case["id"]
        expected = case["expected_policy"]
        claim_raw = case["claim"]
        
        claim_input = ClaimInput(**claim_raw)
        
        # Step 1. Input Normalization
        norm_claim = normalize_claim_input(claim_input)
        
        # Step 2. Query Builder
        queries = qb.build_query(norm_claim)
        
        # Step 3. Three-Way Retrieval
        exact_matches = em.retrieve(queries["structured"])
        query_vector = embedder.embed_query(queries["semantic_query"])
        faiss_matches = faiss_ret.retrieve(query_vector, top_k=config["candidate_pool_size"])
        bm25_matches = bm25_ret.retrieve(queries["bm25_query"], top_k=config["candidate_pool_size"])
        
        # Step 4. Candidate Pool Merging
        top_candidates = pool.merge(
            exact_matches,
            faiss_matches,
            bm25_matches,
            all_chunks_dict
        )
        
        # Step 5. Reranking
        reranked_candidates = reranker.rerank(queries["semantic_query"], top_candidates)
        
        # Step 6. Policy Aggregator
        selected_policy, aggregated_chunks, best_score = agg.aggregate(
            reranked_candidates,
            all_chunks,
            norm_claim.insurance.primary.payer,
            norm_claim.procedure.code,
            norm_claim.clinical_domain
        )
        
        # Calculate retrieval rank of the expected policy in reranked candidates list
        retrieved_policies = []
        seen = set()
        for cand in reranked_candidates:
            pid = cand["policy_id"]
            if pid not in seen:
                seen.add(pid)
                retrieved_policies.append(pid)
                
        rank = -1
        if expected != "NO_RELIABLE_POLICY_MATCH" and expected in retrieved_policies:
            rank = retrieved_policies.index(expected) + 1
            
        # Metrics update
        is_rec_1 = False
        is_rec_3 = False
        is_rec_5 = False
        mrr = 0.0
        
        if expected == "NO_RELIABLE_POLICY_MATCH":
            is_rec_1 = (selected_policy == "NO_RELIABLE_POLICY_MATCH")
            is_rec_3 = (selected_policy == "NO_RELIABLE_POLICY_MATCH")
            is_rec_5 = (selected_policy == "NO_RELIABLE_POLICY_MATCH")
            mrr = 1.0 if selected_policy == "NO_RELIABLE_POLICY_MATCH" else 0.0
        else:
            if rank != -1:
                if rank <= 1:
                    is_rec_1 = True
                if rank <= 3:
                    is_rec_3 = True
                if rank <= 5:
                    is_rec_5 = True
                mrr = 1.0 / rank
                
        if is_rec_1: recalls_1 += 1
        if is_rec_3: recalls_3 += 1
        if is_rec_5: recalls_5 += 1
        mrr_sum += mrr
        
        is_correct = (selected_policy == expected) or (case_id == "conflict_case" and selected_policy in ["LCD-L36039", "NO_RELIABLE_POLICY_MATCH"])
        if is_correct:
            accuracy_count += 1
            
        # Check contamination
        contaminated = False
        contamination_rate = 0.0
        if selected_policy != "NO_RELIABLE_POLICY_MATCH" and aggregated_chunks:
            non_matching_chunks = [c for c in aggregated_chunks if c["policy_id"] != selected_policy]
            if non_matching_chunks:
                contaminated = True
                contamination_failures += 1
                contamination_rate = len(non_matching_chunks) / len(aggregated_chunks)
                
        results.append({
            "case_id": case_id,
            "expected_policy": expected,
            "retrieved_policies": retrieved_policies[:5],
            "rank_found": rank if rank != -1 else "not found",
            "selected_policy": selected_policy,
            "aggregator_match": is_correct,
            "relevance_score": best_score,
            "contaminated": contaminated,
            "contamination_rate": contamination_rate
        })
        
        print(f"Case: {case_id:25} | Expected: {expected:15} | Selected: {selected_policy:15} | Match: {str(is_correct):5} | Contaminated: {str(contaminated)}")

    # Summary metrics
    final_recall_1 = recalls_1 / total_cases
    final_recall_3 = recalls_3 / total_cases
    final_recall_5 = recalls_5 / total_cases
    final_mrr = mrr_sum / total_cases
    final_accuracy = accuracy_count / total_cases
    final_contamination_rate = contamination_failures / total_cases
    
    evaluation_json = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_test_cases": total_cases,
        "metrics": {
            "recall_at_1": final_recall_1,
            "recall_at_3": final_recall_3,
            "recall_at_5": final_recall_5,
            "mean_reciprocal_rank": final_mrr,
            "policy_match_accuracy": final_accuracy,
            "cross_policy_contamination_rate": final_contamination_rate
        },
        "results": results
    }
    
    # Save reports
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "evaluation_report.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation_json, f, indent=2)
        
    md_report = f"""# Prior Authorization Retrieval RAG Evaluation Report

Generated: {evaluation_json["timestamp"]}

## Summary Metrics

| Metric | Target Value | Measured Value | Status |
|---|---|---|---|
| **Recall@1** | >= 0.85 | {final_recall_1:.4f} | {"PASSED" if final_recall_1 >= 0.85 else "WARNING"} |
| **Recall@3** | >= 0.90 | {final_recall_3:.4f} | {"PASSED" if final_recall_3 >= 0.90 else "WARNING"} |
| **Recall@5** | >= 0.95 | {final_recall_5:.4f} | {"PASSED" if final_recall_5 >= 0.95 else "WARNING"} |
| **Mean Reciprocal Rank (MRR)** | >= 0.90 | {final_mrr:.4f} | {"PASSED" if final_mrr >= 0.90 else "WARNING"} |
| **Policy Match Accuracy** | >= 0.95 | {final_accuracy:.4f} | {"PASSED" if final_accuracy >= 0.95 else "WARNING"} |
| **Cross-Policy Contamination** | 0.00% | {final_contamination_rate * 100:.2f}% | {"PASSED" if final_contamination_rate == 0.0 else "FAILED"} |

## Evaluation Test Cases Detail

| Case ID | Expected Policy | Selected Policy | Match? | Contaminated? | Score |
|---|---|---|---|---|---|
"""
    for res in results:
        match_str = "✅ Yes" if res["aggregator_match"] else "❌ No"
        cont_str = "❌ Yes" if res["contaminated"] else "✅ No (0%)"
        md_report += f"| `{res['case_id']}` | `{res['expected_policy']}` | `{res['selected_policy']}` | {match_str} | {cont_str} | {res['relevance_score']:.4f} |\n"
        
    with open(os.path.join("reports", "evaluation_report.md"), "w", encoding="utf-8") as f:
        f.write(md_report)
        
    print("\nEvaluation completed successfully. Reports generated under reports/evaluation_report.json and reports/evaluation_report.md.")

if __name__ == "__main__":
    main()
