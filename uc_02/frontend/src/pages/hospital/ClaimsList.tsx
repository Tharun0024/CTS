import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { ClaimsTable } from '../../components/hospital/ClaimsTable';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getClaims } from '../../services/claimsApi';
import type { Claim } from '../../types/claim';
import { FilePlus2, List } from 'lucide-react';
import { Button } from '../../components/ui/Button';

export function ClaimsList() {
  const navigate = useNavigate();
  const [claims, setClaims]   = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = () => {
    setLoading(true); setError('');
    getClaims().then(setClaims).catch(() => setError('Failed to load claims.')).finally(() => setLoading(false));
  };
  useEffect(() => { fetchData(); }, []);

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <List className="w-6 h-6 text-emerald-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">All Claims</h1>
          </div>
          <p className="text-sm text-slate-500 font-medium">{claims.length} authorization requests total</p>
        </div>
        <Button
          onClick={() => navigate('/hospital/claims/new')}
          className="shadow-md shadow-emerald-200 hover:shadow-lg"
        >
          <FilePlus2 className="w-4 h-4 mr-2" /> New Claim
        </Button>
      </div>
      {loading ? <LoadingState message="Loading claims…" /> :
       error   ? <ErrorState message={error} onRetry={fetchData} /> :
       <ClaimsTable claims={claims} portal="hospital" />}
    </div>
  );
}

