import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from models.rag_models import ClaimInput
from adapters.rag_adapter import rag_claim_adapter, rag_policy_adapter
from adapters.runtime_adapter import RuntimeAdapter
from rag.normalization.input_normalizer import normalize_claim_input
from decision.schemas import DecisionResponse, DecisionOutcome, DecisionReasonCode
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

            # Structured (dict) policy exclusions travel alongside the RAG output
            # but are NOT part of the validated ClaimOutput contract (which stays
            # exactly the 4 sanctioned root keys). Free-text chunk limitation /
            # contraindication strings are intentionally not promoted into
            # decision-level exclusions.
            merged_exclusions = []
            seen_exclusions = set()
            for co in claim_outputs:
                for exc in co.get("exclusions") or []:
                    if not isinstance(exc, dict):
                        continue
                    exc_id = exc.get("exclusion_id")
                    if exc_id and exc_id not in seen_exclusions:
                        seen_exclusions.add(exc_id)
                        merged_exclusions.append(exc)
                        
        # 4. RAG Output to legacy Agent 1 Policy dictionary format (rag_policy_adapter)
        rag_policy = rag_policy_adapter(merged_output, canonical_claim)

        # Attach structured exclusions (kept outside the validated ClaimOutput
        # contract) so hard coverage exclusions reach Agent 1 unchanged.
        if not claim_outputs:
            merged_exclusions = []
        if merged_exclusions:
            rag_policy["exclusions"] = merged_exclusions
        
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
                claim_id=canonical_claim.get("claim_id"),
                reason_code=DecisionReasonCode.NO_MATCHING_POLICY,
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
            claim_id=canonical_claim.get("claim_id"),
            reason_code=DecisionReasonCode.PIPELINE_FAIL_CLOSED,
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
            reason_code=DecisionReasonCode.PROVIDER_CLAIM_NOT_FOUND,
        )

    return run_integrated_pipeline(linked_claim, components)


# =====================================================================
# AGENT 2 V1 INTEGRATION LAYER
# =====================================================================
#
# Real V1 workflow with recovery:
#   Provider data -> CanonicalClaim -> RAG -> Agent 1 -> DecisionResponse
#   -> routing -> Agent 2 (when appropriate) -> provider evidence recovery
#   -> sensitivity/release gate -> SubmissionPackage -> Agent 1 again
#   -> final outcome.
#
# Hard constraints honored here:
#   * Agent 1 (run_integrated_pipeline / DecisionAgent) is never duplicated and
#     its decision semantics are never altered; every version is re-decided by
#     the same deterministic path including RAG.
#   * Agent 2 recovery reads ONLY provider-side evidence (recovery_source);
#     payer-side data never enters recovery. Payer linkage metrics already
#     attached to the canonical claim are read by administrative gates only.
#   * The NVIDIA LLM (agent2 RejectionAnalyzer) may only interpret search
#     concepts; it never makes the coverage decision.
#   * Claim versions are immutable append-only snapshots (V1 -> V2 -> ...).

_ROUTE_RECOVERABLE = "RECOVERABLE"
_ROUTE_TERMINAL = "TERMINAL"

# Sensitivity taxonomy (DATA-VERSION1/README.md): only ROUTINE evidence may be
# released programmatically. PROTECTED_* and UNKNOWN escalate to HUMAN_REVIEW.
_SENSITIVITY_ROUTINE = "ROUTINE"
_SENSITIVITY_PROTECTED_PREFIX = "PROTECTED_"

_ADMIN_INACTIVE_COVERAGE_STATUSES = {"INACTIVE", "LAPSED", "TERMINATED", "EXPIRED"}

# Provenance/meta fact keys that are never merged into derived clinical metrics.
_FACT_META_KEYS = {
    "evidence_type",
    "source_record_id",
    "event_date",
    "provenance",
    "sensitivity",
    "content_reference",
}


def classify_decision_for_agent2(decision: DecisionResponse) -> str:
    """Route an Agent 1 DecisionResponse for Agent 2 handling (frozen V1).

    REQUEST_MORE_INFORMATION  -> the ONLY recoverable outcome -> Agent 2.
    APPROVE                   -> terminal, no Agent 2 recovery.
    HUMAN_REVIEW              -> terminal, no direct Agent 2 recovery.
    REJECT                    -> terminal hard denial, no recovery -- for ANY
                                 reason (coverage exclusion OR hard criterion
                                 failure). There is NO generic REJECT -> Agent2
                                 path. Documentation insufficiency is always
                                 represented as REQUEST_MORE_INFORMATION by
                                 Agent 1, never as a recoverable REJECT.
    """
    outcome = decision.outcome
    if outcome == DecisionOutcome.REQUEST_MORE_INFORMATION:
        return _ROUTE_RECOVERABLE
    return _ROUTE_TERMINAL


def _administrative_block_reason(claim: Dict[str, Any]) -> Optional[str]:
    """Administrative gates that force a terminal REJECT with no Agent 2.

    Lapsed eligibility and exceeded filing deadlines are deterministic
    administrative facts (not uncertainty), so they resolve to a terminal
    administrative denial rather than HUMAN_REVIEW.

    Uses only payer-linkage metrics already attached to the canonical claim
    (orchestration-level gate; Agent 2 itself never queries payer data).
    """
    metrics = (claim.get("case_data") or {}).get("clinical_metrics") or {}
    if metrics.get("eligibility_eligible") is False:
        return "Lapsed eligibility: member is not eligible; terminal administrative denial."
    coverage_status = metrics.get("coverage_status")
    if isinstance(coverage_status, str) and coverage_status.strip().upper() in _ADMIN_INACTIVE_COVERAGE_STATUSES:
        return (
            f"Lapsed eligibility: coverage status '{coverage_status}'; "
            "terminal administrative denial."
        )
    if metrics.get("filing_deadline_exceeded") is True or metrics.get("filing_deadline_status") == "EXCEEDED":
        return "Filing deadline exceeded: resubmission window closed; terminal administrative denial."
    return None


def _requested_evidence_keys(decision: DecisionResponse) -> List[str]:
    """Evidence keys Agent 1 reported as missing or tied to failed criteria."""
    keys = {k for k, status in (decision.evidence_status or {}).items() if status == "missing"}
    for crit_id, evaluation in (decision.criteria_evaluations or {}).items():
        if evaluation.state in ("FAIL", "MISSING", "CONFLICTING"):
            for prov in evaluation.evidence_provenance:
                if prov.evaluation_status == "missing" and prov.evidence_key:
                    keys.add(prov.evidence_key)
    ordered: List[str] = []
    for key in sorted(keys):
        if not key.startswith("__"):
            ordered.append(key)
    return ordered


def _failed_criterion_ids(decision: DecisionResponse) -> List[str]:
    return sorted(
        crit_id
        for crit_id, evaluation in (decision.criteria_evaluations or {}).items()
        if evaluation.state in ("FAIL", "MISSING", "CONFLICTING")
    )


def _decision_to_payer_response(decision: DecisionResponse) -> Any:
    """Convert a DecisionResponse into the agent2 PayerResponse contract."""
    from agent2.schemas.payer_response import PayerResponse

    outcome_map = {
        DecisionOutcome.APPROVE: "APPROVED",
        DecisionOutcome.REJECT: "REJECTED",
        DecisionOutcome.REQUEST_MORE_INFORMATION: "REQUEST_MORE_INFORMATION",
        DecisionOutcome.HUMAN_REVIEW: "HUMAN_REVIEW",
    }
    decision_value = outcome_map.get(decision.outcome, "HUMAN_REVIEW")

    missing_keys = _requested_evidence_keys(decision)
    requested_information = [f"Required evidence is missing: {key}" for key in missing_keys]
    for evaluation in (decision.criteria_evaluations or {}).values():
        for line in evaluation.reasoning:
            if line.startswith("Required evidence is missing:"):
                if line not in requested_information:
                    requested_information.append(line)

    reason_lines = [
        line for line in decision.reasoning
        if "Decision Outcome:" in line or "Required evidence is missing" in line
    ]
    reason = "; ".join(reason_lines) if reason_lines else str(decision.outcome)

    # Frozen routing: only REQUEST_MORE_INFORMATION is Agent2-recoverable.
    # Every REJECT (hard criterion failure or coverage exclusion) is terminal.
    is_recoverable = decision.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION

    return PayerResponse(
        submission_id=decision.claim_id or decision.case_id,
        decision=decision_value,
        reason=reason,
        is_recoverable=is_recoverable,
        failed_criteria=_failed_criterion_ids(decision),
        requested_information=requested_information,
    )


def _classify_sensitivity(item: Dict[str, Any]) -> str:
    """Classify one evidence item: ROUTINE (releasable), PROTECTED, or UNKNOWN."""
    facts = item.get("extracted_facts") or {}
    raw = facts.get("sensitivity") if isinstance(facts, dict) else None
    if raw is None or not str(raw).strip():
        return "UNKNOWN"
    value = str(raw).strip().upper()
    if value == _SENSITIVITY_ROUTINE:
        return "ROUTINE"
    if value.startswith(_SENSITIVITY_PROTECTED_PREFIX):
        return "PROTECTED"
    return "UNKNOWN"


def _release_gate(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Programmatic sensitivity/release gate.

    Returns (released_items, blocked_items). Only ROUTINE evidence is released;
    PROTECTED_* and UNKNOWN evidence are blocked and must go to HUMAN_REVIEW.
    """
    released: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    for item in items:
        if _classify_sensitivity(item) == "ROUTINE":
            released.append(item)
        else:
            blocked.append(item)
    return released, blocked


def _concept_matches_item(concept: str, item: Dict[str, Any]) -> bool:
    concept = concept.strip().lower()
    if not concept:
        return False
    haystacks = [
        str(item.get("evidence_key") or ""),
        str((item.get("extracted_facts") or {}).get("evidence_type") or ""),
        str(item.get("unstructured_text") or ""),
    ]
    facts = item.get("extracted_facts") or {}
    if isinstance(facts, dict):
        haystacks.append(json.dumps(facts, default=str))
    return any(concept in haystack.lower() for haystack in haystacks)


def _select_recovered_evidence(
    pool: List[Dict[str, Any]],
    requested_keys: List[str],
    concepts: List[str],
    existing_ids: set,
) -> List[Dict[str, Any]]:
    """Minimum-necessary selection of real provider records for recovery.

    Only pool items (real evidence rows) can ever be returned, so no evidence
    can be fabricated. Matching is restricted to items whose evidence_key was
    explicitly requested by Agent 1 or whose content matches a requested
    clinical concept; everything else is left out (minimum necessary).
    """
    selected: List[Dict[str, Any]] = []
    seen_ids = set()
    normalized_keys = {str(k).lower() for k in requested_keys}
    for item in pool or []:
        evidence_id = item.get("evidence_id")
        if not evidence_id or evidence_id in existing_ids or evidence_id in seen_ids:
            continue
        key_match = str(item.get("evidence_key") or "").lower() in normalized_keys
        concept_match = any(_concept_matches_item(c, item) for c in concepts)
        if key_match or concept_match:
            selected.append(item)
            seen_ids.add(evidence_id)
    return selected


def _build_next_version_claim(
    base_claim: Dict[str, Any],
    recovered_items: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[str]]:
    """Build the next immutable claim version by appending recovered evidence.

    History is never overwritten: the base version stays untouched and the new
    version is a deep copy plus append-only evidence delta. Derived case_data
    fields (diagnoses, clinical_metrics) are rebuilt for the new evidence set;
    recovered (new_evidence_delta) facts take precedence over previously
    derived metric values because the delta is the corrective content of the
    resubmission, while every original evidence item remains in place.
    """
    claim = deepcopy(base_claim)
    evidence = claim.setdefault("evidence", [])
    existing_ids = {item.get("evidence_id") for item in evidence if isinstance(item, dict)}

    delta_ids: List[str] = []
    for item in recovered_items:
        evidence_id = item.get("evidence_id")
        if not evidence_id or evidence_id in existing_ids:
            continue
        evidence.append(deepcopy(item))
        existing_ids.add(evidence_id)
        delta_ids.append(evidence_id)

    submission = claim.setdefault("submission", {})
    try:
        submission["attempt"] = int(submission.get("attempt") or 1) + 1
    except (TypeError, ValueError):
        submission["attempt"] = 2
    submission["new_evidence_delta"] = delta_ids

    case_data = claim.setdefault("case_data", {})

    # Rebuild claim-relevant diagnoses from the full V-next evidence set
    # (same derivation rule as RuntimeAdapter: ICD codes in content references).
    diagnoses: List[str] = list(case_data.get("diagnoses") or [])
    for item in evidence:
        content = ((item.get("extracted_facts") or {}).get("content_reference")) if isinstance(item, dict) else None
        for code in RuntimeAdapter._extract_diagnosis_codes(content):
            if code not in diagnoses:
                diagnoses.append(code)
    case_data["diagnoses"] = diagnoses

    # Merge recovered facts into derived clinical metrics with delta precedence.
    metrics = dict(case_data.get("clinical_metrics") or {})
    for item in recovered_items:
        facts = item.get("extracted_facts") or {}
        if not isinstance(facts, dict):
            continue
        for key, value in facts.items():
            if key in _FACT_META_KEYS:
                continue
            metrics[key] = value
    case_data["clinical_metrics"] = metrics

    return claim, delta_ids


@dataclass
class Agent2V1Result:
    """Outcome of the Agent1 + Agent2 real V1 pipeline run."""

    final_outcome: DecisionOutcome
    final_decision: DecisionResponse
    versions: List[Dict[str, Any]] = field(default_factory=list)          # immutable snapshots V1..Vn
    submissions: List[Dict[str, Any]] = field(default_factory=list)        # SubmissionPackages for V2+
    agent2_invoked: bool = False
    resubmissions: int = 0
    human_review_required: bool = False
    human_review_reasons: List[str] = field(default_factory=list)
    sensitive_blocked: bool = False
    audit_trail: List[str] = field(default_factory=list)
    # Phase 3 contract fields: structured evidence request Agent2 received and
    # its FOUND/MISSING recovery result (None when Agent2 was never invoked).
    evidence_request: Optional[Any] = None
    recovery_result: Optional[Any] = None
    provider_declined: bool = False
    # Phase 4 control plane: enforced lifecycle states + immutable audit trail.
    control_plane: Optional[Any] = None


def _default_recovery_source_factory(adapter: Optional[RuntimeAdapter] = None):
    """Recovery source backed by the provider DB only (never payer data)."""
    rt = adapter or RuntimeAdapter()

    def source(requested_keys: List[str], concepts: List[str], claim: Dict[str, Any]) -> List[Dict[str, Any]]:
        metrics = (claim.get("case_data") or {}).get("clinical_metrics") or {}
        patient_id = claim.get("patient_id") or metrics.get("patient_id") or metrics.get("member_id")
        return rt.get_provider_evidence_pool(patient_id)

    return source


def run_agent2_v1_pipeline(
    canonical_claim: Dict[str, Any],
    components: Dict[str, Any],
    recovery_source=None,
    max_resubmissions: Optional[int] = None,
    provider_decision: str = "ACCEPT",
    control_plane=None,
    persist_workflow_db: bool = False,
) -> Agent2V1Result:
    """Run the real V1 pipeline with Agent 2 evidence recovery integrated.

    Flow: CanonicalClaim -> RAG -> Agent 1 -> DecisionResponse -> routing ->
    structured EvidenceRequest -> Agent 2 provider-side recovery (FOUND /
    MISSING per requested item) -> sensitivity/release gate -> provider
    accept/decline -> SubmissionPackage (V2+) -> Agent 1 again -> final
    outcome.

    ``recovery_source(requested_keys, concepts, claim) -> [evidence items]``
    supplies the provider-side evidence pool; defaults to the provider DB via
    RuntimeAdapter.get_provider_evidence_pool. Claim versions are immutable
    (V1 -> V2 -> ...) and the loop is bounded by MAX_RESUBMISSION_ATTEMPTS so
    Agent 1 <-> Agent 2 can never loop forever.

    ``provider_decision`` models the provider accept/decline gate on recovered
    evidence: any value other than "ACCEPT" stops the resubmission and
    escalates to HUMAN_REVIEW (Agent 2 never overrides provider consent).

    Phase 4 control plane: every important state/action transition is enforced
    against the frozen lifecycle (RMI is the only recovery route; REJECT and
    APPROVE are terminal; HUMAN_REVIEW can never enter recovery directly) and
    recorded as an immutable audit event carrying correlation_id and
    evidence_request_id. Pass ``control_plane`` to share state across runs
    (e.g. human-resolution re-entry); ``persist_workflow_db=True`` also writes
    events/provider decisions to the agent2 SQLite database.
    """
    from agent2.config import MAX_RESUBMISSION_ATTEMPTS
    from agent2.reasoning.rejection_analyzer import RejectionAnalyzer
    from agent2.recovery import run_contract_recovery
    from agent2.workflow.control_plane import ClaimWorkflowState, WorkflowControlPlane

    if recovery_source is None:
        recovery_source = _default_recovery_source_factory()
    cap = max_resubmissions if max_resubmissions is not None else MAX_RESUBMISSION_ATTEMPTS

    audit: List[str] = []
    versions: List[Dict[str, Any]] = []
    submissions: List[Dict[str, Any]] = []
    human_review_reasons: List[str] = []
    sensitive_blocked = False
    agent2_invoked = False
    resubmissions = 0
    evidence_request: Optional[Any] = None
    recovery_result: Optional[Any] = None
    provider_declined = False

    analyzer = RejectionAnalyzer()

    # Phase 4 control plane: enforced legal transitions + immutable events.
    cp = control_plane or WorkflowControlPlane(persist_db=persist_workflow_db)
    wf_claim_id = str(canonical_claim.get("claim_id") or "UNKNOWN-CLAIM")
    # Version continuity across runs sharing one control plane (re-entry).
    wf_version_offset = max(0, cp.current_version(wf_claim_id) - 1)

    def wf_transition(state, action, version=None, correlation_id=None, erqid=None, detail=None):
        return cp.transition(
            wf_claim_id,
            state,
            action,
            claim_version=version if version is not None else len(versions) + wf_version_offset,
            correlation_id=correlation_id,
            evidence_request_id=erqid,
            detail=detail,
        )

    current_claim = deepcopy(canonical_claim)
    if cp.current_state(wf_claim_id) == ClaimWorkflowState.INIT:
        wf_transition(ClaimWorkflowState.RECEIVED, "Claim received for Agent1 evaluation", version=1 + wf_version_offset)
    wf_transition(ClaimWorkflowState.EVALUATING, f"Agent1 evaluating V{1 + wf_version_offset}", version=1 + wf_version_offset)
    decision = run_integrated_pipeline(current_claim, components)
    versions.append({
        "version": "V1",
        "attempt": (current_claim.get("submission") or {}).get("attempt") or 1,
        "claim": current_claim,
        "decision": decision,
        "new_evidence_delta": [],
    })
    audit.append(f"V1: Agent1 outcome={decision.outcome.value}")

    final_outcome_override: Optional[DecisionOutcome] = None

    while True:
        route = classify_decision_for_agent2(decision)
        if route != _ROUTE_RECOVERABLE:
            if decision.outcome == DecisionOutcome.APPROVE:
                audit.append("Routing: APPROVE is terminal; Agent2 not invoked.")
                wf_transition(ClaimWorkflowState.APPROVED, "Agent1 APPROVE: terminal, no Agent2 recovery")
            elif decision.outcome == DecisionOutcome.HUMAN_REVIEW:
                audit.append("Routing: HUMAN_REVIEW is terminal; no direct Agent2 recovery.")
                human_review_reasons.append("Agent1 escalated to HUMAN_REVIEW; no direct Agent2 recovery.")
                wf_transition(
                    ClaimWorkflowState.HUMAN_REVIEW,
                    "Agent1 HUMAN_REVIEW escalation; no direct Agent2 recovery",
                    detail="; ".join(decision.reasoning[-2:]) if decision.reasoning else None,
                )
            else:
                audit.append(
                    "Routing: REJECT is terminal (hard denial / coverage exclusion); "
                    "no Agent2 recovery."
                )
                wf_transition(
                    ClaimWorkflowState.REJECTED,
                    "Agent1 REJECT: terminal, no Agent2 recovery",
                    detail=str(decision.reason_code.value if decision.reason_code else ""),
                )
            break

        wf_transition(
            ClaimWorkflowState.ROUTED_RECOVERY,
            "REQUEST_MORE_INFORMATION routed to Agent2 (only recoverable outcome)",
            correlation_id=f"CORR-{decision.claim_id or decision.case_id}-V{len(versions)}",
        )

        admin_reason = _administrative_block_reason(current_claim)
        if admin_reason:
            audit.append(
                f"Routing: terminal administrative REJECT ({admin_reason}); Agent2 not invoked."
            )
            wf_transition(ClaimWorkflowState.REJECTED, f"Administrative gate: {admin_reason}")
            final_outcome_override = DecisionOutcome.REJECT
            break

        agent2_invoked = True

        if resubmissions >= cap:
            reason = (
                f"MAX_RESUBMISSION_ATTEMPTS reached ({cap}); stopping safely without overwriting history."
            )
            audit.append(reason)
            human_review_reasons.append(reason)
            wf_transition(ClaimWorkflowState.HUMAN_REVIEW, reason)
            final_outcome_override = DecisionOutcome.HUMAN_REVIEW
            break

        payer_response = _decision_to_payer_response(decision)
        analysis = analyzer.analyze_payer_response(payer_response)
        concepts = list(analysis.get("requested_concepts") or [])
        requested_keys = _requested_evidence_keys(decision)
        audit.append(
            f"Agent2 analysis: failed_criteria={analysis.get('failed_criterion_ids')}, "
            f"requested_concepts={concepts}, requested_keys={requested_keys}"
        )

        pool = recovery_source(requested_keys, concepts, current_claim) or []
        existing_ids = {
            item.get("evidence_id") for item in current_claim.get("evidence", []) if isinstance(item, dict)
        }

        # Phase 3 contract: Agent2 receives ONLY the structured EvidenceRequest
        # and tracks each requested item as FOUND or MISSING against the
        # provider pool (never SATISFIED; never fabricated).
        metrics_for_id = (current_claim.get("case_data") or {}).get("clinical_metrics") or {}
        recovery_patient_id = (
            current_claim.get("patient_id")
            or metrics_for_id.get("patient_id")
            or metrics_for_id.get("member_id")
            or ""
        )
        plan = run_contract_recovery(
            decision,
            patient_id=recovery_patient_id,
            claim_version=len(versions),
            pool=pool,
        )
        if plan is not None:
            evidence_request = plan.request
            recovery_result = plan.result
            audit.append(
                f"Agent2 contract recovery: request={plan.request.evidence_request_id} "
                f"correlation={plan.request.correlation_id} "
                f"FOUND={plan.found_evidence_ids} MISSING={plan.result.missing_requests}"
            )
            # Contract-driven selection: only items the contract tracked as
            # FOUND (real provider records) may proceed. Items already part of
            # the current version are never re-appended.
            candidates = [
                item for item in plan.selected_pool_items
                if item.get("evidence_id") not in existing_ids
            ]
        else:
            # Defensive fallback: RMI without any structured request content.
            # Legacy minimum-necessary selection of real pool records.
            candidates = _select_recovered_evidence(pool, requested_keys, concepts, existing_ids)
        audit.append(f"Agent2 recovery: pool_size={len(pool)}, candidates={[c.get('evidence_id') for c in candidates]}")

        # Control plane: recovery ran over the provider pool; carry the contract
        # IDs through every subsequent event for end-to-end traceability.
        wf_correlation = plan.request.correlation_id if plan is not None else None
        wf_erq = plan.request.evidence_request_id if plan is not None else None
        wf_transition(
            ClaimWorkflowState.RECOVERING,
            "Agent2 EvidenceRequest recovery over provider pool (FOUND/MISSING)",
            correlation_id=wf_correlation,
            erqid=wf_erq,
            detail=(
                f"FOUND={plan.found_evidence_ids} MISSING={plan.result.missing_requests}"
                if plan is not None else "legacy fallback selection"
            ),
        )

        if not candidates:
            reason = "No recoverable provider-side evidence found; nothing was fabricated. Escalating to HUMAN_REVIEW."
            audit.append(reason)
            human_review_reasons.append(reason)
            wf_transition(ClaimWorkflowState.HUMAN_REVIEW, reason, correlation_id=wf_correlation, erqid=wf_erq)
            final_outcome_override = DecisionOutcome.HUMAN_REVIEW
            break

        released, blocked = _release_gate(candidates)
        if blocked:
            sensitive_blocked = True
            blocked_ids = [item.get("evidence_id") for item in blocked]
            reason = (
                f"Programmatic release gate blocked sensitive/restricted evidence {blocked_ids}; "
                "escalating to HUMAN_REVIEW."
            )
            audit.append(reason)
            human_review_reasons.append(reason)
            wf_transition(ClaimWorkflowState.HUMAN_REVIEW, reason, correlation_id=wf_correlation, erqid=wf_erq)
            final_outcome_override = DecisionOutcome.HUMAN_REVIEW
            break

        # Anti-fabrication guard: only records physically present in the
        # provider pool may enter the resubmission.
        pool_ids = {item.get("evidence_id") for item in pool}
        if any(item.get("evidence_id") not in pool_ids for item in released):
            reason = "Recovered evidence failed provenance validation against the provider pool."
            audit.append(reason)
            human_review_reasons.append(reason)
            wf_transition(ClaimWorkflowState.HUMAN_REVIEW, reason, correlation_id=wf_correlation, erqid=wf_erq)
            final_outcome_override = DecisionOutcome.HUMAN_REVIEW
            break

        # Provider accept/decline gate: recovered evidence is only resubmitted
        # with provider consent; decline escalates to HUMAN_REVIEW. The consent
        # decision is persisted as a first-class workflow record.
        wf_transition(
            ClaimWorkflowState.AWAITING_PROVIDER_DECISION,
            "Provider accept/decline gate on recovered evidence",
            correlation_id=wf_correlation,
            erqid=wf_erq,
        )
        released_ids = [item.get("evidence_id") for item in released]
        cp.record_provider_decision(
            wf_claim_id,
            provider_decision,
            claim_version=len(versions) + wf_version_offset,
            evidence_ids=released_ids,
            evidence_request_id=wf_erq,
            correlation_id=wf_correlation,
            reason="Recovered provider evidence consent gate",
        )
        if str(provider_decision).strip().upper() != "ACCEPT":
            provider_declined = True
            reason = (
                f"Provider declined resubmission of recovered evidence "
                f"(decision='{provider_decision}'); no V{len(versions) + 1} is built. "
                "Escalating to HUMAN_REVIEW."
            )
            audit.append(reason)
            human_review_reasons.append(reason)
            wf_transition(ClaimWorkflowState.HUMAN_REVIEW, reason, correlation_id=wf_correlation, erqid=wf_erq)
            final_outcome_override = DecisionOutcome.HUMAN_REVIEW
            break

        next_claim, delta_ids = _build_next_version_claim(current_claim, released)
        resubmissions += 1
        version_label = f"V{len(versions) + 1}"
        attempt_no = (next_claim.get("submission") or {}).get("attempt") or (resubmissions + 1)

        wf_transition(
            ClaimWorkflowState.RESUBMITTING,
            f"Provider ACCEPT; building immutable {version_label} with released delta",
            correlation_id=wf_correlation,
            erqid=wf_erq,
            detail=f"delta={delta_ids}",
        )

        submission_package = {
            "version": version_label,
            "claim_id": next_claim.get("claim_id"),
            "attempt": attempt_no,
            "evidence_ids": [
                item.get("evidence_id") for item in next_claim.get("evidence", []) if isinstance(item, dict)
            ],
            "new_evidence_delta": delta_ids,
            "released": True,
            # Phase 4: contract IDs propagate through the submission.
            "correlation_id": wf_correlation,
            "evidence_request_id": wf_erq,
        }
        submissions.append(submission_package)
        audit.append(
            f"{version_label}: SubmissionPackage prepared with delta={delta_ids} (provenance preserved)."
        )

        # Re-run the SAME Agent 1 pipeline (RAG included) on the new version.
        wf_transition(
            ClaimWorkflowState.EVALUATING,
            f"Agent1 re-evaluating {version_label}",
            version=len(versions) + 1 + wf_version_offset,
            correlation_id=wf_correlation,
            erqid=wf_erq,
        )
        decision = run_integrated_pipeline(next_claim, components)
        versions.append({
            "version": version_label,
            "attempt": attempt_no,
            "claim": next_claim,
            "decision": decision,
            "new_evidence_delta": delta_ids,
        })
        audit.append(f"{version_label}: Agent1 outcome={decision.outcome.value}")
        current_claim = next_claim

    final_outcome = final_outcome_override or decision.outcome
    human_review_required = final_outcome == DecisionOutcome.HUMAN_REVIEW
    return Agent2V1Result(
        final_outcome=final_outcome,
        final_decision=decision,
        versions=versions,
        submissions=submissions,
        agent2_invoked=agent2_invoked,
        resubmissions=resubmissions,
        human_review_required=human_review_required,
        human_review_reasons=human_review_reasons,
        sensitive_blocked=sensitive_blocked,
        audit_trail=audit,
        evidence_request=evidence_request,
        recovery_result=recovery_result,
        provider_declined=provider_declined,
        control_plane=cp,
    )


def reenter_after_human_resolution(
    canonical_claim: Dict[str, Any],
    components: Dict[str, Any],
    control_plane,
    attached_evidence: Optional[List[Dict[str, Any]]] = None,
    recovery_source=None,
    max_resubmissions: Optional[int] = None,
    provider_decision: str = "ACCEPT",
    resolution_note: str = "",
) -> Agent2V1Result:
    """Re-enter the workflow after a human resolution of a HUMAN_REVIEW hold.

    Frozen lifecycle: Agent 2 NEVER resumes recovery directly from
    HUMAN_REVIEW. The resolution transitions the claim
    HUMAN_REVIEW -> RESOLVED_REENTRY -> RECEIVED, and the claim then goes
    through NORMAL Agent 1 routing exactly like any submission (same frozen
    classifier: RMI -> Agent2 recovery; REJECT/APPROVE -> terminal).

    ``control_plane`` must be the control plane that tracked the claim into
    HUMAN_REVIEW (state is enforced; resolving a claim that is not in
    HUMAN_REVIEW raises IllegalWorkflowTransition).

    ``attached_evidence`` are real provider records (dicts with real
    evidence_id) the human resolution adds to the claim; they enter as a new
    append-only claim version (history is never overwritten). Fabricated
    entries (no evidence_id) are rejected.
    """
    from agent2.workflow.control_plane import ClaimWorkflowState

    claim_id = str(canonical_claim.get("claim_id") or "UNKNOWN-CLAIM")
    cp = control_plane
    cp.resolve_human_review(claim_id, resolution_note=resolution_note)

    claim = deepcopy(canonical_claim)
    next_version = cp.current_version(claim_id)
    if attached_evidence:
        for item in attached_evidence:
            if not isinstance(item, dict) or not item.get("evidence_id"):
                raise ValueError(
                    "Human-attached evidence must be real provider records carrying "
                    "an evidence_id (no fabricated evidence)."
                )
        claim, _ = _build_next_version_claim(claim, list(attached_evidence))
        next_version += 1

    # RESOLVED_REENTRY -> RECEIVED: normal Agent 1 routing resumes from here.
    cp.transition(
        claim_id,
        ClaimWorkflowState.RECEIVED,
        "Human resolution re-enters normal Agent1 routing",
        claim_version=next_version,
        detail=resolution_note or None,
    )
    return run_agent2_v1_pipeline(
        claim,
        components,
        recovery_source=recovery_source,
        max_resubmissions=max_resubmissions,
        provider_decision=provider_decision,
        control_plane=cp,
    )


def run_agent2_pipeline_from_db(
    patient_id: str,
    components: Dict[str, Any],
    claim_id: Optional[str] = None,
    attempt: Optional[int] = None,
    adapter: Optional[RuntimeAdapter] = None,
    max_resubmissions: Optional[int] = None,
) -> Agent2V1Result:
    """End-to-end entry with Agent 2: provider DB -> linked runtime claim ->
    run_agent2_v1_pipeline, with recovery sourced from the provider DB only."""
    rt = adapter or RuntimeAdapter()
    linked_claim = rt.get_linked_runtime_claim(patient_id, claim_id, attempt)

    if linked_claim is None:
        fallback = DecisionResponse(
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
        return Agent2V1Result(
            final_outcome=DecisionOutcome.HUMAN_REVIEW,
            final_decision=fallback,
            human_review_required=True,
            human_review_reasons=["Provider claim or payer context not found in V1 databases."],
            audit_trail=["Agent2 pipeline aborted: linked runtime claim unavailable."],
        )

    linked_claim["patient_id"] = patient_id
    return run_agent2_v1_pipeline(
        linked_claim,
        components,
        recovery_source=_default_recovery_source_factory(rt),
        max_resubmissions=max_resubmissions,
    )
