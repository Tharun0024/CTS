import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { clsx } from 'clsx';
import type { InsuranceClaim, ClaimStatus } from '../../types/claim';
import { Search } from 'lucide-react';

const FILTERS: { label: string; value: ClaimStatus | 'ALL' }[] = [
  { label: 'All',          value: 'ALL' },
  { label: 'Processing',   value: 'PROCESSING' },
  { label: 'Under Review', value: 'UNDER_REVIEW' },
  { label: 'Pending',      value: 'PENDING_REVIEW' },
  { label: 'More Info',    value: 'MORE_INFO' },
  { label: 'Resubmitted',  value: 'SUBMITTED_AGAIN' },
  { label: 'Human Review', value: 'HUMAN_REVIEW' },
  { label: 'Accepted',     value: 'ACCEPTED' },
  { label: 'Rejected',     value: 'REJECTED' },
];

const PRIORITY_COLORS: Record<string, string> = {
  HIGH:   'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW:    'bg-slate-100 text-slate-600',
};

interface IncomingClaimsTableProps {
  claims: InsuranceClaim[];
  // Optional pre-applied search term (e.g. from the header search ?q= param).
  initialQuery?: string;
}

export function IncomingClaimsTable({ claims, initialQuery }: IncomingClaimsTableProps) {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState<ClaimStatus | 'ALL'>('ALL');
  const [query, setQuery] = useState(initialQuery ?? '');

  // Keep the filter in sync when a new header search navigates here.
  useEffect(() => {
    setQuery(initialQuery ?? '');
  }, [initialQuery]);

  const byFilter = activeFilter === 'ALL' ? claims : claims.filter(c => c.status === activeFilter);
  const filtered = query
    ? byFilter.filter(c =>
        c.claim_id.toLowerCase().includes(query.toLowerCase()) ||
        c.procedure.toLowerCase().includes(query.toLowerCase()) ||
        c.patient_id.toLowerCase().includes(query.toLowerCase()))
    : byFilter;

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm animate-fade-in-up">
      {/* Filters */}
      <div className="flex overflow-x-auto border-b border-slate-200 bg-slate-50/50 no-scrollbar">
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
            className={clsx(
              'px-3 py-2.5 text-xs font-semibold whitespace-nowrap transition-all border-b-2 -mb-px flex-shrink-0',
              activeFilter === f.value
                ? 'border-brand-600 text-brand-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'
            )}
          >
            {f.label}
            {f.value !== 'ALL' && (
              <span className="ml-1 text-[10px] bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full">
                {claims.filter(c => c.status === f.value).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search bar */}
      <div className="px-4 py-3 border-b border-slate-100 bg-white">
        <div className="relative w-full md:w-96">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filter by claim ID, procedure, or patient…"
            className="pl-9 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all placeholder:text-slate-400"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No claims found" description="No claims match this filter." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[900px]">
            <thead className="bg-slate-50 text-slate-500 text-[11px] font-semibold uppercase tracking-wide border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5">Priority</th>
                <th className="px-4 py-2.5">Claim ID</th>
                <th className="px-4 py-2.5">Hospital</th>
                <th className="px-4 py-2.5">Procedure</th>
                <th className="px-4 py-2.5">Service Date</th>
                <th className="px-4 py-2.5">Attempt</th>
                <th className="px-4 py-2.5">Resubmission</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(c => (
                <tr
                  key={c.claim_id}
                  className="hover:bg-brand-50/20 cursor-pointer transition-all duration-150 group"
                  onClick={() => navigate(`/insurance/claims/${c.claim_id}`)}
                >
                  <td className="px-4 py-2.5">
                    {c.priority ? (
                      <span className={clsx('text-[9px] font-extrabold px-1.5 py-0.5 rounded', PRIORITY_COLORS[c.priority] ?? 'bg-slate-100 text-slate-600')}>
                        {c.priority}
                      </span>
                    ) : (
                      <span className="text-slate-300">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-semibold text-brand-600 group-hover:text-brand-700">{c.claim_id}</td>
                  <td className="px-4 py-2.5 text-slate-600 max-w-[150px] truncate font-medium">{c.hospital}</td>
                  <td className="px-4 py-2.5 text-slate-700 max-w-[180px] truncate">{c.procedure}</td>
                  <td className="px-4 py-2.5 text-slate-500">
                    {new Date(c.service_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </td>
                  <td className="px-4 py-2.5 font-semibold text-slate-700">Attempt {c.attempt ?? 1}</td>
                  <td className="px-4 py-2.5 text-[11px] font-semibold text-slate-600">
                    {(c.resubmission_status ?? 'NOT_REQUIRED').replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-2.5"><StatusBadge status={c.status} className="scale-95 origin-left" /></td>
                  <td className="px-4 py-2.5 text-slate-400 text-[11px]">
                    {new Date(c.submitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
