import json
from typing import Any, Dict, Optional

from models.rag_models import ClaimInput
from adapters.rag_adapter import rag_claim_adapter, rag_policy_adapter
from adapters.runtime_adapter import RuntimeAdapter
from rag.normalization.input_normalizer import normalize_claim_input
from decision.schemas import DecisionResponse, DecisionOutcome
from decision.agent import DecisionAgent

def run_integrated_pipeline(canonical_claim: Dict[str, Any], components: Dict[str, Any]) -> Any:
    """
    Executes the end-to-end integrated flow (Constraint 1-16):
    Canonical Claim -> rag_claim_adapter -> RAG Pipeline -> rag_policy_adapter -> Agent 1 evaluate_canonical_claim -> DecisionResponse
    """
    try:
        # 1. Canonical Claim to RAG inputs list (supports multiple procedures, Constraint 3 & 6)
        rag_inputs = rag_claim_adapter(canonical_claim)
        
        # 2. Run RAG pipeline for each input and collect ClaimOutputs (Constraint 4)
        claim_outputs = []
        for inp_dict in rag_inputs:
            try:
                # Convert dict to ClaimInput model
                claim_input = ClaimInput(**inp_dict)
                
                # Run existing RAG pipeline using the components
                # A. Input Normalization
                norm_claim = normalize_claim_input(claim_input)
                
                # B. Query Builder
                queries = components["query_builder"].build_query(norm_claim)
                
                # C. Three-Way Retrieval
                exact_res = components["exact_matcher"].retrieve(queries["structured"])
                
                # Handle potential RAG retrieval failures safely (Constraint 9)
                query_vector = components["bge_embedder"].embed_query(queries["semantic_query"])
                faiss_res = components["faiss_retriever"].retrieve(
                    query_vector, top_k=components["config"]["candidate_pool_size"]
                )
                
                bm25_res = components["bm25_retriever"].retrieve(
                    queries["bm25_query"], top_k=components["config"]["candidate_pool_size"]
                )
                
                # D. Merge candidates
                candidates = components["candidate_pool"].merge(
                    exact_res, faiss_res, bm25_res, components["all_chunks_dict"]
                )
                
                # E. Reranking
                reranked = components["bge_reranker"].rerank(queries["semantic_query"], candidates)
                
                # F. Aggregate Policy (procedure-required; honor claim policy_id or fail closed)
                requested_policy_id = norm_claim.insurance.primary.policy_id or None
                selected_policy_id, aggregated_chunks, best_score = components["policy_aggregator"].aggregate(
                    reranked,
                    components["all_chunks"],
                    norm_claim.insurance.primary.payer,
                    norm_claim.procedure.code,
                    norm_claim.clinical_domain,
                    requested_policy_id=requested_policy_id,
                )
                
                if selected_policy_id == "NO_RELIABLE_POLICY_MATCH" or not aggregated_chunks:
                    # RAG did not find a policy match for this procedure, fail safely
                    if requested_policy_id:
                        print(
                            f"[RAG Integration] Requested policy '{requested_policy_id}' "
                            f"unavailable or procedure-incompatible for claim {norm_claim.claim_id}; "
                            "no substitution."
                        )
                    continue
                    
                # G. Analyze Chunks
                analyzer_output = components["deterministic_analyzer"].analyze_chunks(aggregated_chunks)
                
                # H. Build Evidence
                evidence_obj = components["evidence_builder"].build_evidence(
                    selected_policy_id,
                    norm_claim.insurance.primary.payer,
                    analyzer_output,
                    aggregated_chunks
                )
                
                # I. LLM formatting
                prompt = components["prompt_builder"].build_prompt(norm_claim.model_dump(), evidence_obj)
                llm_response = components["llm_client"].generate_claim_output(
                    claim_id=norm_claim.claim_id,
                    policy_id=selected_policy_id,
                    payer=norm_claim.insurance.primary.payer,
                    relevance_score=best_score,
                    evidence_object=evidence_obj,
                    prompt=prompt
                )
                
                # J. Clean and validate
                cleaned_output = components["output_validator"].filter_decision_fields(llm_response)
                is_valid = components["output_validator"].validate(cleaned_output, selected_policy_id)
                if not is_valid:
                    recovery_output = components["llm_client"]._deterministic_formatter(
                        claim_id=norm_claim.claim_id,
                        policy_id=selected_policy_id,
                        payer=norm_claim.insurance.primary.payer,
                        relevance_score=best_score,
                        evidence_object=evidence_obj
                    )
                    cleaned_output = components["output_validator"].filter_decision_fields(recovery_output)
                    
                claim_outputs.append(cleaned_output)
            except Exception as e:
                # Handle individual procedure/RAG failure safely (Constraint 9)
                print(f"[RAG Integration] Failure during RAG run for input {inp_dict}: {e}")
                
        # 3. Merge RAG outputs from multiple procedures (Constraint 3 & 6)
        if not claim_outputs:
            # RAG failure or no policies matched: return safe empty policy
            merged_output = {
                "claim_id": canonical_claim.get("claim_id") or "UNKNOWN-CLAIM",
                "policy_matches": [],
                "criteria": [],
                "documentation_requirements": []
            }
        else:
            # Synthesize merged output from all ClaimOutputs
            merged_output = {
                "claim_id": claim_outputs[0]["claim_id"],
                "policy_matches": [],
                "criteria": [],
                "documentation_requirements": []
            }
            
            seen_policies = set()
            for co in claim_outputs:
                for pm in co.get("policy_matches") or []:
                    pol_id = pm["policy_id"]
                    if pol_id not in seen_policies:
                        seen_policies.add(pol_id)
                        merged_output["policy_matches"].append(pm)
                    else:
                        # Update relevance score if higher
                        for existing_pm in merged_output["policy_matches"]:
                            if existing_pm["policy_id"] == pol_id:
                                existing_pm["relevance_score"] = max(
                                    existing_pm["relevance_score"], pm["relevance_score"]
                                )
                                
            seen_criteria = set()
            for co in claim_outputs:
                for crit in co.get("criteria") or []:
                    crit_id = crit["criterion_id"]
                    if crit_id not in seen_criteria:
                        seen_criteria.add(crit_id)
                        merged_output["criteria"].append(crit)
                        
            seen_docs = set()
            for co in claim_outputs:
                for doc in co.get("documentation_requirements") or []:
                    req = doc["requirement"]
                    if req not in seen_docs:
                        seen_docs.add(req)
                        merged_output["documentation_requirements"].append(doc)
                        
        # 4. RAG Output to legacy Agent 1 Policy dictionary format (rag_policy_adapter)
        rag_policy = rag_policy_adapter(merged_output, canonical_claim)
        
        if not rag_policy.get("criteria"):
            # Safe fallback: no policy criteria matched or RAG failure occurred. Fail closed to HUMAN_REVIEW (Constraint 9 & 12)
            return DecisionResponse(
                case_id=canonical_claim.get("claim_id") or "UNKNOWN-CLAIM",
                outcome=DecisionOutcome.HUMAN_REVIEW,
                reasoning=["RAG retrieval failed or found no matching policy criteria. Escalating to HUMAN_REVIEW (fail-closed)."],
                exclusion_results={},
                criteria_results={},
                criteria_evaluations={},
                evidence_status={},
                errors=["RAG failed to retrieve any criteria for the requested procedures."],
                claim_id=canonical_claim.get("claim_id")
            )
        
        # 5. Execute Agent 1 Decision logic (Constraint 14 & 15)
        agent = DecisionAgent(
            llm_provider=components.get("llm_provider")
        )
        decision_response = agent.evaluate_canonical_claim(canonical_claim, rag_policy)

        # Surface payer linkage notes without overriding claim payer or LLM decision authority.
        metrics = (canonical_claim.get("case_data") or {}).get("clinical_metrics") or {}
        payer_notes = []
        if metrics.get("member_id"):
            payer_notes.append(
                f"Payer linkage: member_id={metrics.get('member_id')} "
                f"member_payer_id={metrics.get('member_payer_id')} "
                f"plan_id={metrics.get('plan_id')} "
                f"eligibility_eligible={metrics.get('eligibility_eligible')}."
            )
        for note in metrics.get("payer_alias_notes") or []:
            payer_notes.append(str(note))
        if metrics.get("claim_member_payer_mismatch") is True:
            payer_notes.append(
                "Claim payer and member payer differ after alias normalization; "
                "claim_payer was preserved (not overridden)."
            )
        if payer_notes:
            decision_response.reasoning = [
                "--- Payer Context (non-decisional linkage) ---",
                *payer_notes,
                "--- End Payer Context ---",
                *decision_response.reasoning,
            ]
        return decision_response

        
    except Exception as e:
        # Catch-all safe fail-closed: return DecisionResponse with HUMAN_REVIEW outcome (Constraint 9)
        print(f"[RAG Integration] Critical error in integrated pipeline: {e}")
        return DecisionResponse(
            case_id=canonical_claim.get("claim_id") or "UNKNOWN-CLAIM",
            outcome=DecisionOutcome.HUMAN_REVIEW,
            reasoning=["Integrated pipeline catch-all error fallback.", f"Error details: {e}"],
            exclusion_results={},
            criteria_results={},
            criteria_evaluations={},
            evidence_status={},
            errors=[f"Integrated pipeline critical error: {e}"],
            claim_id=canonical_claim.get("claim_id")
        )


def run_pipeline_from_db(
    patient_id: str,
    components: Dict[str, Any],
    claim_id: Optional[str] = None,
    attempt: Optional[int] = None,
    adapter: Optional[RuntimeAdapter] = None,
) -> DecisionResponse:
    """End-to-end entry: provider DB + payer DB → Runtime → CanonicalClaim → RAG → Decision.

    Builds the linked runtime claim (provider data enriched with payer_data.db context)
    and feeds it into run_integrated_pipeline. Payer linkage (member_id, plan_id,
    coverage, eligibility) is propagated automatically.
    """
    rt = adapter or RuntimeAdapter()
    linked_claim = rt.get_linked_runtime_claim(patient_id, claim_id, attempt)

    if linked_claim is None:
        return DecisionResponse(
            case_id=claim_id or patient_id or "UNKNOWN-CLAIM",
            outcome=DecisionOutcome.HUMAN_REVIEW,
            reasoning=[
                "Runtime adapter could not resolve provider claim and payer context.",
                f"patient_id={patient_id}, claim_id={claim_id}, attempt={attempt}.",
            ],
            exclusion_results={},
            criteria_results={},
            criteria_evaluations={},
            evidence_status={},
            errors=["Provider claim or payer context not found in V1 databases."],
            claim_id=claim_id,
        )

    return run_integrated_pipeline(linked_claim, components)
