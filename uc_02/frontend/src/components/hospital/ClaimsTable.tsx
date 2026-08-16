import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '../ui/Badge';
import { EmptyState } from '../common/EmptyState';
import { clsx } from 'clsx';
import type { Claim, ClaimStatus } from '../../types/claim';
import { Search } from 'lucide-react';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/Table';

const TABS: { label: string; value: ClaimStatus | 'ALL' }[] = [
  { label: 'All',           value: 'ALL' },
  { label: 'Submitted',     value: 'SUBMITTED' },
  { label: 'Processing',    value: 'PROCESSING' },
  { label: 'Accepted',      value: 'ACCEPTED' },
  { label: 'Rejected',      value: 'REJECTED' },
  { label: 'More Info',     value: 'MORE_INFO' },
  { label: 'Human Review',  value: 'HUMAN_REVIEW' },
  { label: 'Resubmitted',   value: 'SUBMITTED_AGAIN' },
];

const statusBadgeVariant: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
  'ACCEPTED': 'success',
  'REJECTED': 'error',
  'MORE_INFO': 'warning',
  'HUMAN_REVIEW': 'info',
  'PROCESSING': 'default',
  'SUBMITTED': 'default',
  'UNDER_REVIEW': 'info'
};

const statusDisplay: Record<string, string> = {
  'REJECTED': 'Rejected',
  'MORE_INFO': 'Needs Information',
  'HUMAN_REVIEW': 'Under Human Review',
  'ACCEPTED': 'Accepted',
  'PROCESSING': 'Processing',
  'SUBMITTED': 'Submitted',
  'UNDER_REVIEW': 'Under Review'
};

interface ClaimsTableProps {
  claims: Claim[];
  portal: 'hospital' | 'insurance';
}

export function ClaimsTable({ claims, portal }: ClaimsTableProps) {
  const navigate    = useNavigate();
  const [tab, setTab] = useState<ClaimStatus | 'ALL'>('ALL');
  const [query, setQuery] = useState('');

  const isHospital   = portal === 'hospital';
  const accentColor  = isHospital ? 'text-emerald-700'    : 'text-indigo-700';
  const accentBg     = isHospital ? 'bg-emerald-50'       : 'bg-indigo-50';
  const activeBadge  = isHospital ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 'bg-indigo-100 text-indigo-700 border-indigo-200';
  const rowHover     = isHospital ? 'hover:bg-emerald-50/60' : 'hover:bg-indigo-50/60';
  const idColor      = isHospital ? 'text-emerald-700 group-hover:text-emerald-900' : 'text-indigo-700 group-hover:text-indigo-900';

  const byTab = tab === 'ALL' ? claims : claims.filter(c => c.status === tab);
  const filtered = query
    ? byTab.filter(c =>
        c.claim_id.toLowerCase().includes(query.toLowerCase()) ||
        c.procedure.toLowerCase().includes(query.toLowerCase()) ||
        c.patient_id.toLowerCase().includes(query.toLowerCase()))
    : byTab;

  const detailPath = (id: string) => `/${portal}/claims/${id}`;

  return (
    <Card className="overflow-hidden animate-fade-in-up">
      {/* Tab bar */}
      <div className="flex overflow-x-auto no-scrollbar border-b border-slate-100 bg-slate-50/50">
        {TABS.map(t => {
          const cnt = t.value === 'ALL' ? claims.length : claims.filter(c => c.status === t.value).length;
          const isActive = tab === t.value;
          return (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-3 text-[13px] font-semibold whitespace-nowrap transition-all border-b-2 -mb-px flex-shrink-0',
                isActive
                  ? `border-current ${accentColor} ${accentBg}`
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100/50'
              )}
            >
              {t.label}
              <span className={clsx(
                'text-[10px] font-bold px-1.5 py-0.5 rounded-full border',
                isActive ? activeBadge : 'bg-slate-100 text-slate-500 border-slate-200'
              )}>
                {cnt}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search bar */}
      <CardHeader className="py-4 px-5 border-b border-slate-100 bg-white">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filter by claim ID, procedure, or patient…"
            className="pl-9 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg w-full md:w-96 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-slate-400"
          />
        </div>
      </CardHeader>

      {/* Table */}
      <CardContent className="p-0">
        {filtered.length === 0 ? (
          <div className="py-16 bg-slate-50/50">
            <EmptyState title="No claims found" description="Try adjusting your filter or search." />
          </div>
        ) : (
          <>
            <Table className="min-w-[700px]">
              <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                <TableRow className="hover:bg-transparent">
                  <TableHead className="py-3 px-5">Claim ID</TableHead>
                  <TableHead className="py-3 px-5">Patient ID</TableHead>
                  <TableHead className="py-3 px-5">Procedure</TableHead>
                  <TableHead className="py-3 px-5">Service Date</TableHead>
                  <TableHead className="py-3 px-5">Attempt</TableHead>
                  <TableHead className="py-3 px-5">Evidence Request</TableHead>
                  <TableHead className="py-3 px-5">Resubmission</TableHead>
                  <TableHead className="py-3 px-5">Status</TableHead>
                  <TableHead className="py-3 px-5 text-right">Last Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map(c => (
                  <TableRow
                    key={c.claim_id}
                    className={clsx('cursor-pointer transition-colors duration-150', rowHover)}
                    onClick={() => navigate(detailPath(c.claim_id))}
                  >
                    <TableCell className="px-5 py-3">
                      <span className={clsx('font-bold font-mono text-sm', idColor)}>{c.claim_id}</span>
                    </TableCell>
                    <TableCell className="px-5 py-3 text-slate-700 font-medium text-sm">{c.patient_id}</TableCell>
                    <TableCell className="px-5 py-3 text-slate-600 max-w-[220px] truncate text-sm">{c.procedure}</TableCell>
                    <TableCell className="px-5 py-3 text-sm text-slate-500">
                      {new Date(c.service_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </TableCell>
                    <TableCell className="px-5 py-3 text-sm font-semibold text-slate-700">Attempt {c.attempt ?? 1}</TableCell>
                    <TableCell className="px-5 py-3 text-[11px] font-semibold text-slate-600">
                      {(c.evidence_request_status ?? 'CLOSED').replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell className="px-5 py-3 text-[11px] font-semibold text-slate-600">
                      {(c.resubmission_status ?? 'NOT_REQUIRED').replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell className="px-5 py-3">
                      <Badge variant={statusBadgeVariant[c.status] || 'default'}>
                        {statusDisplay[c.status] || c.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-5 py-3 text-xs font-medium text-slate-400 text-right">
                      {new Date(c.updated_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-medium text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of <span className="font-semibold text-slate-700">{claims.length}</span> claims
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
