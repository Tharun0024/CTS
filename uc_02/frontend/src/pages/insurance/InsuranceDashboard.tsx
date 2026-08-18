import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getInsuranceClaims } from '../../services/insuranceApi';
import { getReviews } from '../../services/reviewApi';
import type { InsuranceClaim, ReviewItem } from '../../types/claim';
import { ClipboardList, Users, CheckCircle2, Clock, ArrowRight, AlertTriangle, XCircle } from 'lucide-react';

export function InsuranceDashboard() {
  const navigate = useNavigate();
  const [claims, setClaims]   = useState<InsuranceClaim[]>([]);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError('');
    }
    Promise.all([getInsuranceClaims(), getReviews()])
      .then(([c, r]) => { setClaims(c); setReviews(r); })
      .catch(() => {
        if (showLoading) setError('Failed to load dashboard data.');
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

  const total = claims.length;
  const count = (status: string) => claims.filter(c => c.status === status).length;
  const accepted = count('ACCEPTED');
  const processing = claims.filter(c => ['PROCESSING', 'UNDER_REVIEW', 'SUBMITTED', 'SUBMITTED_AGAIN', 'RESUBMISSION_CHECK', 'DRAFT'].includes(c.status)).length;
  const needsInfo = count('MORE_INFO');
  const rejected = count('REJECTED');
  const humanReview = count('HUMAN_REVIEW');

  const pct = (num: number) => total > 0 ? Math.round((num / total) * 100) : 0;

  const stats = [
    { label: 'Total Claims',  value: total, sub: 'All time', icon: ClipboardList, color: 'text-slate-700', bg: 'bg-slate-50', path: '/insurance/claims' },
    { label: 'Approved',      value: accepted, sub: `${pct(accepted)}% approval rate`, icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50', path: '/insurance/claims' },
    { label: 'Processing',    value: processing, sub: `${pct(processing)}% in pipeline`, icon: Clock, color: 'text-blue-600', bg: 'bg-blue-50', path: '/insurance/claims' },
    { label: 'Needs Info',    value: needsInfo, sub: needsInfo > 0 ? 'Action required' : 'All clear', icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', path: '/insurance/claims' },
    { label: 'Denied',        value: rejected, sub: `${pct(rejected)}% rejection rate`, icon: XCircle, color: 'text-red-650', bg: 'bg-red-50', path: '/insurance/claims' },
    { label: 'Human Review',  value: humanReview, sub: `${pct(humanReview)}% require review`, icon: Users, color: 'text-indigo-600', bg: 'bg-indigo-50', path: '/insurance/review' },
  ];

  const recent = [...claims].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 5);
  const highPriority = reviews.filter(r => r.priority === 'HIGH' && r.status !== 'COMPLETED');

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
            <div>
              <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
              <p className="text-xs text-slate-500 mt-0.5">Claims authorization overview</p>
            </div>
            <button
              onClick={() => navigate('/insurance/claims')}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 border-2 border-brand-700 text-white text-xs font-bold rounded-lg transition-all"
            >
              <ClipboardList className="w-3.5 h-3.5" /> View All Claims
            </button>
          </div>

          {loading ? <LoadingState message="Loading dashboard…" /> :
           error   ? <ErrorState message={error} onRetry={fetchData} /> :
           (
            <div className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {stats.map((s, i) => {
                  const Icon = s.icon;
                  return (
                    <button
                      key={i}
                      onClick={() => navigate(s.path)}
                      className="bg-white border border-slate-200 rounded-xl p-4 text-left hover:border-brand-300 hover:shadow-sm transition-all group"
                    >
                      <div className={`w-8 h-8 ${s.bg} rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform`}>
                        <Icon className={`w-4 h-4 ${s.color}`} />
                      </div>
                      <p className="text-2xl font-bold text-slate-900">{s.value}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
                    </button>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Recent claims */}
                <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
                  <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-slate-800">Recent Incoming Claims</h2>
                    <button onClick={() => navigate('/insurance/claims')} className="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1">
                      View all <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm min-w-[400px]">
                      <thead className="bg-slate-50 text-xs text-slate-500 font-semibold border-b border-slate-200">
                        <tr>
                          <th className="px-5 py-3">Claim</th>
                          <th className="px-5 py-3">Hospital</th>
                          <th className="px-5 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {recent.map(c => (
                          <tr key={c.claim_id} className="hover:bg-brand-50/30 cursor-pointer group transition-colors"
                            onClick={() => navigate(`/insurance/claims/${c.claim_id}`)}>
                            <td className="px-5 py-3 font-semibold text-brand-600 group-hover:text-brand-700">{c.claim_id}</td>
                            <td className="px-5 py-3 text-xs text-slate-500 truncate max-w-[120px]">{c.hospital}</td>
                            <td className="px-5 py-3"><StatusBadge status={c.status} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* High priority reviews */}
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                  <div className="px-5 py-4 border-b border-red-200 bg-red-50/50 flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-semibold text-slate-800">High Priority Reviews</h2>
                      <p className="text-xs text-red-600 mt-0.5">{highPriority.length} urgent</p>
                    </div>
                    <button onClick={() => navigate('/insurance/review')} className="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1">
                      Queue <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {highPriority.length === 0 ? (
                      <p className="text-xs text-slate-400 text-center py-6">No high priority reviews.</p>
                    ) : highPriority.map(r => (
                      <div key={r.review_id} className="px-5 py-3 cursor-pointer hover:bg-red-50/30 transition-colors"
                        onClick={() => navigate(`/insurance/review/${r.review_id}`)}>
                        <p className="text-xs font-semibold text-red-700">{r.claim_id}</p>
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{r.procedure}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
</div>
  );
}
