"""Phase 1 — Deterministic Prior Authorization pre-check BEFORE Agent 1.

Decides, with an explicit rule-based engine (NO LLM), whether the current
claim/procedure requires prior authorization. The engine is backed ONLY by
existing policy/benefit data:

  * the RAG policy corpus records (policy_id / payer / procedure_codes),
    the same records the V1 retrieval pipeline uses, and
  * the member plan benefit rows already attached to the canonical claim by
    the authorized RuntimeAdapter flow (payer_context.benefits, including
    authorization_requirement). No Big Patient/EHR data is accessed here.

Rules are evaluated in a fixed order; the first match wins and is fully
explainable (requires_prior_auth, matched_rule, reason, policy_reference,
source):

  PA-RULE-BENEFIT-AUTHORIZATION   a plan benefit whose category matches the
                                  requested service carries
                                  authorization_requirement = true.
  PA-RULE-POLICY-CORPUS           a coverage policy in the existing policy
                                  corpus lists one of the claim's procedure
                                  codes (exact or inclusive code range).
  PA-RULE-CLAIM-POLICY-REFERENCE  the claim explicitly references a coverage
                                  policy that exists in the policy corpus.
  PA-RULE-DEFAULT-NO-AUTH         no rule matched -> prior auth not required.
  PA-RULE-FAIL-CLOSED             the engine itself failed -> fail closed and
                                  require prior authorization.

Routing impact is intentionally NONE: both outcomes continue through the
existing frozen V1 path (no-auth -> direct Agent 1 evaluation unchanged;
auth-required -> the existing authorization/review workflow). The outcome is
represented explicitly on the workflow control plane and on the pipeline
result, never as a parallel decision pipeline.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Rule identifiers (stable, machine-readable)
# ---------------------------------------------------------------------------

RULE_BENEFIT_AUTHORIZATION = "PA-RULE-BENEFIT-AUTHORIZATION"
RULE_POLICY_CORPUS = "PA-RULE-POLICY-CORPUS"
RULE_CLAIM_POLICY_REFERENCE = "PA-RULE-CLAIM-POLICY-REFERENCE"
RULE_DEFAULT_NO_AUTH = "PA-RULE-DEFAULT-NO-AUTH"
RULE_FAIL_CLOSED = "PA-RULE-FAIL-CLOSED"

# Default backing data: the normalized RAG policy corpus of the V1 pipeline.
_DEFAULT_POLICY_CORPUS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "normalized" / "normalized_policies.json"
)

# ---------------------------------------------------------------------------
# Explicit procedure -> benefit-category rules.
# These map a requested service onto the benefit categories used by the payer
# benefit data (payer_data.db benefits.benefit_category). Deliberately small,
# explicit and deterministic; unknown services map to no category.
# ---------------------------------------------------------------------------

_PROCEDURE_PREFIX_CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("27", "Orthopedics"),      # CPT 27xxx: hip/knee joint procedures
    ("63", "Spine"),            # CPT 63xxx: spinal decompression procedures
)

_PROCEDURE_CODE_CATEGORIES: Dict[str, str] = {
    "27130": "Orthopedics",    # Total hip arthroplasty
    "27446": "Orthopedics",    # Total knee arthroplasty
    "27447": "Orthopedics",    # Total knee arthroplasty
    "27486": "Orthopedics",    # Revision knee arthroplasty
    "22612": "Spine",          # Lumbar spinal fusion
    "22630": "Spine",          # Lumbar interbody fusion
    "94660": "Sleep Medicine", # CPAP initiation and management
    "94760": "Sleep Medicine", # Non-invasive ventilation management
    "95806": "Sleep Medicine", # Sleep study (polysomnography)
    "95810": "Sleep Medicine", # Sleep study (polysomnography)
}

_DESCRIPTION_KEYWORD_CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("arthroplasty", "Orthopedics"),
    ("knee replacement", "Orthopedics"),
    ("hip replacement", "Orthopedics"),
    ("laminotomy", "Spine"),
    ("laminectomy", "Spine"),
    ("spinal fusion", "Spine"),
    ("cpap", "Sleep Medicine"),
)


@dataclass(frozen=True)
class PriorAuthPrecheckResult:
    """Explainable outcome of the deterministic prior-auth pre-check."""

    requires_prior_auth: bool
    matched_rule: str
    reason: str
    policy_reference: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requires_prior_auth": self.requires_prior_auth,
            "matched_rule": self.matched_rule,
            "reason": self.reason,
            "policy_reference": self.policy_reference,
            "source": self.source,
        }

    def to_detail_line(self) -> str:
        """Compact audit-trail detail. Never contains the ' | ' separator so
        control-plane persistence round-trips losslessly."""
        return (
            "prior_auth_precheck: "
            f"requires_prior_auth={str(self.requires_prior_auth).lower()}, "
            f"matched_rule={self.matched_rule}, "
            f"policy_reference={self.policy_reference or 'none'}, "
            f"source={self.source or 'none'}, "
            f"reason={self.reason}"
        )


# ---------------------------------------------------------------------------
# Deterministic matching helpers
# ---------------------------------------------------------------------------

_CODE_PATTERN = re.compile(r"^([A-Za-z]*)(\d+)$")


def _normalize_code(code: Any) -> str:
    return str(code or "").strip().upper()


def _code_matches(policy_code: Any, claim_code: str) -> bool:
    """Exact code match or inclusive range match (e.g. '33202-33273')."""
    candidate = _normalize_code(policy_code)
    if not candidate or not claim_code:
        return False
    if candidate == claim_code:
        return True
    if "-" not in candidate:
        return False
    low_raw, _, high_raw = candidate.partition("-")
    low_match = _CODE_PATTERN.match(_normalize_code(low_raw))
    high_match = _CODE_PATTERN.match(_normalize_code(high_raw))
    claim_match = _CODE_PATTERN.match(claim_code)
    if not (low_match and high_match and claim_match):
        return False
    if not (low_match.group(1) == high_match.group(1) == claim_match.group(1)):
        return False
    low, high, value = (
        int(low_match.group(2)),
        int(high_match.group(2)),
        int(claim_match.group(2)),
    )
    return min(low, high) <= value <= max(low, high)


def _service_benefit_categories(claim: Dict[str, Any]) -> List[str]:
    """Deterministic benefit-category candidates for the requested service."""
    case_data = claim.get("case_data") or {}
    metrics = case_data.get("clinical_metrics") or {}
    categories: List[str] = []

    def _add(category: Optional[str]) -> None:
        if category and category not in categories:
            categories.append(category)

    for code in sorted(_normalize_code(c) for c in (case_data.get("procedures") or [])):
        if not code:
            continue
        _add(_PROCEDURE_CODE_CATEGORIES.get(code))
        if code in _PROCEDURE_CODE_CATEGORIES:
            continue
        for prefix, category in _PROCEDURE_PREFIX_CATEGORIES:
            if code.startswith(prefix):
                _add(category)
                break

    description = str(metrics.get("claim_procedure") or "").lower()
    if description:
        for keyword, category in _DESCRIPTION_KEYWORD_CATEGORIES:
            if keyword in description:
                _add(category)

    return categories


def _load_default_policy_corpus() -> List[Dict[str, Any]]:
    with open(_DEFAULT_POLICY_CORPUS_PATH, "r", encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError("Policy corpus must be a list of policy records.")
    return records


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class PriorAuthRuleEngine:
    """Explicit, deterministic, explainable prior-authorization rule engine.

    ``policy_records`` are existing policy corpus records (dicts carrying at
    least policy_id / payer / procedure_codes). When omitted, the engine loads
    the normalized V1 policy corpus from data/normalized. The engine never
    reads patient/EHR data and never calls an LLM.
    """

    def __init__(
        self,
        policy_records: Optional[List[Dict[str, Any]]] = None,
        source_label: Optional[str] = None,
    ) -> None:
        if policy_records is None:
            policy_records = _load_default_policy_corpus()
            source_label = source_label or str(_DEFAULT_POLICY_CORPUS_PATH)
        self._policy_records = list(policy_records)
        self._source_label = source_label or "RAG policy corpus"

    # -- rules ---------------------------------------------------------------

    def _rule_benefit_authorization(
        self, claim: Dict[str, Any]
    ) -> Optional[PriorAuthPrecheckResult]:
        payer_context = claim.get("payer_context") or {}
        benefits = payer_context.get("benefits") or []
        if not benefits:
            return None
        categories = _service_benefit_categories(claim)
        if not categories:
            return None
        wanted = {category.strip().lower() for category in categories}
        for benefit in benefits:
            category = str(benefit.get("benefit_category") or "").strip().lower()
            if category in wanted and bool(benefit.get("authorization_requirement")):
                benefit_id = benefit.get("benefit_id") or "UNKNOWN-BENEFIT"
                plan_id = payer_context.get("plan_id") or "UNKNOWN-PLAN"
                return PriorAuthPrecheckResult(
                    requires_prior_auth=True,
                    matched_rule=RULE_BENEFIT_AUTHORIZATION,
                    reason=(
                        f"Plan benefit '{benefit.get('benefit_category')}' requires "
                        "authorization and matches the requested service; prior "
                        "authorization is required by the member's plan benefits."
                    ),
                    policy_reference=f"{benefit_id} (plan {plan_id})",
                    source="payer benefit data (payer_context.benefits)",
                )
        return None

    def _rule_policy_corpus(
        self, claim: Dict[str, Any]
    ) -> Optional[PriorAuthPrecheckResult]:
        case_data = claim.get("case_data") or {}
        procedures = sorted(
            _normalize_code(code) for code in (case_data.get("procedures") or [])
        )
        procedures = [code for code in procedures if code]
        if not procedures:
            return None
        for record in self._policy_records:
            policy_codes = record.get("procedure_codes") or []
            for code in procedures:
                matched = [pc for pc in policy_codes if _code_matches(pc, code)]
                if matched:
                    policy_id = record.get("policy_id") or "UNKNOWN-POLICY"
                    payer = record.get("payer") or "unknown payer"
                    title = record.get("policy_title") or "coverage policy"
                    return PriorAuthPrecheckResult(
                        requires_prior_auth=True,
                        matched_rule=RULE_POLICY_CORPUS,
                        reason=(
                            f"Procedure code {code} is covered by prior-auth "
                            f"policy {policy_id} ('{title}', {payer}) in the "
                            "existing policy corpus; prior authorization applies."
                        ),
                        policy_reference=policy_id,
                        source=self._source_label,
                    )
        return None

    def _rule_claim_policy_reference(
        self, claim: Dict[str, Any]
    ) -> Optional[PriorAuthPrecheckResult]:
        metrics = (claim.get("case_data") or {}).get("clinical_metrics") or {}
        claim_policy_id = str(metrics.get("claim_policy_id") or "").strip()
        if not claim_policy_id:
            return None
        for record in self._policy_records:
            if str(record.get("policy_id") or "").strip().lower() == claim_policy_id.lower():
                payer = record.get("payer") or "unknown payer"
                title = record.get("policy_title") or "coverage policy"
                return PriorAuthPrecheckResult(
                    requires_prior_auth=True,
                    matched_rule=RULE_CLAIM_POLICY_REFERENCE,
                    reason=(
                        f"Claim explicitly references prior-auth policy "
                        f"{claim_policy_id} ('{title}', {payer}) present in the "
                        "existing policy corpus; prior authorization applies."
                    ),
                    policy_reference=record.get("policy_id"),
                    source=self._source_label,
                )
        return None

    # -- evaluation ------------------------------------------------------------

    def evaluate(self, claim: Dict[str, Any]) -> PriorAuthPrecheckResult:
        """Run the ordered rule set. Deterministic; first match wins.

        Never raises: an internal failure fails CLOSED (prior authorization
        required) with the explicit PA-RULE-FAIL-CLOSED marker.
        """
        try:
            for rule in (
                self._rule_benefit_authorization,
                self._rule_policy_corpus,
                self._rule_claim_policy_reference,
            ):
                result = rule(claim)
                if result is not None:
                    return result
            return PriorAuthPrecheckResult(
                requires_prior_auth=False,
                matched_rule=RULE_DEFAULT_NO_AUTH,
                reason=(
                    "No prior-authorization policy or plan benefit requiring "
                    "authorization matched the requested procedure; prior "
                    "authorization is not required."
                ),
                policy_reference=None,
                source=self._source_label,
            )
        except Exception as exc:  # deterministic fail-closed gate
            return PriorAuthPrecheckResult(
                requires_prior_auth=True,
                matched_rule=RULE_FAIL_CLOSED,
                reason=(
                    "Prior-auth pre-check failed closed because of an internal "
                    f"error ({type(exc).__name__}); treating the request as "
                    "requiring prior authorization."
                ),
                policy_reference=None,
                source="prior_auth_precheck:fail-closed",
            )


def run_prior_auth_precheck(
    claim: Dict[str, Any],
    policy_records: Optional[List[Dict[str, Any]]] = None,
    source_label: Optional[str] = None,
) -> PriorAuthPrecheckResult:
    """Convenience entry point used by the V1 pipeline before Agent 1 runs.

    ``policy_records=None`` loads the normalized V1 policy corpus; callers may
    inject already-loaded corpus records (e.g. the pipeline's all_chunks) so
    the pre-check always uses the exact same policy data as RAG retrieval.
    """
    engine = PriorAuthRuleEngine(policy_records=policy_records, source_label=source_label)
    return engine.evaluate(claim)
