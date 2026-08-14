import type { ReviewItem, ReviewDetails } from '../types/claim';
import { mockClaimDetails } from './claims';

export const mockReviews: ReviewItem[] = [
  {
    review_id: 'REV-001',
    claim_id: 'CLM-004',
    hospital: 'Northside Heart Institute',
    patient_id: 'PAT-004',
    procedure: 'Cardiac Catheterization',
    reason_for_review: 'Conflicting clinical evidence — patient comorbidities (Diabetes + CKD) require specialist judgment',
    assigned_at: '2026-08-10T16:30:00Z',
    status: 'IN_PROGRESS',
    priority: 'HIGH',
  },
  {
    review_id: 'REV-002',
    claim_id: 'CLM-006',
    hospital: 'Lakeside Surgical Center',
    patient_id: 'PAT-006',
    procedure: 'Bariatric Surgery (Gastric Bypass)',
    reason_for_review: 'Missing psychiatric clearance; borderline BMI qualification requires clinical review',
    assigned_at: '2026-08-12T09:30:00Z',
    status: 'PENDING',
    priority: 'MEDIUM',
  },
  {
    review_id: 'REV-003',
    claim_id: 'CLM-009',
    hospital: 'Sports Medicine Clinic',
    patient_id: 'PAT-009',
    procedure: 'Knee Arthroscopy',
    reason_for_review: 'Young patient, minimal conservative treatment history',
    assigned_at: '2026-08-12T11:00:00Z',
    status: 'PENDING',
    priority: 'LOW',
  },
];

export const mockReviewDetails: ReviewDetails[] = mockReviews.map((rev) => ({
  ...rev,
  claim_details: mockClaimDetails.find(c => c.claim_id === rev.claim_id) || mockClaimDetails[3],
  ai_recommendation: rev.priority === 'HIGH' ? 'HUMAN_REVIEW' : 'ACCEPT',
  ai_confidence: rev.priority === 'HIGH' ? 0.55 : 0.78,
}));
