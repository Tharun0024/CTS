import { useState, useEffect } from 'react';
import { ReviewQueueTable } from '../../components/insurance/ReviewQueueTable';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getReviews } from '../../services/reviewApi';
import type { ReviewItem } from '../../types/claim';

export function ReviewQueue() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = () => {
    setLoading(true); setError('');
    getReviews()
      .then(setReviews)
      .catch(() => setError('Failed to load review queue.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
<div className="mb-6">
            <h1 className="text-xl font-bold text-slate-900">Review Queue</h1>
            <p className="text-xs text-slate-500 mt-0.5">Claims requiring human clinical judgment</p>
          </div>

          {loading ? <LoadingState message="Loading review queue…" /> :
           error   ? <ErrorState message={error} onRetry={fetchData} /> :
           <ReviewQueueTable reviews={reviews} />
          }
</div>
  );
}
