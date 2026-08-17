// Notifications service — V1 has no backend notifications endpoint, so alerts
// are derived client-side from the SAME real claim records every other view
// uses (same pattern as reviewApi). Only genuinely alarming events produce a
// notification: REJECT, HUMAN_REVIEW, REQUEST_MORE_INFORMATION, provider
// DECLINE of Agent 2 recovered evidence, and failed Agent 2 recovery.
// Normal APPROVE never alerts. No mock data is used anywhere here.

import { getClaims, getClaimDetails } from './claimsApi';
import type { ClaimDetails, Notification, NotificationType } from '../types/claim';

const READ_KEY = 'orca_read_notifications';

function readIds(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(READ_KEY) ?? '[]') as string[]);
  } catch {
    return new Set();
  }
}

function writeIds(ids: Set<string>): void {
  localStorage.setItem(READ_KEY, JSON.stringify([...ids]));
}

// Derive alarming notifications from one real claim record.
function deriveFromClaim(claim: ClaimDetails): Notification[] {
  const out: Notification[] = [];
  const at = claim.updated_at || claim.submitted_at || new Date().toISOString();
  const push = (event: string, type: NotificationType, message: string) => {
    out.push({
      notification_id: `NOTIF-${claim.claim_id}-${event}`,
      claim_id: claim.claim_id,
      message,
      type,
      read: false,
      created_at: at,
    });
  };

  const decision = claim.decision;
  const reasonCode = decision?.reason_code ? ` (${decision.reason_code.replace(/_/g, ' ').toLowerCase()})` : '';

  // Terminal denial.
  if (claim.status === 'REJECTED' || decision?.status === 'REJECT') {
    push('REJECT', 'DECISION', `Claim ${claim.claim_id} was denied${reasonCode}. ${decision?.reason ?? ''}`.trim());
  }

  // Human resolution required.
  if (claim.status === 'HUMAN_REVIEW' || decision?.status === 'HUMAN_REVIEW') {
    const reasons = claim.human_review_reasons?.length
      ? ` Reasons: ${claim.human_review_reasons.join('; ')}.`
      : '';
    push('HUMAN_REVIEW', 'HUMAN_REVIEW', `Claim ${claim.claim_id} requires human review.${reasons}`);
  }

  // REQUEST_MORE_INFORMATION routed to Agent 2 recovery.
  if (claim.status === 'MORE_INFO' || decision?.status === 'MORE_INFORMATION') {
    const missing = claim.missing_information.length
      ? ` Requested: ${claim.missing_information.join('; ')}.`
      : '';
    push('MORE_INFO', 'MORE_INFO', `Additional information was requested for claim ${claim.claim_id}.${missing}`);
  }

  // Provider declined release of Agent 2 recovered evidence.
  const declined = (claim.provider_decisions ?? []).some(d => d.decision === 'DECLINE');
  if (declined) {
    push('PROVIDER_DECLINE', 'PROVIDER_DECLINE',
      `Provider declined release of Agent 2 recovered evidence for claim ${claim.claim_id}; the claim was escalated to human review.`);
  }

  // Agent 2 recovery found no releasable evidence.
  if (claim.recovery_result && claim.recovery_result.recovered_evidence_ids.length === 0) {
    push('RECOVERY_FAILED', 'RECOVERY_FAILED',
      `Agent 2 recovery found no releasable evidence for claim ${claim.claim_id}.`);
  }

  return out;
}

// Derived from the live backend claim dataset (main + simulation claims).
export async function getNotifications(): Promise<Notification[]> {
  const claims = await getClaims();
  const alarming = claims.filter(c =>
    c.status === 'REJECTED' || c.status === 'HUMAN_REVIEW' || c.status === 'MORE_INFO'
  );

  const details = await Promise.all(
    alarming.map(c => getClaimDetails(c.claim_id).catch(() => null))
  );

  const notifications: Notification[] = [];
  for (const record of details) {
    if (record) notifications.push(...deriveFromClaim(record));
  }

  const read = readIds();
  for (const n of notifications) n.read = read.has(n.notification_id);

  return notifications.sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

// Read-state is the only local concern (no backend endpoint exists for it).
export async function markAsRead(notificationId: string): Promise<void> {
  const ids = readIds();
  ids.add(notificationId);
  writeIds(ids);
}

export async function markAllRead(): Promise<void> {
  const notifications = await getNotifications();
  const ids = readIds();
  for (const n of notifications) ids.add(n.notification_id);
  writeIds(ids);
}
