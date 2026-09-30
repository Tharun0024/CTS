import { useState, useEffect } from 'react';
import { ShieldCheck, Search, Filter, ArrowRight, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { getAuthorizations } from '../../services/authorizationApi';
import type { Authorization } from '../../services/authorizationApi';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';

export function Authorizations() {
  const [authorizations, setAuthorizations] = useState<Authorization[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const navigate = useNavigate();

  useEffect(() => {
    getAuthorizations().then(data => { setAuthorizations(data); setLoading(false); });
  }, []);

  const statuses = ['All', 'Approved', 'Pending', 'In Review', 'Denied', 'Expired'];
  const statusOptions = statuses.map(s => ({ label: s, value: s }));

  const filtered = authorizations.filter(a => {
    const matchesSearch = a.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.procedure.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.auth_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'All' || a.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'error' | 'info'; icon: any; iconColor: string }> = {
    'Approved': { variant: 'success', icon: CheckCircle2, iconColor: 'text-emerald-500' },
    'Pending': { variant: 'info', icon: Clock, iconColor: 'text-blue-500' },
    'In Review': { variant: 'warning', icon: AlertCircle, iconColor: 'text-violet-500' },
    'Denied': { variant: 'error', icon: XCircle, iconColor: 'text-rose-500' },
    'Expired': { variant: 'default', icon: Clock, iconColor: 'text-slate-400' },
  };

  const statCounts = {
    approved: authorizations.filter(a => a.status === 'Approved').length,
    pending: authorizations.filter(a => a.status === 'Pending').length,
    denied: authorizations.filter(a => a.status === 'Denied').length,
  };

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center shadow-md">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            Authorizations
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Track and manage prior authorization requests</p>
        </div>
        <Button
          onClick={() => navigate('/hospital/claims/new')}
          className="bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-lg shadow-emerald-200 hover:shadow-xl w-max border-0"
        >
          <ShieldCheck className="w-4 h-4 mr-2" /> New Authorization
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Approved', value: statCounts.approved, gradient: 'from-emerald-600 to-teal-700' },
          { label: 'Pending Review', value: statCounts.pending, gradient: 'from-blue-600 to-indigo-700' },
          { label: 'Denied', value: statCounts.denied, gradient: 'from-rose-600 to-red-700' },
        ].map(s => (
          <Card key={s.label} className={`bg-gradient-to-br ${s.gradient} border-0 shadow-md`}>
            <CardContent className="p-5">
              <p className="text-3xl font-bold text-white tracking-tight">{s.value}</p>
              <p className="text-xs font-semibold text-white/70 uppercase tracking-wide mt-1">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <CardHeader className="py-4 px-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search by ID, patient, or procedure..."
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
          {loading ? (
            <div className="p-8 space-y-3">
              {[1, 2, 3].map(i => <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse" />)}
            </div>
          ) : (
            <>
              <Table className="min-w-[700px]">
                <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="py-3 px-5">Auth ID & Patient</TableHead>
                    <TableHead className="py-3 px-5">Procedure & Provider</TableHead>
                    <TableHead className="py-3 px-5">Payer Info</TableHead>
                    <TableHead className="py-3 px-5">Status</TableHead>
                    <TableHead className="py-3 px-5 text-right"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map(auth => {
                    const sc = statusConfig[auth.status];
                    const StatusIcon = sc?.icon || Clock;
                    return (
                      <TableRow key={auth.auth_id} className="hover:bg-slate-50/60 transition-colors group">
                        <TableCell className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <p className="text-[13px] font-bold text-slate-900 font-mono">
                              {auth.auth_id}
                            </p>
                            {auth.priority === 'Urgent' && (
                              <Badge variant="error" className="px-1.5 py-0 rounded text-[9px] uppercase font-bold tracking-wider">Urgent</Badge>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 font-medium mt-0.5">{auth.patient_name}</p>
                        </TableCell>
                        <TableCell className="px-5 py-4 max-w-[220px]">
                          <p className="text-[13px] font-bold text-slate-800 truncate" title={auth.procedure}>{auth.procedure}</p>
                          <p className="text-xs text-slate-500 truncate mt-0.5">{auth.provider_name}</p>
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <p className="text-[13px] font-bold text-slate-800">{auth.payer}</p>
                          <p className="text-xs font-mono text-slate-500 mt-0.5">{auth.auth_number || 'N/A'}</p>
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <div className="flex items-center gap-1.5">
                            <StatusIcon className={clsx('w-3.5 h-3.5 flex-shrink-0', sc?.iconColor)} />
                            <Badge variant={sc?.variant || 'default'} className="px-2 py-0.5 rounded-md text-[11px] font-bold">
                              {auth.status}
                            </Badge>
                          </div>
                          {auth.expiry_date && <p className="text-[10px] font-medium text-slate-400 mt-1 ml-5">Exp: {auth.expiry_date}</p>}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-right">
                          {auth.claim_id ? (
                            <button
                              onClick={() => navigate(`/hospital/claims/${auth.claim_id}`)}
                              className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 justify-end w-full group-hover:underline"
                            >
                              View Claim <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={() => navigate('/hospital/claims/new')}
                              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 justify-end w-full group-hover:underline"
                            >
                              Create Claim <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {filtered.length === 0 && (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={5} className="px-6 py-16 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                            <ShieldCheck className="w-6 h-6 text-slate-400" />
                          </div>
                          <p className="text-slate-500 font-medium text-sm">No authorizations found</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              
              {!loading && filtered.length > 0 && (
                <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-medium text-slate-500">
                  Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of <span className="font-semibold text-slate-700">{authorizations.length}</span> authorizations
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
