import type { Notification } from '../types/claim';

let notifIdCounter = 1;
const makeId = () => `NOTIF-${String(notifIdCounter++).padStart(3, '0')}`;

export const mockNotifications: Notification[] = [
  {
    notification_id: makeId(),
    claim_id: 'CLM-001',
    message: 'CLM-001 (Total Knee Replacement) has been ACCEPTED. All policy criteria satisfied.',
    type: 'DECISION',
    read: false,
    created_at: '2026-08-11T11:00:00Z',
  },
  {
    notification_id: makeId(),
    claim_id: 'CLM-002',
    message: 'CLM-002 (Lumbar Spinal Fusion) has been REJECTED. Missing MRI and orthopedic evaluation.',
    type: 'DECISION',
    read: false,
    created_at: '2026-08-11T09:30:00Z',
  },
  {
    notification_id: makeId(),
    claim_id: 'CLM-003',
    message: 'CLM-003 (CT Scan) requires additional information. Please upload lab results and prior imaging.',
    type: 'MORE_INFO',
    read: false,
    created_at: '2026-08-11T10:15:00Z',
  },
  {
    notification_id: makeId(),
    claim_id: 'CLM-004',
    message: 'CLM-004 (Cardiac Catheterization) has been escalated to HUMAN REVIEW due to clinical complexity.',
    type: 'STATUS_CHANGE',
    read: true,
    created_at: '2026-08-10T16:00:00Z',
  },
  {
    notification_id: makeId(),
    claim_id: 'CLM-007',
    message: 'CLM-007 resubmission analysis complete — 94% probability of approval. Ready to resubmit.',
    type: 'RESUBMISSION',
    read: true,
    created_at: '2026-08-12T11:00:00Z',
  },
  {
    notification_id: makeId(),
    claim_id: 'CLM-005',
    message: 'CLM-005 (Shoulder Arthroscopy) is now being processed.',
    type: 'STATUS_CHANGE',
    read: true,
    created_at: '2026-08-12T10:02:00Z',
  },
];
