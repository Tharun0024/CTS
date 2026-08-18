// Phase 6 adapter: reconciles the real V1 backend record (Phase 5A/5B) with
// the existing frontend types. This is the ONLY place naming differences are
// resolved — frozen backend semantics are never changed, the UI is never
// redesigned. Everything here is pure mapping over data the backend already
// returns (decision, status, versions, evidence, timeline, recovery).

import type {
  Agent2ResultStatus,
  Claim,
  ClaimDetails,
  ClaimStatus,
  DecisionStatus,
  EvidenceRequestStatus,
  OriginalRejection,
  PolicyEvidenceItem,
  ResubmissionStatus,
  TimelineEvent,
} from '../types/claim';
import { humanizeDecision } from '../utils/decisionHumanizer';

// ---------------------------------------------------------------------------
// Backend payload shapes (as serialized by api/claims/mapping.py)
// ---------------------------------------------------------------------------

export interface BackendEvent {
  seq: number;
  claim_id: string;
  claim_version?: number | null;
  state_before?: string;
  state_after?: string;
  action?: string;
  correlation_id?: string | null;
  evidence_request_id?: string | null;
  detail?: string | null;
  timestamp: string;
}

export interface BackendRecord {
  claim_id: string;
  patient_id?: string;
  status: string;                    // already frontend ClaimStatus vocabulary
  workflow_state?: string;
  claim_version?: number;
  decision?: {
    outcome?: string;
    status?: string;                 // already frontend decision vocabulary
    reason_code?: string | null;
    reasoning?: string[];
    agent2_recoverable?: boolean;
    requested_information?: string[];
    criteria_results?: Record<string, boolean>;
    criteria_evaluations?: Record<string, any>;
    referenced_evidence_ids?: string[];
    criterion_assessments?: Record<string, any>;
    // Phase 2: informational-only Agent1 confidence metrics.
    confidence_score?: number | null;
    confidence_level?: string | null;
    confidence_factors?: string[];
  } | null;
  agent2_invoked?: boolean;
  resubmissions?: number;
  human_review_required?: boolean;
  human_review_reasons?: string[];
  // Phase 3: human cross-verification of an Agent1 REJECT.
  human_verification_pending?: boolean;
  human_resolution?: string | null;
  original_rejection?: OriginalRejection | null;
  // Phase 1: deterministic prior-auth pre-check outcome (display-only).
  prior_auth_precheck?: {
    requires_prior_auth?: boolean;
    matched_rule?: string;
    reason?: string;
    policy_reference?: string | null;
  } | null;
  sensitive_blocked?: boolean;
  provider_declined?: boolean;
  evidence_request?: {
    evidence_request_id: string;
    correlation_id?: string | null;
    requested_information?: string[];
    criterion_ids?: string[];
    evidence_keys?: string[];
    policy_id?: string | null;
    source_reason_code?: string | null;
    created_at?: string;
    status?: string;
  } | null;
  recovery_result?: {
    evidence_request_id: string;
    item_results: { request_text: string; criterion_id: string | null; evidence_key: string; state: string; evidence_ids: string[] }[];
    recovered_evidence_ids: string[];
    notes?: string[];
  } | null;
  versions?: {
    version: string;
    attempt?: number;
    decision?: BackendRecord['decision'];
    new_evidence_delta?: string[];
    evidence_ids?: string[];
  }[];
  submissions?: {
    submission_id: string;
    claim_version?: number;
    version?: string;
    attempt?: number;
    evidence_ids?: string[];
    released?: boolean;
    correlation_id?: string | null;
    evidence_request_id?: string | null;
  }[];
  provider_decisions?: {
    decision_id: string;
    claim_id: string;
    claim_version?: number;
    decision: 'ACCEPT' | 'DECLINE';
    evidence_ids: string[];
    reason?: string | null;
    decided_at?: string;
  }[];
  canonical_claim?: {
    claim_id?: string;
    patient_id?: string;
    submission?: { attempt?: number; date?: string };
    case_data?: {
      case_id?: string;
      patient_age?: number;
      diagnoses?: string[];
      procedures?: string[];
      clinical_metrics?: Record<string, unknown>;
    };
    evidence?: {
      evidence_key?: string;
      evidence_id?: string;
      source?: string;
      status?: string;
      extracted_facts?: Record<string, unknown>;
    }[];
  };
  timeline?: BackendEvent[];
  created_at?: string;
  updated_at?: string;
  simulation_id?: string;
}

export interface BackendSummary {
  claim_id: string;
  patient_id?: string;
  status?: string;
  workflow_state?: string;
  decision_status?: string | null;
  decision_outcome?: string | null;
  claim_version?: number;
  agent2_invoked?: boolean;
  resubmissions?: number;
  updated_at?: string;
  // simulation-enriched display fields
  procedure?: string | null;
  procedure_code?: string | null;
  diagnosis_codes?: string[];
  service_date?: string | null;
  payer?: string | null;
  policy_id?: string | null;
  simulation_id?: string;
}

// ---------------------------------------------------------------------------
// State vocabulary reconciliation (backend workflow state -> frontend status)
// ---------------------------------------------------------------------------

const STATE_TO_FRONTEND_STATUS: Record<string, ClaimStatus> = {
  INIT: 'DRAFT',
  RECEIVED: 'SUBMITTED',
  EVALUATING: 'PROCESSING',
  ROUTED_RECOVERY: 'UNDER_REVIEW',
  RECOVERING: 'UNDER_REVIEW',
  AWAITING_PROVIDER_DECISION: 'MORE_INFO',
  RESUBMITTING: 'SUBMITTED_AGAIN',
  APPROVED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  HUMAN_REVIEW: 'HUMAN_REVIEW',
  RESOLVED_REENTRY: 'PROCESSING',
  FAILED: 'HUMAN_REVIEW',
};

const KNOWN_FRONTEND_STATUSES = new Set<string>([
  'DRAFT', 'SUBMITTED', 'PROCESSING', 'UNDER_REVIEW', 'PENDING_REVIEW',
  'ACCEPTED', 'REJECTED', 'MORE_INFO', 'HUMAN_REVIEW', 'RESUBMISSION_CHECK',
  'SUBMITTED_AGAIN',
]);

export function toFrontendStatus(record: { status?: string; workflow_state?: string }): ClaimStatus {
  if (record.status && KNOWN_FRONTEND_STATUSES.has(record.status)) {
    return record.status as ClaimStatus;
  }
  if (record.workflow_state && STATE_TO_FRONTEND_STATUS[record.workflow_state]) {
    return STATE_TO_FRONTEND_STATUS[record.workflow_state];
  }
  return 'SUBMITTED';
}

// Timeline icon key (ClaimTimeline CFG) derived from the event target state.
const STATE_TO_TIMELINE_KEY: Record<string, string> = {
  RECEIVED: 'SUBMITTED',
  EVALUATING: 'PROCESSING',
  RESOLVED_REENTRY: 'PROCESSING',
  ROUTED_RECOVERY: 'UNDER_REVIEW',
  RECOVERING: 'UNDER_REVIEW',
  AWAITING_PROVIDER_DECISION: 'MORE_INFO',
  RESUBMITTING: 'SUBMITTED_AGAIN',
  APPROVED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  HUMAN_REVIEW: 'HUMAN_REVIEW',
  FAILED: 'HUMAN_REVIEW',
};

function prettyState(state?: string): string {
  return (state ?? 'UNKNOWN').replace(/_/g, ' ');
}

export function mapTimeline(events: BackendEvent[] | undefined): TimelineEvent[] {
  return (events ?? []).map((event) => ({
    timestamp: event.timestamp,
    event: event.state_after ?? event.action ?? 'EVENT',
    message: event.detail || `${prettyState(event.state_before)} → ${prettyState(event.state_after)}`,
    status: (event.state_after && STATE_TO_TIMELINE_KEY[event.state_after]) as ClaimStatus | undefined,
  }));
}

// ---------------------------------------------------------------------------
// Derived lifecycle views (pure mapping from backend truth)
// ---------------------------------------------------------------------------

function deriveEvidenceRequestStatus(record: BackendRecord): EvidenceRequestStatus {
  const erq = record.evidence_request;
  if (!erq) return 'CLOSED';
  if (erq.status && ['PENDING_PROVIDER_RESPONSE', 'WAITING_FOR_PROVIDER', 'RECEIVED', 'UNDER_AGENT2_REVIEW', 'CLOSED'].includes(erq.status)) {
    return erq.status as EvidenceRequestStatus;
  }
  switch (record.workflow_state) {
    case 'ROUTED_RECOVERY':
    case 'RECOVERING':
      return 'PENDING_PROVIDER_RESPONSE';
    case 'AWAITING_PROVIDER_DECISION':
      return 'WAITING_FOR_PROVIDER';
    case 'RESUBMITTING':
      return 'RECEIVED';
    default:
      return 'CLOSED';
  }
}

function deriveResubmissionStatus(record: BackendRecord): ResubmissionStatus {
  if ((record.resubmissions ?? 0) > 0 || record.workflow_state === 'RESUBMITTING') {
    return 'RESUBMITTED';
  }
  if (record.evidence_request && record.workflow_state !== 'APPROVED') {
    return 'AWAITING_EVIDENCE';
  }
  return 'NOT_REQUIRED';
}

function deriveAgent2Result(record: BackendRecord): Agent2ResultStatus | null {
  if (!record.agent2_invoked) return null;
  return record.provider_declined || record.human_review_required
    ? 'ESCALATED_TO_HUMAN'
    : 'RELEASED';
}

function mapPolicyEvidence(record: BackendRecord): PolicyEvidenceItem[] {
  // One row per real submitted evidence item, with its real provenance.
  // MET/NOT_MET is derived only from the Agent1 decision: items Agent1 still
  // requests are NOT_MET; everything submitted on an approved claim is MET.
  const evidence = record.canonical_claim?.evidence ?? [];
  const requested = new Set(record.decision?.requested_information ?? []);
  const approved = record.workflow_state === 'APPROVED';
  return evidence
    .filter((item) => item && item.evidence_key)
    .map((item) => {
      const facts = item.extracted_facts ?? {};
      const provenance = (facts['provenance'] as string) || item.source || 'Provider Record';
      const notMet = !approved && [...requested].some((req) =>
        req.toLowerCase().includes(String(item.evidence_key).toLowerCase())
      );
      return {
        criterion: String(item.evidence_key),
        patient_value: (facts['content_reference'] as string) || item.source || 'Documented in patient record',
        status: notMet ? 'NOT_MET' : 'MET',
        source: provenance,
      } as PolicyEvidenceItem;
    });
}

// ---------------------------------------------------------------------------
// Full record -> ClaimDetails (the shape the existing UI consumes)
// ---------------------------------------------------------------------------

export function toClaimDetails(record: BackendRecord): ClaimDetails {
  const canonical = record.canonical_claim ?? {};
  const caseData = canonical.case_data ?? {};
  const metrics = (caseData.clinical_metrics ?? {}) as Record<string, unknown>;
  const procedures = caseData.procedures ?? [];
  const decision = record.decision ?? null;

  const versions = record.versions ?? [];
  const submissions = record.submissions ?? [];
  const attempt = submissions.length > 0
    ? submissions[submissions.length - 1].attempt ?? versions.length
    : Math.max(versions.length, 1);

  const submissionHistory = submissions.map((submission) => {
    const versionNumber = submission.claim_version;
    const firstEvent = (record.timeline ?? []).find(
      (event) => typeof versionNumber === 'number' && event.claim_version === versionNumber
    );
    return {
      attempt: submission.attempt ?? versionNumber ?? 1,
      submitted_at: firstEvent?.timestamp ?? record.created_at ?? record.updated_at ?? '',
      status: (firstEvent ? toFrontendStatus({ workflow_state: firstEvent.state_after ?? undefined }) : 'SUBMITTED') as ClaimStatus,
      note: `Submission ${submission.submission_id} (${submission.version ?? 'V?'})` +
        (submission.released ? ' — evidence released to payer' : ''),
    };
  });

  const recoveredIds = record.recovery_result?.recovered_evidence_ids ?? [];
  const providerAccepted = (record.provider_decisions ?? []).some((d) => d.decision === 'ACCEPT');
  const evidenceResponse = record.recovery_result
    ? {
        evidence: recoveredIds.length > 0
          ? `${recoveredIds.length} evidence item(s) recovered by Agent 2`
          : 'Agent 2 recovery found no releasable evidence',
        decision: (record.provider_declined ? 'ESCALATED' : 'RELEASED') as 'RELEASED' | 'ESCALATED',
        status: (providerAccepted || (record.submissions ?? []).some((s) => s.released)
          ? 'SENT_TO_PAYER'
          : 'RECEIVED') as 'SENT_TO_PAYER' | 'RECEIVED' | 'ESCALATED',
        responded_at: record.updated_at,
      }
    : null;

  const resubmissionStatus = deriveResubmissionStatus(record);
  const evidenceRequestStatus = deriveEvidenceRequestStatus(record);

  return {
    claim_id: record.claim_id,
    patient: {
      patient_id: record.patient_id ?? canonical.patient_id ?? 'UNKNOWN',
      age: typeof caseData.patient_age === 'number' ? caseData.patient_age : 0,
      gender: (metrics['patient_gender'] as string) ?? 'Unknown',
      name: (metrics['patient_name'] as string) ?? undefined,
      dob: (metrics['patient_dob'] as string) ?? undefined,
      address: (metrics['patient_address'] as string) ?? undefined,
      contact: (metrics['patient_phone'] as string) ?? (metrics['patient_contact'] as string) ?? undefined,
      relationship: (metrics['patient_relationship'] as string) ?? undefined,
      policy_holder: (metrics['policy_holder'] as string) ?? undefined,
    },
    claim: {
      procedure: (metrics['claim_procedure'] as string) ?? procedures[0] ?? 'Unspecified procedure',
      procedure_code: procedures[0] ?? 'N/A',
      diagnosis_codes: caseData.diagnoses ?? [],
      service_date: canonical.submission?.date ?? record.created_at ?? '',
    },
    policy: {
      payer: (metrics['claim_payer'] as string) ?? 'Unknown payer',
      policy_id: (metrics['claim_policy_id'] as string) ?? record.evidence_request?.policy_id ?? 'N/A',
      policy_name: (metrics['claim_policy_id'] as string) ?? record.evidence_request?.policy_id ?? 'Policy on file',
    },
    decision: decision
      ? {
          status: (decision.status ?? decision.outcome ?? 'HUMAN_REVIEW') as DecisionStatus,
          reason: humanizeDecision(decision),
          reason_code: decision.reason_code ?? undefined,
          criteria_results: decision.criteria_results,
          criteria_evaluations: decision.criteria_evaluations,
          referenced_evidence_ids: decision.referenced_evidence_ids,
          criterion_assessments: decision.criterion_assessments,
          confidence_score: decision.confidence_score ?? null,
          confidence_level: decision.confidence_level ?? null,
          confidence_factors: decision.confidence_factors ?? [],
        }
      : null,
    policy_evidence: mapPolicyEvidence(record),
    missing_information: decision?.requested_information ?? [],
    resubmission: {
      eligible: record.workflow_state === 'REJECTED' && (record.resubmissions ?? 0) === 0,
      status: resubmissionStatus,
    },
    status: toFrontendStatus(record),
    submitted_at: record.created_at ?? '',
    updated_at: record.updated_at ?? record.created_at ?? '',
    hospital: 'City General Hospital',
    documents: [],
    timeline: mapTimeline(record.timeline),
    attempt,
    submission_history: submissionHistory,
    evidence_request: record.evidence_request
      ? {
          request_id: record.evidence_request.evidence_request_id,
          requested_evidence:
            (record.evidence_request.requested_information ?? []).join('; ') ||
            (record.evidence_request.evidence_keys ?? []).join(', ') ||
            'Additional clinical documentation',
          reason: record.evidence_request.source_reason_code
            ? String(record.evidence_request.source_reason_code).replace(/_/g, ' ')
            : 'Agent 1 requested additional information for policy criteria evaluation.',
          status: evidenceRequestStatus,
        }
      : null,
    evidence_response: evidenceResponse,
    evidence_request_status: evidenceRequestStatus,
    resubmission_status: resubmissionStatus,
    agent2_result: deriveAgent2Result(record),
    reevaluation_status: record.workflow_state ?? null,
    // live backend fields
    workflow_state: record.workflow_state,
    claim_version: record.claim_version,
    agent2_invoked: record.agent2_invoked,
    resubmissions: record.resubmissions,
    human_review_reasons: record.human_review_reasons,
    recovery_result: record.recovery_result ?? null,
    versions: versions.map((version) => ({
      version: version.version,
      attempt: version.attempt,
      decision: version.decision
        ? {
            status: (version.decision.status ?? 'HUMAN_REVIEW') as DecisionStatus,
            reason: humanizeDecision(version.decision),
            reason_code: version.decision.reason_code ?? undefined,
            outcome: version.decision.outcome,
          }
        : null,
      new_evidence_delta: version.new_evidence_delta,
      evidence_ids: version.evidence_ids,
    })),
    provider_decisions: record.provider_decisions ?? [],
    simulation_id: record.simulation_id,
    // Phase 3: human cross-verification of an Agent1 REJECT.
    human_verification_pending: record.human_verification_pending ?? false,
    human_resolution: record.human_resolution ?? null,
    original_rejection: record.original_rejection ?? null,
    prior_auth_precheck: record.prior_auth_precheck ?? null,
  };
}

// ---------------------------------------------------------------------------
// Summaries -> Claim (list views)
// ---------------------------------------------------------------------------

export function toClaimSummary(summary: BackendSummary): Claim {
  const status = toFrontendStatus({ status: summary.status, workflow_state: summary.workflow_state });
  return {
    claim_id: summary.claim_id,
    patient_id: summary.patient_id ?? 'UNKNOWN',
    hospital: 'City General Hospital',
    procedure: summary.procedure ?? summary.procedure_code ?? 'Unspecified procedure',
    procedure_code: summary.procedure_code ?? 'N/A',
    diagnosis_codes: summary.diagnosis_codes ?? [],
    service_date: summary.service_date ?? summary.updated_at ?? '',
    payer: summary.payer ?? undefined,
    policy_id: summary.policy_id ?? undefined,
    status,
    attempt: Math.max(summary.claim_version ?? 1, 1),
    evidence_request_status: undefined,
    resubmission_status: (summary.resubmissions ?? 0) > 0 ? 'RESUBMITTED' : 'NOT_REQUIRED',
    agent2_result: summary.agent2_invoked ? 'RELEASED' : null,
    submitted_at: summary.updated_at ?? '',
    updated_at: summary.updated_at ?? '',
    simulation_id: summary.simulation_id,
  } as Claim & { simulation_id?: string };
}
