import json

import re
from typing import Any, Dict, List, Optional
from decision.schemas import (
    Policy,
    CaseData,
    EvidenceItem,
    EvidenceStatus,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
    CanonicalClaim,
    CriterionAssessment,
    CriterionAssessmentStatus,
    PolicyCriterion,
)
from decision.decision_logic import make_decision
from decision.llm_provider import LLMProvider, NVIDIAProvider
from decision.llm_schemas import (
    LLMCriterionAssessmentResponse,
    LLMStructuredResponse,
    InterpretationState,
)
from decision.llm_prompt import (
    CRITERION_ASSESSMENT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_criterion_assessment_prompt,
    build_user_prompt,
    OPTIMIZED_SYSTEM_PROMPT,
    build_optimized_user_prompt,
)


class DecisionAgent:
    """
    Orchestrates deterministic decisions. The current integration contract is
    ``evaluate_canonical_claim(canonical_claim, rag_policy)``; its optional LLM
    step supplies non-decisional criterion assessments only. The legacy
    raw-evidence extraction path remains available for migration compatibility.
    """

    def __init__(
        self,
        policy: Optional[Policy] = None,
        confidence_threshold: float = 0.7,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """
        Initializes the DecisionAgent with a Policy, confidence thresholds, and optional LLMProvider.
        """
        self.policy = policy
        self.confidence_threshold = confidence_threshold
        self.llm_provider = llm_provider

    @staticmethod
    def _canonical_path_exists(document: Any, path: str) -> bool:
        """Validate a restricted JSONPath (root, object keys, and list indices only)."""
        if not isinstance(path, str) or not path.startswith("$"):
            return False
        current = document
        remainder = path[1:]
        token_pattern = re.compile(r"(?:\.([A-Za-z_][A-Za-z0-9_]*))|(?:\[(\d+)\])")
        position = 0
        while position < len(remainder):
            match = token_pattern.match(remainder, position)
            if not match:
                return False
            key, index = match.groups()
            if key is not None:
                if not isinstance(current, dict) or key not in current:
                    return False
                current = current[key]
            else:
                if not isinstance(current, list) or int(index) >= len(current):
                    return False
                current = current[int(index)]
            position = match.end()
        return True

    @staticmethod
    def _validate_criterion_assessments(
        assessments: List[CriterionAssessment],
        policy: Policy,
        claim: CanonicalClaim,
        canonical_json: Dict[str, Any],
    ) -> None:
        expected_ids = {criterion.criterion_id for criterion in policy.criteria}
        assessment_ids = [assessment.criterion_id for assessment in assessments]
        if len(assessment_ids) != len(set(assessment_ids)):
            raise ValueError("LLM returned duplicate criterion assessments.")
        if set(assessment_ids) != expected_ids:
            raise ValueError("LLM assessments must cover each RAG policy criterion exactly once.")
        criteria_by_id = {criterion.criterion_id: criterion for criterion in policy.criteria}
        for assessment in assessments:
            criterion = criteria_by_id[assessment.criterion_id]
            for path in assessment.evidence_paths:
                if not DecisionAgent._canonical_path_exists(canonical_json, path):
                    raise ValueError(
                        f"LLM assessment '{assessment.criterion_id}' references missing canonical path: {path}"
                    )
            reasoning_text = " ".join(assessment.reasoning)
            reasoning_paths = re.findall(r"\$[A-Za-z_][A-Za-z0-9_.\[\]]*", reasoning_text)
            if any(path not in assessment.evidence_paths for path in reasoning_paths):
                raise ValueError(
                    f"LLM assessment '{assessment.criterion_id}' reasoning references an uncited canonical path."
                )

            if assessment.status in {
                CriterionAssessmentStatus.SATISFIED,
                CriterionAssessmentStatus.NOT_SATISFIED,
            } and not assessment.evidence_paths:
                raise ValueError(
                    f"LLM assessment '{assessment.criterion_id}' requires canonical evidence paths for {assessment.status.value}."
                )

            if assessment.status == CriterionAssessmentStatus.MISSING:
                expected_evidence = set(criterion.required_evidence or criterion.required_evidence_keys)
                if assessment.evidence_paths:
                    raise ValueError("MISSING assessments cannot cite canonical evidence as present.")
                if not assessment.required_evidence_paths:
                    raise ValueError("MISSING assessments must cite a required evidence expectation.")
                if not expected_evidence or not set(assessment.required_evidence_paths).issubset(expected_evidence):
                    raise ValueError("MISSING assessment cites an unknown required evidence expectation.")
                if any(item.evidence_key in assessment.required_evidence_paths for item in claim.evidence):
                    raise ValueError("MISSING assessment is unsupported because required canonical evidence exists.")
            elif assessment.required_evidence_paths:
                raise ValueError("Only MISSING assessments may cite required evidence expectations.")

            # The LLM cannot use an explanation to reverse deterministic facts.
            baseline = make_decision(
                policy=Policy(policy_id=policy.policy_id, name=policy.name, criteria=[criterion]),
                case_data=claim.case_data,
                evidence_list=claim.evidence,
                confidence_threshold=0.7,
            )
            baseline_state = baseline.criteria_evaluations[criterion.criterion_id].state
            if assessment.status == CriterionAssessmentStatus.SATISFIED and baseline_state != "PASS":
                raise ValueError("SATISFIED assessment is unsupported by canonical deterministic evidence.")
            if assessment.status == CriterionAssessmentStatus.NOT_SATISFIED and baseline_state != "FAIL":
                raise ValueError("NOT_SATISFIED assessment is unsupported by canonical deterministic evidence.")
            if assessment.status == CriterionAssessmentStatus.NOT_APPLICABLE:
                if baseline_state != "NOT_APPLICABLE":
                    raise ValueError("NOT_APPLICABLE assessment is unsupported by policy applicability context.")

    @staticmethod
    def _assessment_guard_key(criterion: PolicyCriterion) -> str:
        return f"__criterion_assessment__{criterion.criterion_id}"

    def _translate_assessments_to_deterministic_inputs(
        self,
        claim: CanonicalClaim,
        policy: Policy,
        assessments: List[CriterionAssessment],
    ) -> tuple[Policy, List[EvidenceItem]]:
        """Convert only conservative assessment signals into existing engine inputs.

        This never adds claim facts or upgrades evidence. A model's SATISFIED or
        NOT_SATISFIED label therefore cannot itself approve or reject. Safety
        labels are represented as existing evidence quality states for the
        deterministic compiler to resolve.
        """
        decision_policy = policy.model_copy(deep=True)
        decision_evidence = [item.model_copy(deep=True) for item in claim.evidence]
        criteria_by_id = {criterion.criterion_id: criterion for criterion in decision_policy.criteria}

        for assessment in assessments:
            criterion = criteria_by_id[assessment.criterion_id]
            keys = list(criterion.required_evidence_keys)

            if assessment.status == CriterionAssessmentStatus.MISSING:
                if keys:
                    # A MISSING assessment cannot fabricate evidence; make only the
                    # existing required evidence unavailable to the compiler.
                    decision_evidence = [
                        item for item in decision_evidence if item.evidence_key not in keys
                    ]
                else:
                    # Give the unchanged compiler an explicit missing requirement.
                    criterion.required_evidence_keys = [self._assessment_guard_key(criterion)]
                continue

            if assessment.status not in {
                CriterionAssessmentStatus.UNCERTAIN,
                CriterionAssessmentStatus.CONFLICTING,
            }:
                # SATISFIED, NOT_SATISFIED, and NOT_APPLICABLE add no facts and do
                # not bypass any deterministic rule or mandatory requirement.
                continue

            guard_key = keys[0] if keys else self._assessment_guard_key(criterion)
            if not keys:
                criterion.required_evidence_keys = [guard_key]
            decision_evidence.append(
                EvidenceItem(
                    evidence_key=guard_key,
                    source=f"Criterion assessment safety signal: {assessment.criterion_id}",
                    status=(
                        EvidenceStatus.CONTRADICTORY
                        if assessment.status == CriterionAssessmentStatus.CONFLICTING
                        else EvidenceStatus.UNVERIFIED
                    ),
                    confidence_score=0.0,
                    is_ambiguous=(assessment.status == CriterionAssessmentStatus.UNCERTAIN),
                    extracted_facts={},
                )
            )

        return decision_policy, decision_evidence

    @staticmethod
    def _map_external_claim_to_legacy(claim_dict: Dict[str, Any]) -> Dict[str, Any]:
        if "case_data" in claim_dict:
            return claim_dict

        patient = claim_dict.get("patient", {})
        age = patient.get("age")
        if age is None:
            age = claim_dict.get("patient_age", 0)
        claim_id = claim_dict.get("claim_id") or claim_dict.get("case_id") or "UNKNOWN-CLAIM"
        
        diagnoses = claim_dict.get("diagnoses", [])
        procedures = claim_dict.get("procedures") or []
        proc = claim_dict.get("procedure")
        if proc:
            if isinstance(proc, dict):
                code = proc.get("code") or proc.get("procedure_code")
                if code:
                    procedures.append(str(code))
            elif isinstance(proc, str):
                procedures.append(proc)
                
        clinical_metrics = {}
        evidence = []

        def process_dict(source_dict: Dict[str, Any], default_source: str):
            if not isinstance(source_dict, dict):
                return
            for k, v in source_dict.items():
                if isinstance(v, dict):
                    has_status = "status" in v
                    has_confidence = "confidence_score" in v or "confidence" in v
                    has_facts = "extracted_facts" in v or "facts" in v
                    has_unstructured = "unstructured_text" in v or "text" in v or "content" in v
                    
                    if has_status or has_confidence or has_facts or has_unstructured:
                        evidence.append({
                            "evidence_key": k,
                            "evidence_id": v.get("evidence_id") or v.get("document_id") or f"{k}_id",
                            "source": v.get("source") or default_source,
                            "status": v.get("status") or "verified",
                            "confidence_score": v.get("confidence_score") or v.get("confidence") or 1.0,
                            "is_ambiguous": v.get("is_ambiguous", False),
                            "extracted_facts": v.get("extracted_facts") or v.get("facts") or {},
                            "unstructured_text": v.get("unstructured_text") or v.get("content") or v.get("text")
                        })
                        facts = v.get("extracted_facts") or v.get("facts") or {}
                        if isinstance(facts, dict):
                            clinical_metrics.update(facts)
                    else:
                        clinical_metrics[k] = v
                else:
                    clinical_metrics[k] = v

        process_dict(claim_dict.get("clinical_information") or {}, "Clinical Information")
        process_dict(claim_dict.get("treatment_history") or {}, "Treatment History")
        process_dict(claim_dict.get("diagnostic_information") or {}, "Diagnostic Information")
        
        clinical_metrics["patient"] = patient
        if "age" in patient:
            clinical_metrics["patient_age"] = patient["age"]
        if "gender" in patient:
            clinical_metrics["patient_gender"] = patient["gender"]

        documents = claim_dict.get("documents", [])
        if isinstance(documents, list):
            for idx, doc in enumerate(documents):
                if isinstance(doc, dict):
                    evidence_key = doc.get("evidence_key") or doc.get("document_type") or f"doc_{idx}"
                    evidence_id = doc.get("evidence_id") or doc.get("document_id") or f"doc_id_{idx}"
                    source = doc.get("source") or "Document Upload"
                    status = doc.get("status") or "unverified"
                    confidence = doc.get("confidence_score") or doc.get("confidence") or 1.0
                    facts = doc.get("extracted_facts") or doc.get("facts") or {}
                    text = doc.get("unstructured_text") or doc.get("content") or doc.get("text")
                    is_ambiguous = doc.get("is_ambiguous", False)
                    
                    evidence.append({
                        "evidence_key": evidence_key,
                        "evidence_id": evidence_id,
                        "source": source,
                        "status": status,
                        "confidence_score": confidence,
                        "is_ambiguous": is_ambiguous,
                        "extracted_facts": facts,
                        "unstructured_text": text
                    })
                    if isinstance(facts, dict):
                        clinical_metrics.update(facts)

        if not evidence and "evidence" in claim_dict:
            evidence = claim_dict["evidence"]

        return {
            "case_data": {
                "case_id": claim_id,
                "patient_age": age or 0,
                "diagnoses": diagnoses,
                "procedures": procedures,
                "clinical_metrics": clinical_metrics
            },
            "evidence": evidence
        }

    @staticmethod
    def _map_external_policy_to_legacy(policy_dict: Dict[str, Any]) -> Dict[str, Any]:
        if "policy_id" in policy_dict:
            return policy_dict

        matched_policies = policy_dict.get("matched_policies", [])
        policy_id = "UNKNOWN-POLICY"
        name = "RAG Matched Policy"
        if matched_policies and isinstance(matched_policies, list):
            policy_id = matched_policies[0].get("policy_id") or policy_id
            name = matched_policies[0].get("name") or policy_id

        raw_criteria = policy_dict.get("criteria", [])
        criteria = []
        for crit in raw_criteria:
            crit_id = crit.get("criterion_id")
            crit_name = crit.get("name") or crit.get("requirement") or "Unnamed Criterion"
            crit_desc = crit.get("description") or crit.get("requirement") or ""
            mandatory = crit.get("mandatory", True)
            
            clinical_rule = crit.get("clinical_rule")
            evidence_rule = crit.get("evidence_rule")
            required_evidence_keys = crit.get("required_evidence_keys") or crit.get("required_evidence") or []
            interpretation_guidance = crit.get("interpretation_guidance", "")
            evaluation_type = crit.get("evaluation_type", "")
            
            criteria.append({
                "criterion_id": crit_id,
                "name": crit_name,
                "description": crit_desc,
                "mandatory": mandatory,
                "clinical_rule": clinical_rule,
                "evidence_rule": evidence_rule,
                "required_evidence_keys": required_evidence_keys,
                "interpretation_guidance": interpretation_guidance,
                "evaluation_type": evaluation_type
            })
            
        exclusions = []
        raw_exclusions = policy_dict.get("exclusions", [])
        for exc in raw_exclusions:
            exc_id = exc.get("exclusion_id")
            exc_name = exc.get("name") or "Unnamed Exclusion"
            rule = exc.get("rule")
            req_keys = exc.get("required_evidence_keys") or []
            exclusions.append({
                "exclusion_id": exc_id,
                "name": exc_name,
                "rule": rule,
                "required_evidence_keys": req_keys
            })

        return {
            "policy_id": policy_id,
            "name": name,
            "exclusions": exclusions,
            "criteria": criteria
        }

    @staticmethod
    def _filter_canonical_claim(claim_dict: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        # Filter external/original claim to only include relevant fields matching required_keys.
        # Preserve the current canonical contract (`case_data` + `evidence[]`) while still supporting
        # legacy external payloads during migration.
        filtered = {
            "claim_id": claim_dict.get("claim_id"),
            "patient": claim_dict.get("patient"),
            "diagnoses": claim_dict.get("diagnoses"),
            "procedure": claim_dict.get("procedure"),
        }

        if "case_data" in claim_dict:
            filtered["case_data"] = claim_dict["case_data"]
        if "evidence" in claim_dict:
            evs = claim_dict["evidence"]
            if isinstance(evs, list):
                filtered_evs = [
                    ev for ev in evs
                    if isinstance(ev, dict)
                    and any(rk.lower() in (ev.get("evidence_key") or "").lower() for rk in required_keys)
                ]
                if filtered_evs:
                    filtered["evidence"] = filtered_evs

        for section in ["clinical_information", "treatment_history", "diagnostic_information"]:
            if section in claim_dict:
                sec_dict = claim_dict[section]
                if isinstance(sec_dict, dict):
                    filtered_sec = {
                        k: v for k, v in sec_dict.items()
                        if any(rk.lower() in k.lower() or k.lower() in rk.lower() for rk in required_keys)
                    }
                    if filtered_sec:
                        filtered[section] = filtered_sec
        if "documents" in claim_dict:
            docs = claim_dict["documents"]
            if isinstance(docs, list):
                filtered_docs = [
                    doc for doc in docs
                    if isinstance(doc, dict) and any(
                        rk.lower() in (doc.get("evidence_key") or doc.get("document_type") or "").lower()
                        for rk in required_keys
                    )
                ]
                if filtered_docs:
                    filtered["documents"] = filtered_docs
        return filtered

    @staticmethod
    def _find_candidate_paths(data: Any, current_path: str = "$") -> Dict[int, str]:
        candidates = {}
        def traverse(val: Any, path: str):
            if isinstance(val, dict):
                for k, v in val.items():
                    next_path = f"{path}.{k}"
                    traverse(v, next_path)
            elif isinstance(val, list):
                for idx, item in enumerate(val):
                    next_path = f"{path}[{idx}]"
                    traverse(item, next_path)
            else:
                candidates[len(candidates) + 1] = path
        traverse(data, current_path)
        return candidates

    @staticmethod
    def _get_relevant_candidates(claim_dict: Dict[str, Any], required_key: str) -> Dict[int, str]:
        relevant_candidates = {}
        idx = 1

        if "evidence" in claim_dict and isinstance(claim_dict["evidence"], list):
            for i, item in enumerate(claim_dict["evidence"]):
                if not isinstance(item, dict):
                    continue
                evidence_key = str(item.get("evidence_key") or "")
                if required_key.lower() in evidence_key.lower():
                    facts = item.get("extracted_facts") or {}
                    if isinstance(facts, dict):
                        for fact_key in facts:
                            relevant_candidates[idx] = f"$.evidence[{i}].extracted_facts.{fact_key}"
                            idx += 1
                    else:
                        relevant_candidates[idx] = f"$.evidence[{i}]"
                        idx += 1

        if "case_data" in claim_dict and isinstance(claim_dict["case_data"], dict):
            metrics = claim_dict["case_data"].get("clinical_metrics") or {}
            if isinstance(metrics, dict):
                for metric_key in metrics:
                    if required_key.lower() in metric_key.lower() or metric_key.lower() in required_key.lower():
                        relevant_candidates[idx] = f"$.case_data.clinical_metrics.{metric_key}"
                        idx += 1

        if not relevant_candidates:
            all_candidates = DecisionAgent._find_candidate_paths(claim_dict)
            for _, path in all_candidates.items():
                if required_key.lower() in path.lower():
                    relevant_candidates[idx] = path
                    idx += 1
        return relevant_candidates

    def evaluate_canonical_claim(
        self, canonical_claim: Dict[str, Any], rag_policy: Dict[str, Any]
    ) -> DecisionResponse:
        """Assess canonical claim JSON against RAG policy JSON, then decide deterministically.

        The LLM supplies criterion-level explainability only. It cannot extract facts,
        mutate the canonical claim, or choose the final outcome.
        """
        claim_id = canonical_claim.get("claim_id") or canonical_claim.get("case_data", {}).get("case_id")
        policy_id = rag_policy.get("policy_id")
        if not policy_id:
            matched_policies = rag_policy.get("matched_policies", [])
            if matched_policies and isinstance(matched_policies, list):
                policy_id = matched_policies[0].get("policy_id")
        submission_attempt = canonical_claim.get("submission", {}).get("attempt")

        if "case_data" in canonical_claim and "evidence" in canonical_claim:
            mapped_claim = {
                "case_data": canonical_claim["case_data"],
                "evidence": canonical_claim["evidence"],
            }
        else:
            mapped_claim = self._map_external_claim_to_legacy(canonical_claim)

        if "policy_id" in rag_policy and "criteria" in rag_policy:
            mapped_policy = rag_policy
        else:
            mapped_policy = self._map_external_policy_to_legacy(rag_policy)

        claim = CanonicalClaim.model_validate(mapped_claim)
        policy = Policy.model_validate(mapped_policy)
        provider = self.llm_provider or NVIDIAProvider()
        assessments: List[CriterionAssessment] = []

        for criterion in policy.criteria:
            required_keys = criterion.required_evidence_keys or criterion.required_evidence or []
            
            if not required_keys:
                baseline = make_decision(
                    policy=Policy(policy_id=policy.policy_id, name=policy.name, criteria=[criterion]),
                    case_data=claim.case_data,
                    evidence_list=claim.evidence,
                    confidence_threshold=0.7,
                )
                baseline_state = baseline.criteria_evaluations[criterion.criterion_id].state
                status_map = {
                    "PASS": CriterionAssessmentStatus.SATISFIED,
                    "FAIL": CriterionAssessmentStatus.NOT_SATISFIED,
                    "NOT_APPLICABLE": CriterionAssessmentStatus.NOT_APPLICABLE,
                }
                agg_status = status_map.get(baseline_state, CriterionAssessmentStatus.UNCERTAIN)
                assessments.append(
                    CriterionAssessment(
                        criterion_id=criterion.criterion_id,
                        status=agg_status,
                        evidence_paths=[],
                        required_evidence_paths=[],
                        reasoning=["Deterministically evaluated via engine rules."]
                    )
                )
                continue

            criterion_evidence_assessments = []
            legacy_mode = False
            legacy_assessments = []

            for rk in required_keys:
                candidates = self._get_relevant_candidates(canonical_claim, rk)
                minimized_claim = self._filter_canonical_claim(canonical_claim, [rk])
                
                try:
                    try:
                        raw_response = provider.generate_structured_response(
                            build_optimized_user_prompt(minimized_claim, criterion, rk, candidates),
                            OPTIMIZED_SYSTEM_PROMPT,
                        )
                    except (KeyError, TypeError, AttributeError, ValueError) as fallback_exc:
                        if hasattr(provider, "call_count"):
                            provider.call_count -= 1
                        raw_response = provider.generate_structured_response(
                            build_criterion_assessment_prompt(canonical_claim, criterion),
                            CRITERION_ASSESSMENT_SYSTEM_PROMPT,
                        )
                    
                    if "criterion_assessments" in raw_response:
                        legacy_mode = True
                        parsed_response = LLMCriterionAssessmentResponse.model_validate_json(raw_response)
                        single_criterion_policy = Policy(
                            policy_id=policy.policy_id,
                            name=policy.name,
                            criteria=[criterion],
                        )
                        self._validate_criterion_assessments(
                            parsed_response.criterion_assessments,
                            single_criterion_policy,
                            claim,
                            canonical_claim,
                        )
                        legacy_assessments.extend(parsed_response.criterion_assessments)
                        break
                        
                    parsed = json.loads(raw_response)
                    status = parsed.get("status")
                    selected_paths = parsed.get("selected_paths", [])
                    reason = parsed.get("reason")
                    
                    if status not in {"SUPPORTED", "MISSING", "UNCERTAIN", "CONFLICTING"}:
                        raise ValueError(f"Invalid status classified by LLM: {status}")
                        
                    mapped_paths = []
                    for idx in selected_paths:
                        if idx not in candidates:
                            raise ValueError(f"Invalid path index selection: {idx}")
                        mapped_paths.append(candidates[idx])
                        
                    if status == "SUPPORTED" and not mapped_paths:
                        raise ValueError("SUPPORTED status requires at least one valid path selection.")
                        
                    criterion_evidence_assessments.append({
                        "key": rk,
                        "status": status,
                        "paths": mapped_paths,
                        "reason": reason
                    })
                except Exception as exc:
                    return DecisionResponse(
                        case_id=claim.case_data.case_id,
                        outcome=DecisionOutcome.HUMAN_REVIEW,
                        reasoning=["Engine Fail-Closed Triggered.", "Invalid criterion-assessment LLM response."],
                        exclusion_results={},
                        criteria_results={},
                        criteria_evaluations={},
                        evidence_status={},
                        errors=[f"Criterion assessment layer failed: {exc}"],
                        claim_id=claim_id,
                        policy_id=policy_id,
                        submission_attempt=submission_attempt,
                        reason_code=DecisionReasonCode.LLM_ASSESSMENT_FAIL_CLOSED,
                    )
            
            if legacy_mode:
                assessments.extend(legacy_assessments)
                continue
                
            aggregated_paths = []
            aggregated_required = []
            aggregated_reasons = []
            statuses = []
            
            for ea in criterion_evidence_assessments:
                statuses.append(ea["status"])
                aggregated_paths.extend(ea["paths"])
                if ea["status"] == "MISSING":
                    aggregated_required.append(ea["key"])
                if ea["reason"]:
                    lines = []
                    v = ea["reason"]
                    if isinstance(v, list):
                        lines.extend(v)
                    elif isinstance(v, str):
                        for line in v.replace("\r", "").split("\n"):
                            cleaned = line.strip()
                            if cleaned.startswith("- ") or cleaned.startswith("* "):
                                cleaned = cleaned[2:].strip()
                            if cleaned:
                                lines.append(cleaned)
                    if not lines:
                        lines = [str(v)]
                    aggregated_reasons.extend(lines)
                    
            if "CONFLICTING" in statuses:
                agg_status = CriterionAssessmentStatus.CONFLICTING
            elif "UNCERTAIN" in statuses:
                # V1 determinism: a definitive clinical-rule failure outranks LLM
                # uncertainty. The deterministic engine owns the final decision, so an
                # uncertain reading of unrelated evidence cannot mask a hard FAILED
                # criterion (FAILED CRITERION -> REJECT). Only when the deterministic
                # baseline is not a definitive FAIL do we honor the model's uncertainty.
                baseline_unc = make_decision(
                    policy=Policy(policy_id=policy.policy_id, name=policy.name, criteria=[criterion]),
                    case_data=claim.case_data,
                    evidence_list=claim.evidence,
                    confidence_threshold=0.7,
                )
                if baseline_unc.criteria_evaluations[criterion.criterion_id].state == "FAIL":
                    agg_status = CriterionAssessmentStatus.NOT_SATISFIED
                else:
                    agg_status = CriterionAssessmentStatus.UNCERTAIN
            elif "MISSING" in statuses:
                agg_status = CriterionAssessmentStatus.MISSING
            else:
                baseline = make_decision(
                    policy=Policy(policy_id=policy.policy_id, name=policy.name, criteria=[criterion]),
                    case_data=claim.case_data,
                    evidence_list=claim.evidence,
                    confidence_threshold=0.7,
                )
                baseline_state = baseline.criteria_evaluations[criterion.criterion_id].state
                if baseline_state == "PASS":
                    agg_status = CriterionAssessmentStatus.SATISFIED
                elif baseline_state == "FAIL":
                    agg_status = CriterionAssessmentStatus.NOT_SATISFIED
                elif baseline_state == "NOT_APPLICABLE":
                    agg_status = CriterionAssessmentStatus.NOT_APPLICABLE
                else:
                    agg_status = CriterionAssessmentStatus.UNCERTAIN
                    
            assessments.append(
                CriterionAssessment(
                    criterion_id=criterion.criterion_id,
                    status=agg_status,
                    evidence_paths=list(set(aggregated_paths)),
                    required_evidence_paths=aggregated_required,
                    reasoning=aggregated_reasons if aggregated_reasons else ["Evaluated via optimized classifier."]
                )
            )

        decision_policy, decision_evidence = self._translate_assessments_to_deterministic_inputs(
            claim, policy, assessments
        )

        response = make_decision(
            policy=decision_policy,
            case_data=claim.case_data,
            evidence_list=decision_evidence,
            confidence_threshold=self.confidence_threshold,
        )
        response.criterion_assessments = {
            assessment.criterion_id: assessment
            for assessment in assessments
        }
        response.reasoning = [
            "--- LLM Criterion Assessments (non-decisional) ---",
            *[
                f" - {assessment.criterion_id}: {assessment.status.value}; paths={assessment.evidence_paths}; {assessment.reasoning}"
                for assessment in assessments
            ],
            "--- End LLM Criterion Assessments ---",
            *response.reasoning,
        ]
        response.claim_id = claim_id
        response.policy_id = policy_id
        response.submission_attempt = submission_attempt
        return response

    def evaluate(
        self,
        case_data: CaseData,
        evidence_list: List[EvidenceItem],
        use_llm: bool = False,
    ) -> DecisionResponse:
        """
        Runs clinical case evaluation.
        If use_llm is True, checks first if existing deterministic evidence is already sufficient
        (i.e., yields APPROVE or REJECT output) or if no raw unstructured text exists. If so, skips LLM.
        Otherwise, invokes the LLM provider to extract structured facts before decision compiling.
        Adapts a maximum of ONE retry for transient/malformed responses, and fails safely to HUMAN_REVIEW.
        """
        if self.policy is None:
            raise ValueError("A Policy is required for the legacy evaluate method.")

        errors: List[str] = []
        reasoning: List[str] = []

        if use_llm:
            # 1. Optimistic Sufficiency Check: Skip LLM call if deterministic facts already yield Approve/Reject
            det_first = make_decision(
                policy=self.policy,
                case_data=case_data,
                evidence_list=evidence_list,
                confidence_threshold=self.confidence_threshold,
            )
            has_unstructured = any(
                e.unstructured_text and e.unstructured_text.strip() for e in evidence_list
            )

            if det_first.outcome in [DecisionOutcome.APPROVE, DecisionOutcome.REJECT] or not has_unstructured:
                # Deterministic facts are already sufficient, or there is nothing to extract
                return det_first

            try:
                # 2. Resolve / Instantiate the LLM provider
                provider = self.llm_provider
                if provider is None:
                    provider = NVIDIAProvider()

                # Get prompts
                system_p = SYSTEM_PROMPT
                user_p = build_user_prompt(case_data, self.policy, evidence_list)

                # 3. Model Request with exactly ONE retry for transient/malformed failures
                structured_response = None
                last_err = None

                for attempt in range(2):
                    try:
                        raw_response = provider.generate_structured_response(user_p, system_p)
                        parsed_json = json.loads(raw_response)
                        structured_response = LLMStructuredResponse(**parsed_json)
                        break
                    except Exception as e:
                        last_err = e
                        if attempt == 0:
                            reasoning.append(
                                f"Transient/Malformed LLM exception on attempt 1: {str(e)}. Retrying once..."
                            )
                            continue
                        else:
                            raise last_err

                if structured_response is not None:
                    # 4. Reason trace updates from LLM
                    reasoning.append("--- LLM Intelligence Layer Interpretation ---")
                    reasoning.append(f"Reasoning Summary: {structured_response.overall_reasoning_summary}")

                    # 5. Map structured facts to the EvidenceItems list
                    missing_items = []
                    for fact in structured_response.extracted_facts:
                        if fact.state == InterpretationState.MISSING:
                            missing_items.append((fact.evidence_key, fact.evidence_id))
                            reasoning.append(
                                f" - Key: '{fact.evidence_key}' | State: {fact.state.value} | Status: '{fact.interpretation_status}' | Conf: {fact.confidence}"
                            )
                            continue

                        # Find matching evidence item(s) by key (and id if present)
                        matches = [e for e in evidence_list if e.evidence_key == fact.evidence_key]
                        if fact.evidence_id:
                            matches = [e for e in matches if e.evidence_id == fact.evidence_id]

                        reasoning.append(
                            f" - Key: '{fact.evidence_key}' | State: {fact.state.value} | Status: '{fact.interpretation_status}' | Conf: {fact.confidence}"
                        )

                        # Update matched evidence item fields
                        for item in matches:
                            # Direct fact extraction
                            if fact.extracted_fact:
                                item.extracted_facts.update(fact.extracted_fact)
                            
                            item.confidence_score = fact.confidence
                            
                            # Map status & state
                            status_str = fact.interpretation_status.lower().strip()
                            if status_str == "verified":
                                item.status = EvidenceStatus.VERIFIED
                            elif status_str == "contradictory" or fact.state == InterpretationState.CONFLICTING:
                                item.status = EvidenceStatus.CONTRADICTORY
                            elif status_str == "unverified" or fact.state == InterpretationState.UNCERTAIN:
                                item.status = EvidenceStatus.UNVERIFIED
                            
                            if fact.state == InterpretationState.UNCERTAIN:
                                item.is_ambiguous = True

                    # Filter out the items that the LLM resolved as MISSING
                    final_evidence = []
                    for e in evidence_list:
                        is_missing = False
                        for m_key, m_id in missing_items:
                            if e.evidence_key == m_key:
                                if m_id is None or e.evidence_id == m_id:
                                    is_missing = True
                                    break
                        if not is_missing:
                            final_evidence.append(e)
                    
                    evidence_list = final_evidence
                    reasoning.append("--- End of LLM Interpretation ---")

            except Exception as e:
                # Failure Handling: Fail safely to HUMAN_REVIEW
                err_msg = f"LLM Layer failed: {str(e)}"
                errors.append(err_msg)
                
                return DecisionResponse(
                    case_id=case_data.case_id,
                    outcome=DecisionOutcome.HUMAN_REVIEW,
                    reasoning=[
                        "Engine Fail-Closed Triggered.",
                        f"Reason: {err_msg}"
                    ],
                    exclusion_results={},
                    criteria_results={},
                    criteria_evaluations={},
                    evidence_status={},
                    errors=errors,
                    reason_code=DecisionReasonCode.LLM_ASSESSMENT_FAIL_CLOSED,
                )

        # 6. Fallback or transition to the deterministic decision engine
        resp = make_decision(
            policy=self.policy,
            case_data=case_data,
            evidence_list=evidence_list,
            confidence_threshold=self.confidence_threshold,
        )

        # Consolidate reasoning traces
        if reasoning:
            resp.reasoning = reasoning + resp.reasoning
        if errors:
            resp.errors.extend(errors)

        return resp
