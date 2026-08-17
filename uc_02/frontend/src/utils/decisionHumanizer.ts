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
    case 'HUMAN_REVIEW':
      return `Automated evaluation could not reach a safe conclusion${reason ? ` (${reason})` : ''}. ` +
        'The claim was routed to human review.';
    default:
      break;
  }

  // Fallback: pass through whatever the backend recorded, trimmed.
  const cleaned = (decision.reasoning ?? []).map(line => line.trim()).filter(Boolean);
  return cleaned.length > 0 ? cleaned.join(' ') : 'No reasoning recorded.';
}
