import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getReviews } from '../../services/reviewApi';
import type { ReviewItem } from '../../types/claim';
import { StatusBadge } from '../../components/common/StatusBadge';
import { EmptyState } from '../../components/common/EmptyState';
import { clsx } from 'clsx';
import { Users } from 'lucide-react';

const PRIORITY_COLORS: Record<string, string> = {
  HIGH:   'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW:    'bg-slate-100 text-slate-600 border-slate-200',
};

export function HospitalReviewQueue() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError('');
    }
    getReviews()
      .then(setReviews)
      .catch(() => {
        if (showLoading) setError('Failed to load review queue.');
      })
      .finally(() => {
        if (showLoading) setLoading(false);
      });
  };

  useEffect(() => {
    fetchData(true);
    const timer = setInterval(() => {
      fetchData(false);
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Users className="w-6 h-6 text-emerald-600" />
          Hospital Human Verification Queue
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">Claims awaiting hospital clinical verification or hold resolution</p>
      </div>

      {loading ? <LoadingState message="Loading review queue…" /> :
       error   ? <ErrorState message={error} onRetry={fetchData} /> :
       <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm animate-fade-in-up">
         <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
           <div>
             <h3 className="text-sm font-semibold text-slate-800">Verification Cases</h3>
             <p className="text-[11px] text-slate-500 mt-0.5">{reviews.length} case(s) pending verification</p>
           </div>
         </div>

         {reviews.length === 0 ? (
           <EmptyState title="Queue is clear" description="No claims pending clinical verification." />
         ) : (
           <div className="divide-y divide-slate-100">
             {reviews.map((r, index) => (
               <div
                 key={r.review_id}
                 className={clsx(
                   "px-4 py-3 cursor-pointer hover:bg-emerald-50/20 hover-card-trigger transition-all duration-150 group",
                   `stagger-${(index % 5) + 1}`
                 )}
                 onClick={() => navigate(`/hospital/claims/${r.claim_id}`)}
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
                       <span className="text-xs font-semibold text-emerald-700 group-hover:text-emerald-900">{r.claim_id}</span>
                       <StatusBadge 
                         status={
                           r.status === 'PENDING' ? 'UNDER_REVIEW' : 
                           r.status === 'IN_PROGRESS' ? 'UNDER_REVIEW' : 'ACCEPTED'
                         } 
                         className="scale-90 origin-left" 
                       />
                     </div>
                     <p className="text-xs font-semibold text-slate-700 mt-0.5">{r.procedure}</p>
                     <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">{r.reason_for_review}</p>
                     <div className="flex items-center gap-2 mt-1.5">
                       <span className="text-[11px] text-slate-400">
                         Assigned {new Date(r.assigned_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                       </span>
                     </div>
                   </div>

                   <span className="text-xs font-medium text-emerald-700 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 self-center">
                     Verify Claim →
                   </span>
                 </div>
               </div>
             ))}
           </div>
         )}
       </div>
      }
    </div>
  );
}
