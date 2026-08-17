import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

import { IncomingClaimsTable } from '../../components/insurance/IncomingClaimsTable';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getInsuranceClaims } from '../../services/insuranceApi';
import type { InsuranceClaim } from '../../types/claim';

export function IncomingClaims() {
  const [searchParams] = useSearchParams();
  // Header search navigates here with ?q=<term> to pre-filter the real list.
  const initialQuery = searchParams.get('q') ?? '';
  const [claims, setClaims]   = useState<InsuranceClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError('');
    }
    getInsuranceClaims()
      .then(setClaims)
      .catch(() => {
        if (showLoading) setError('Failed to load claims.');
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
            <h1 className="text-xl font-bold text-slate-900">Incoming Claims</h1>
            <p className="text-xs text-slate-500 mt-0.5">{claims.length} claims from hospitals</p>
          </div>

          {loading ? <LoadingState message="Loading claims…" /> :
           error   ? <ErrorState message={error} onRetry={fetchData} /> :
           <IncomingClaimsTable claims={claims} initialQuery={initialQuery} />
          }
</div>
  );
}
