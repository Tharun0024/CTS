import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { clsx } from 'clsx';
import type { ReviewItem } from '../../types/claim';

const PRIORITY_COLORS: Record<string, string> = {
  HIGH:   'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW:    'bg-slate-100 text-slate-600 border-slate-200',
};

interface ReviewQueueTableProps {
  reviews: ReviewItem[];
}

export function ReviewQueueTable({ reviews }: ReviewQueueTableProps) {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm animate-fade-in-up">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Human Review Queue</h3>
          <p className="text-[11px] text-slate-500 mt-0.5">{reviews.length} case(s) awaiting review</p>
        </div>
        <span className="text-[11px] font-bold bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full">
          {reviews.filter(r => r.priority === 'HIGH').length} HIGH
        </span>
      </div>

      {reviews.length === 0 ? (
        <EmptyState title="Queue is clear" description="No cases pending human review." />
      ) : (
        <div className="divide-y divide-slate-100">
          {reviews.map((r, index) => (
            <div
              key={r.review_id}
              className={clsx(
                "px-4 py-3 cursor-pointer hover:bg-brand-50/20 hover-card-trigger transition-all duration-150 group",
                `stagger-${(index % 5) + 1}`
              )}
              onClick={() => navigate(`/insurance/review/${r.review_id}`)}
            >
              <div className="flex items-start gap-3">
                <span className={clsx(
                  'text-[9px] font-extrabold px-1.5 py-0.5 rounded border flex-shrink-0 mt-0.5',
                  PRIORITY_COLORS[r.priority]
                )}>
                  {r.priority}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-brand-600 group-hover:text-brand-700">{r.claim_id}</span>
                    <StatusBadge status={r.status as 'SUBMITTED' | 'PROCESSING' | 'ACCEPTED'} className="scale-90 origin-left" />
                  </div>
                  <p className="text-xs font-semibold text-slate-700 mt-0.5">{r.procedure}</p>
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">{r.reason_for_review}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[11px] text-slate-400 font-medium">{r.hospital}</span>
                    <span className="text-slate-300 text-xs">•</span>
                    <span className="text-[11px] text-slate-400">
                      Assigned {new Date(r.assigned_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>

                <span className="text-xs font-medium text-brand-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 self-center">
                  Review →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
