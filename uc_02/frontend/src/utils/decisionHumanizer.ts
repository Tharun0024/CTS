// Frontend-only humanizer for Agent 1 decision rationale. The backend ships
// raw internal trace lines ("Step 1: Evaluating exclusions.", "Key: ... |
// State: MISSING | ...", LLM debug sections). The UI must show a concise
// human-readable explanation WITHOUT altering the backend reasoning — so this
// converts at the adapter boundary, preferring the structured fields the
// backend already returns (status, reason_code, requested_information) and
// falling back to the raw trace only when nothing structured exists.

export interface DecisionLike {
  outcome?: string;
  status?: string;
  reason_code?: string | null;
  reasoning?: string[];
  requested_information?: string[];
  criteria_results?: Record<string, boolean>;
  criteria_evaluations?: Record<string, any>;
  referenced_evidence_ids?: string[];
  criterion_assessments?: Record<string, any>;
}

function prettyReasonCode(code?: string | null): string {
  return code ? code.replace(/_/g, ' ').toLowerCase() : '';
}

// Exact V1 outcome labels for primary decision badges/text. The internal
// vocabulary (ACCEPT / REJECT / MORE_INFORMATION / HUMAN_REVIEW and their
// claim-status twins) is mapped here for display only — backend values are
// never altered.
export function decisionLabel(status?: string | null): string {
  switch (status) {
    case 'ACCEPT':
    case 'ACCEPTED':
    case 'APPROVED':
      return 'APPROVE';
    case 'REJECT':
    case 'REJECTED':
      return 'REJECT';
    case 'MORE_INFORMATION':
    case 'MORE_INFO':
      return 'REQUEST MORE INFORMATION';
    case 'HUMAN_REVIEW':
      return 'HUMAN REVIEW';
    default:
      return (status ?? '').replace(/_/g, ' ').trim();
  }
}

export function humanizeDecision(decision: DecisionLike | null | undefined): string {
  if (!decision) return 'No decision recorded.';
  const status = decision.status ?? decision.outcome ?? '';
  const reason = prettyReasonCode(decision.reason_code);
  const missing = decision.requested_information ?? [];
  const missingList = missing.join('; ');

  switch (status) {
    case 'ACCEPT':
      return 'All evaluated policy criteria were satisfied based on the submitted evidence, so the claim is approved.';
    case 'REJECT':
      return `The claim was denied${reason ? ` (${reason})` : ''}.` +
        (missingList ? ` Outstanding items: ${missingList}.` : '');
    case 'MORE_INFORMATION':
      return `Additional information is required before a decision can be made` +
        (missingList ? `: ${missingList}.` : '.');
    case 'HUMAN_REVIEW': {
      const lines: string[] = [];
      lines.push(`DECISION: Escalated to Human Review`);
      lines.push(`REASON CODE: ${decision.reason_code || 'UNCERTAIN_CONCLUSIVENESS'}`);
      
      // Criteria status
      const criteriaStates: string[] = [];
      const evals = decision.criteria_evaluations || {};
      const results = decision.criteria_results || {};
      for (const [critId, evalObj] of Object.entries(evals)) {
        const critName = evalObj.criterion_name || evalObj.name || critId;
        const passed = results[critId] === true;
        criteriaStates.push(`- ${critId}: ${critName} (${passed ? 'PASSED' : 'NOT MET / UNCERTAIN'})`);
      }
      if (criteriaStates.length > 0) {
        lines.push(`CRITERIA STATUS:\n${criteriaStates.join('\n')}`);
      } else {
        lines.push(`CRITERIA STATUS: Incomplete or uncertain criteria validation.`);
      }
      
      // Supporting evidence IDs
      const evidenceIds = decision.referenced_evidence_ids || [];
      lines.push(`SUPPORTING EVIDENCE: ${evidenceIds.length > 0 ? evidenceIds.join(', ') : 'None referenced'}`);
      
      // Missing / uncertain information
      lines.push(`MISSING/UNCERTAIN INFORMATION: ${missing.length > 0 ? missing.join('; ') : 'None outstanding'}`);
      
      // Why automation stopped
      let stoppedWhy = 'Automation stopped because the clinical criteria could not be definitively validated with the available evidence.';
      if (decision.reason_code === 'SENSITIVE_DATA_BLOCKED') {
        stoppedWhy = 'Automation stopped because sensitive clinical data release consent was declined or blocked.';
      } else if (decision.reason_code === 'PIPELINE_FAIL_CLOSED') {
        stoppedWhy = 'Automation stopped because the RAG decision pipeline failed closed on error.';
      } else if (decision.reason_code === 'NO_MATCHING_POLICY') {
        stoppedWhy = 'Automation stopped because no compatible active policy was found for the requested procedure.';
      } else if (missing.length > 0) {
        stoppedWhy = 'Automation stopped because key required evidence items are missing and need provider resubmission.';
      }
      lines.push(`WHY AUTOMATION STOPPED: ${stoppedWhy}`);
      
      // What the human should review/do
      let humanAction = 'The human reviewer should review the clinical documents, verify the diagnostic criteria, and manually determine prior authorization status.';
      if (decision.reason_code === 'SENSITIVE_DATA_BLOCKED') {
        humanAction = 'The reviewer should contact the provider to obtain manual authorization or release consent for the requested clinical documents.';
      } else if (missing.length > 0) {
        humanAction = 'The reviewer should verify if the provider has resubmitted the missing documentation and re-trigger evaluation.';
      }
      lines.push(`RECOMMENDED REVIEWER ACTION: ${humanAction}`);
      
      return lines.join('\n\n');
    }
    default:
      break;
  }

  // Fallback: pass through whatever the backend recorded, trimmed.
  const cleaned = (decision.reasoning ?? []).map(line => line.trim()).filter(Boolean);
  return cleaned.length > 0 ? cleaned.join(' ') : 'No reasoning recorded.';
}
