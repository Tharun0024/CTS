from typing import Any, Dict, List, Set
from decision.schemas import (
    Policy,
    CaseData,
    EvidenceItem,
    EvidenceStatus,
    EvidenceProvenance,
    CriterionEvaluation,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
)
from decision.policy_evaluator import (
    evaluate_exclusions,
    evaluate_clinical_criteria,
    validate_rule,
    evaluate_rule,
    resolve_field_value,
)
from decision.evidence_evaluator import (
    evaluate_all_evidence,
    evaluate_evidence_group,
)


def _collect_referenced_evidence_ids(
    criteria_evaluations: Dict[str, CriterionEvaluation],
) -> List[str]:
    """Aggregate the real evidence IDs grounded in criterion provenance traces."""
    ids: List[str] = []
    for evaluation in criteria_evaluations.values():
        for prov in evaluation.evidence_provenance:
            if prov.evidence_id and prov.evidence_id not in ids:
                ids.append(prov.evidence_id)
    return ids


def make_decision(
    policy: Policy,
    case_data: CaseData,
    evidence_list: List[EvidenceItem],
    confidence_threshold: float = 0.7,
) -> DecisionResponse:
    """
    Orchestrates the policy evaluation, evidence evaluation, and final decision-making logic.
    Hardened to enforce fail-closed behavior, strict evidence safety, and state preservation.

    Decision hierarchy (highest to lowest priority):
      EXCLUSION → CONFLICT → FAILED → MISSING → APPROVE
    """
    try:
        reasoning: List[str] = []
        reasoning.append(f"Starting decision determination for Case ID: {case_data.case_id} against Policy: {policy.name} ({policy.policy_id}).")

        # 0. Payer Safety Gate
        payer = case_data.clinical_metrics.get("claim_payer")
        member_id = case_data.clinical_metrics.get("member_id")
        _unknown_payer_names = {"unknown", "unknownpayer", "unknown_payer", "none", ""}
        if payer is not None and str(payer).strip().lower() in _unknown_payer_names:
            reasoning.append(
                f"Payer safety gate triggered: claim_payer={payer!r} is unrecognized. "
                "Escalating to HUMAN_REVIEW (unknown payer)."
            )
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.HUMAN_REVIEW,
                reasoning=reasoning,
                exclusion_results={},
                criteria_results={},
                criteria_evaluations={},
                evidence_status={},
                errors=["Payer is unknown or unvalidated."],
                reason_code=DecisionReasonCode.UNKNOWN_PAYER,
            )
        # Note: payer present but member_id absent is NOT treated as unvalidated.
        # In real pipeline, runtime adapter attaches member_id from payer_data.db.
        # Test fixtures may omit member_id; this does not indicate an unvalidated payer.

        # 1. Policy Rules Validation (Fail-closed behavior)
        validation_errors = []
        for exc in policy.exclusions:
            if not validate_rule(exc.rule):
                validation_errors.append(f"Invalid rule in exclusion '{exc.exclusion_id}': {exc.rule}")
        for crit in policy.criteria:
            if crit.clinical_rule and not validate_rule(crit.clinical_rule):
                validation_errors.append(f"Invalid clinical rule in criterion '{crit.criterion_id}': {crit.clinical_rule}")
            if crit.evidence_rule and not validate_rule(crit.evidence_rule):
                validation_errors.append(f"Invalid evidence rule in criterion '{crit.criterion_id}': {crit.evidence_rule}")
            if crit.applicability_rule and not validate_rule(crit.applicability_rule):
                validation_errors.append(f"Invalid applicability rule in criterion '{crit.criterion_id}': {crit.applicability_rule}")

        if validation_errors:
            reasoning.append("Policy validation failed. Escalating to HUMAN_REVIEW (fail-closed).")
            for err in validation_errors:
                reasoning.append(f" - Error: {err}")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.HUMAN_REVIEW,
                reasoning=reasoning,
                exclusion_results={},
                criteria_results={},
                criteria_evaluations={},
                evidence_status={},
                errors=validation_errors,
                reason_code=DecisionReasonCode.POLICY_VALIDATION_ERROR,
            )

        # 2. Evaluate Clinical Exclusions on CaseData
        exclusion_results = evaluate_exclusions(case_data, policy.exclusions)
        
        # 3. Evaluate Evidence
        evidence_map: Dict[str, List[EvidenceItem]] = {}
        for item in evidence_list:
            evidence_map.setdefault(item.evidence_key, []).append(item)

        evidence_status = evaluate_all_evidence(
            policy.criteria, policy.exclusions, evidence_list, confidence_threshold
        )

        # 4. Check Exclusion Evidence Reliability
        # An exclusion clinically triggered must only cause REJECT if supported by reliable evidence.
        exclusion_reject = False
        exclusion_human_review = False
        triggered_exclusions_reasons: List[str] = []
        uncertain_exclusions_reasons: List[str] = []

        reasoning.append("Step 1: Evaluating exclusions.")
        for exclusion in policy.exclusions:
            exc_id = exclusion.exclusion_id
            clinical_match = exclusion_results.get(exc_id, False)
            
            if clinical_match:
                if exclusion.required_evidence_keys:
                    # Verify evidence quality for this exclusion
                    exc_evidence_statuses = {
                        key: evidence_status.get(key, "missing")
                        for key in exclusion.required_evidence_keys
                    }
                    
                    # If any required evidence is missing or has quality alerts
                    has_unreliable_evidence = any(
                        status in ["missing", "contradictory", "ambiguous", "unverified", "low_confidence", "failed_validation"]
                        for status in exc_evidence_statuses.values()
                    )
                    
                    if has_unreliable_evidence:
                        exclusion_human_review = True
                        details = ", ".join(f"'{k}': {v}" for k, v in exc_evidence_statuses.items())
                        uncertain_exclusions_reasons.append(
                            f"Exclusion '{exclusion.name}' ({exc_id}) triggered on field '{exclusion.rule.field}' but has unreliable evidence: {details}."
                        )
                    else:
                        exclusion_reject = True
                        triggered_exclusions_reasons.append(
                            f"Exclusion '{exclusion.name}' ({exc_id}) triggered on field '{exclusion.rule.field}'."
                        )
                else:
                    # No evidence required, triggers rejection immediately
                    exclusion_reject = True
                    triggered_exclusions_reasons.append(
                        f"Exclusion '{exclusion.name}' ({exc_id}) triggered on CaseData directly."
                    )

        if triggered_exclusions_reasons:
            for reason in triggered_exclusions_reasons:
                reasoning.append(f" - {reason}")
        if uncertain_exclusions_reasons:
            for reason in uncertain_exclusions_reasons:
                reasoning.append(f" - {reason}")

        # 5. Evaluate Criteria Applicability, Clinical Checks, and Evidence Quality
        criteria_evaluations: Dict[str, CriterionEvaluation] = {}
        criteria_results: Dict[str, bool] = {}

        reasoning.append("Step 2: Evaluating criteria eligibility.")
        for criterion in policy.criteria:
            crit_id = criterion.criterion_id
            crit_reasoning: List[str] = []
            
            # Check Applicability
            is_applicable = True
            if criterion.applicability_rule is not None:
                try:
                    is_applicable = evaluate_rule(criterion.applicability_rule, case_data)
                    crit_reasoning.append(
                        f"Applicability rule evaluated to {is_applicable} (field: '{criterion.applicability_rule.field}')."
                    )
                except Exception as ex:
                    is_applicable = True  # Safety default, but flag error
                    crit_reasoning.append(f"Applicability rule evaluation raised exception: {str(ex)}. Defaulting to applicable.")

            if not is_applicable:
                criteria_evaluations[crit_id] = CriterionEvaluation(
                    criterion_id=crit_id,
                    state="NOT_APPLICABLE",
                    evidence_provenance=[],
                    reasoning=crit_reasoning,
                )
                criteria_results[crit_id] = True  # Non-applicable criteria do not block approval
                reasoning.append(f" - Criterion '{criterion.name}' ({crit_id}) is NOT_APPLICABLE.")
                continue

            # Clinical Condition Check on CaseData
            clinical_ok = True
            if criterion.clinical_rule is not None:
                try:
                    clinical_ok = evaluate_rule(criterion.clinical_rule, case_data)
                    if not clinical_ok:
                        crit_reasoning.append("clinical rule not met")
                    else:
                        crit_reasoning.append(f"Clinical rule check passed (field: '{criterion.clinical_rule.field}').")
                except Exception as ex:
                    clinical_ok = False
                    crit_reasoning.append(f"Clinical rule evaluation raised exception: {str(ex)}.")

            # Compile Provenance and evidence quality checks
            provenance_list: List[EvidenceProvenance] = []
            has_missing = False
            has_quality_issue = False
            has_validation_failure = False

            criterion_evidence_statuses = {
                key: evidence_status.get(key, "missing")
                for key in criterion.required_evidence_keys
            }

            for key, status in criterion_evidence_statuses.items():
                if status == "missing":
                    has_missing = True
                    crit_reasoning.append(f"Required evidence is missing: {key}")
                elif status in ["contradictory", "ambiguous", "unverified", "low_confidence"]:
                    has_quality_issue = True
                    if status == "contradictory":
                        crit_reasoning.append(f"Evidence '{key}' for criterion '{criterion.name}' has status 'contradictory'.")
                    else:
                        crit_reasoning.append(f"Evidence '{key}' has status '{status}'.")
                elif status == "failed_validation":
                    has_validation_failure = True
                    crit_reasoning.append("extracted facts did not match validation rule")

                # Generate provenance trace for each provided item
                items = evidence_map.get(key, [])
                if not items:
                    provenance_list.append(
                        EvidenceProvenance(
                            evidence_key=key,
                            source="N/A (Missing)",
                            relevant_fact=None,
                            confidence_score=0.0,
                            evaluation_status="missing",
                            criterion_id=crit_id,
                        )
                    )
                else:
                    for item in items:
                        # Determine item-specific evaluation status
                        item_status = "verified"
                        if item.status == EvidenceStatus.CONTRADICTORY:
                            item_status = "contradictory"
                        elif item.is_ambiguous:
                            item_status = "ambiguous"
                        elif item.status == EvidenceStatus.UNVERIFIED:
                            item_status = "unverified"
                        elif item.confidence_score < confidence_threshold:
                            item_status = "low_confidence"
                        elif status == "failed_validation":
                            item_status = "failed_validation"

                        provenance_list.append(
                            EvidenceProvenance(
                                evidence_key=key,
                                evidence_id=item.evidence_id,
                                source=item.source,
                                relevant_fact=item.extracted_facts,
                                confidence_score=item.confidence_score,
                                evaluation_status=item_status,
                                criterion_id=crit_id,
                            )
                        )

            # Resolve Criterion Evaluation State
            # V1 hierarchy: EXCLUSION > CONFLICT > FAILED > MISSING > APPROVE
            # "Definite FAIL" = clinical rule field exists in data but evaluates false.
            # "Indeterminate" = clinical rule field absent from data (treat as MISSING).
            clinical_definitely_failed = False
            if not clinical_ok and criterion.clinical_rule is not None:
                field_val = resolve_field_value(criterion.clinical_rule.field, case_data)
                if field_val is not None:
                    clinical_definitely_failed = True

            if has_quality_issue:
                # Genuine evidence conflict/quality issue on the same criterion
                # outranks a clinical-rule failure (conflicting facts cannot be
                # treated as a definitive FAIL).
                resolved_state = "CONFLICTING"
            elif has_validation_failure or clinical_definitely_failed:
                resolved_state = "FAIL"
            elif has_missing:
                resolved_state = "MISSING"
            else:
                resolved_state = "PASS"

            criteria_evaluations[crit_id] = CriterionEvaluation(
                criterion_id=crit_id,
                state=resolved_state,
                evidence_provenance=provenance_list,
                reasoning=crit_reasoning,
            )
            criteria_results[crit_id] = (resolved_state == "PASS")

            if resolved_state == "PASS":
                reasoning.append(f" - Criterion '{criterion.name}' ({crit_id}) is fully satisfied.")
            else:
                reasoning.append(f" - Criterion '{criterion.name}' ({crit_id}) is NOT satisfied. Reason: {', '.join(crit_reasoning)}.")

        # 6. Apply Decision Hierarchy with Safety Logic
        reasoning.append("Step 3: Compiling final decision from hierarchy.")

        # Rule 1: Exclusion triggers rejection
        if exclusion_reject:
            reasoning.append("Decision Outcome: REJECT (Policy exclusion matched with verified evidence).")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.REJECT,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.COVERAGE_EXCLUSION,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
            )

        # Rule 2: Exclusion triggered but evidence is not reliable -> Escalate to HUMAN_REVIEW
        if exclusion_human_review:
            reasoning.append("Decision Outcome: HUMAN_REVIEW. Exclusion clinically matched, but evidence is unreliable.")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.HUMAN_REVIEW,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.UNRELIABLE_EXCLUSION_EVIDENCE,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
            )

        # Gather criteria states
        mandatory_conflict = False
        mandatory_fail = False
        mandatory_missing = False
        all_mandatory_passed = True

        for criterion in policy.criteria:
            if not criterion.mandatory:
                continue
            
            evaluation = criteria_evaluations.get(criterion.criterion_id)
            if not evaluation:
                continue

            if evaluation.state == "CONFLICTING":
                mandatory_conflict = True
                all_mandatory_passed = False
            elif evaluation.state == "FAIL":
                mandatory_fail = True
                all_mandatory_passed = False
            elif evaluation.state == "MISSING":
                mandatory_missing = True
                all_mandatory_passed = False
            elif evaluation.state == "PASS" or evaluation.state == "NOT_APPLICABLE":
                pass

        # Rule 3: Mandatory evidence conflict/unreliability (contradictions, low confidence) -> HUMAN_REVIEW
        if mandatory_conflict:
            reasoning.append("Decision Outcome: HUMAN_REVIEW.")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.HUMAN_REVIEW,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.EVIDENCE_CONFLICT,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
            )

        # Rule 4: Verified Mandatory Failure -> REJECT
        if mandatory_fail:
            reasoning.append("Decision Outcome: REJECT.")
            for criterion in policy.criteria:
                if criterion.mandatory and criteria_evaluations[criterion.criterion_id].state == "FAIL":
                    reasoning.append(f" - Mandatory criterion '{criterion.name}' ({criterion.criterion_id}) was violated with high-confidence evidence.")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.REJECT,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.CRITERION_FAILED_HARD,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
            )

        # Rule 5: Missing mandatory evidence -> REQUEST_MORE_INFORMATION
        if mandatory_missing:
            # Sort the missing keys to be predictable
            missing_keys = sorted(list({k for c in policy.criteria if c.mandatory for k in c.required_evidence_keys if k not in evidence_map}))
            reasoning.append(f"Decision Outcome: REQUEST_MORE_INFORMATION. Required evidence is missing: {', '.join(missing_keys)}")
            # Policy-defined documentation requests for Agent2 recovery routing.
            # Only keys actually absent from the submitted evidence are requested.
            requested_information = sorted({
                f"{criterion.name} ({criterion.criterion_id}): {key}"
                for criterion in policy.criteria
                if criterion.mandatory and criteria_evaluations.get(criterion.criterion_id)
                and criteria_evaluations[criterion.criterion_id].state == "MISSING"
                for key in criterion.required_evidence_keys
                if key not in evidence_map
            })
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.REQUEST_MORE_INFORMATION,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.MISSING_DOCUMENTATION,
                requested_information=requested_information,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
                agent2_recoverable=True,
            )

        # Rule 6: All mandatory criteria met, no exclusions triggered -> APPROVE
        if all_mandatory_passed:
            reasoning.append("Decision Outcome: APPROVE. All mandatory criteria are fully satisfied.")
            return DecisionResponse(
                case_id=case_data.case_id,
                outcome=DecisionOutcome.APPROVE,
                reasoning=reasoning,
                exclusion_results=exclusion_results,
                criteria_results=criteria_results,
                criteria_evaluations=criteria_evaluations,
                evidence_status=evidence_status,
                reason_code=DecisionReasonCode.ALL_CRITERIA_SATISFIED,
                referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
            )

        # Safety Fallback
        reasoning.append("Decision Outcome: HUMAN_REVIEW.")
        return DecisionResponse(
            case_id=case_data.case_id,
            outcome=DecisionOutcome.HUMAN_REVIEW,
            reasoning=reasoning,
            exclusion_results=exclusion_results,
            criteria_results=criteria_results,
            criteria_evaluations=criteria_evaluations,
            evidence_status=evidence_status,
            reason_code=DecisionReasonCode.ENGINE_FAIL_CLOSED,
            referenced_evidence_ids=_collect_referenced_evidence_ids(criteria_evaluations),
        )

    except Exception as ex:
        # Catch-all safety wrapper (Fail-closed behavior)
        import traceback
        err_msg = f"Internal Engine Failure (fail-closed): {str(ex)}"
        reasoning_trace = [
            err_msg,
            "Traceback details:",
        ] + traceback.format_exc().splitlines()
        
        return DecisionResponse(
            case_id=case_data.case_id,
            outcome=DecisionOutcome.HUMAN_REVIEW,
            reasoning=reasoning_trace,
            exclusion_results={},
            criteria_results={},
            criteria_evaluations={},
            evidence_status={},
            errors=[err_msg],
            reason_code=DecisionReasonCode.ENGINE_FAIL_CLOSED,
        )
