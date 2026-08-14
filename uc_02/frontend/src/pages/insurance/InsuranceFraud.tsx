import { useState } from 'react';
import { XOctagon, Search, Filter, AlertTriangle, ArrowRight, TrendingUp, CheckCircle2, DollarSign } from 'lucide-react';
import { mockDenials } from '../../mock/denials';

import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';

export function InsuranceFraud() {
  const [fraudAlerts] = useState(mockDenials);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const navigate = useNavigate();

  const statuses = ['All', 'Open', 'In Appeal', 'Won', 'Lost', 'Closed'];
  const statusOptions = statuses.map(s => ({ label: s, value: s }));

  const filtered = fraudAlerts.filter(d => {
    const matchesSearch = d.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.claim_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'All' || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
    'Open': { variant: 'error' },
    'In Appeal': { variant: 'warning' },
    'Won': { variant: 'success' },
    'Lost': { variant: 'default' },
    'Closed': { variant: 'default' },
  };

  const totalDeniedAmount = fraudAlerts.reduce((acc, d) => acc + d.denied_amount, 0);
  const wonAmount = fraudAlerts.filter(d => d.status === 'Won').reduce((acc, d) => acc + d.denied_amount, 0);
  const openCount = fraudAlerts.filter(d => d.status === 'Open').length;
  const inAppealCount = fraudAlerts.filter(d => d.status === 'In Appeal').length;
  const wonCount = fraudAlerts.filter(d => d.status === 'Won').length;
  const appealSuccessRate = fraudAlerts.filter(d => d.status === 'Won' || d.status === 'Lost').length > 0
    ? Math.round((wonCount / (wonCount + fraudAlerts.filter(d => d.status === 'Lost').length)) * 100)
    : 0;

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-rose-500 to-red-700 flex items-center justify-center shadow-md">
              <XOctagon className="w-4 h-4 text-white" />
            </div>
            fraudAlerts Management
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Track, appeal, and recover denied claims</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-rose-600 to-red-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-rose-200" />
              <span className="text-[10px] font-bold text-rose-200 uppercase tracking-wider">Open</span>
            </div>
            <p className="text-3xl font-bold text-white tracking-tight">{openCount}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Pending review</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-amber-500 to-orange-600 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-amber-200" />
              <span className="text-[10px] font-bold text-amber-200 uppercase tracking-wider">In Appeal</span>
            </div>
            <p className="text-3xl font-bold text-white tracking-tight">{inAppealCount}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Active appeals</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-600 to-teal-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-200" />
              <span className="text-[10px] font-bold text-emerald-200 uppercase tracking-wider">Won</span>
            </div>
            <p className="text-3xl font-bold text-white tracking-tight">{wonCount}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">{appealSuccessRate}% success rate</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-violet-600 to-purple-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-4 h-4 text-violet-200" />
              <span className="text-[10px] font-bold text-violet-200 uppercase tracking-wider">Recovered</span>
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">${(wonAmount / 1000).toFixed(0)}k</p>
            <p className="text-xs text-white/70 font-semibold mt-1">of ${(totalDeniedAmount / 1000).toFixed(0)}k denied</p>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <CardHeader className="py-4 px-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search by Claim ID or Patient..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 w-full"
            />
          </div>
          <div className="flex items-center gap-2 w-full sm:w-64">
            <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <Select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              options={statusOptions}
            />
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Table className="min-w-[700px]">
            <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
              <TableRow className="hover:bg-transparent">
                <TableHead className="py-3 px-5">Claim & Patient</TableHead>
                <TableHead className="py-3 px-5">Denial Reason</TableHead>
                <TableHead className="py-3 px-5 text-right">Amount</TableHead>
                <TableHead className="py-3 px-5">Status & Deadline</TableHead>
                <TableHead className="py-3 px-5"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(denial => (
                <TableRow key={denial.denial_id} className="hover:bg-slate-50/60 transition-colors group">
                  <TableCell className="px-5 py-4">
                    <p className="text-[13px] font-bold text-slate-900 font-mono">{denial.claim_id}</p>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">{denial.patient_name}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 max-w-[230px]">
                    <p className="text-[13px] font-bold text-slate-800 truncate" title={denial.denial_reason}>{denial.denial_reason}</p>
                    <p className="text-[11px] text-rose-600 font-mono font-bold mt-0.5">{denial.reason_code}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <p className="text-sm font-bold text-slate-900 tracking-tight">${denial.denied_amount.toLocaleString()}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4">
                    <Badge variant={statusConfig[denial.status]?.variant || 'default'} className="px-2 py-0.5 text-[11px] font-bold">
                      {denial.status}
                    </Badge>
                    {(denial.status === 'Open' || denial.status === 'In Appeal') && (
                      <p className="text-[10px] text-slate-500 mt-1.5 font-medium">
                        Appeal by: {new Date(denial.appeal_deadline).toLocaleDateString()}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <button
                      onClick={() => navigate(`/hospital/claims/${denial.claim_id}`)}
                      className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 justify-end w-full group-hover:underline"
                    >
                      View Claim <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={5} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-slate-400" />
                      </div>
                      <p className="text-slate-500 font-medium text-sm">No fraudAlerts found</p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {filtered.length > 0 && (
            <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-medium text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of <span className="font-semibold text-slate-700">{fraudAlerts.length}</span> fraudAlerts
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
