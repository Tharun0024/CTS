import { useState, useEffect } from 'react';
import { DollarSign, Search, Filter, CreditCard, CheckCircle2, AlertTriangle, ArrowRight, TrendingUp, Banknote } from 'lucide-react';
import { getPayments } from '../../services/paymentsApi';
import type { Payment } from '../../types/payment';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';

import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';

export function Payments() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const navigate = useNavigate();

  useEffect(() => { getPayments().then(data => setPayments(data)); }, []);

  const statuses = ['All', 'Paid', 'Pending', 'Partial', 'Denied', 'Appealing'];
  const statusOptions = statuses.map(s => ({ label: s, value: s }));

  const filtered = payments.filter(p => {
    const matchesSearch = p.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.claim_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.payer.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'All' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusVariantMap: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    'Paid': 'success',
    'Pending': 'info',
    'Partial': 'warning',
    'Denied': 'error',
    'Appealing': 'default',
  };

  const totalOutstanding = payments.filter(p => p.status === 'Pending' || p.status === 'Partial')
    .reduce((acc, curr) => acc + (curr.approved_amount - curr.paid_amount), 0);
  const totalPaid = payments.filter(p => p.status === 'Paid').reduce((acc, curr) => acc + curr.paid_amount, 0);
  const totalBilled = payments.reduce((acc, curr) => acc + curr.billed_amount, 0);
  const totalPatientResp = payments.reduce((acc, curr) => acc + curr.patient_responsibility, 0);
  const collectionRate = totalBilled > 0 ? Math.round((totalPaid / totalBilled) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center shadow-md">
              <DollarSign className="w-4 h-4 text-white" />
            </div>
            Payments & Revenue
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Track claim payments and outstanding balances</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-amber-500 to-orange-600 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-amber-200" />
              <span className="text-[10px] font-bold text-amber-200 uppercase tracking-wider">Outstanding AR</span>
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">${totalOutstanding.toLocaleString()}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Pending from payers</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-600 to-teal-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-200" />
              <span className="text-[10px] font-bold text-emerald-200 uppercase tracking-wider">Collected</span>
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">${totalPaid.toLocaleString()}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Successfully reconciled</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-600 to-indigo-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <CreditCard className="w-4 h-4 text-blue-200" />
              <span className="text-[10px] font-bold text-blue-200 uppercase tracking-wider">Patient Resp.</span>
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">${totalPatientResp.toLocaleString()}</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Copays & deductibles</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-violet-600 to-purple-700 border-0 shadow-md">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-violet-200" />
              <span className="text-[10px] font-bold text-violet-200 uppercase tracking-wider">Collection Rate</span>
            </div>
            <p className="text-3xl font-bold text-white tracking-tight">{collectionRate}%</p>
            <p className="text-xs text-white/70 font-semibold mt-1">Target: 85%</p>
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
              placeholder="Search by Claim ID, Payer, or Patient..."
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
          <Table className="min-w-[800px]">
            <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
              <TableRow className="hover:bg-transparent">
                <TableHead className="py-3 px-5">Claim / Patient</TableHead>
                <TableHead className="py-3 px-5">Payer / Procedure</TableHead>
                <TableHead className="py-3 px-5 text-right">Billed</TableHead>
                <TableHead className="py-3 px-5 text-right">Paid</TableHead>
                <TableHead className="py-3 px-5 text-right">Pt. Resp.</TableHead>
                <TableHead className="py-3 px-5">Status</TableHead>
                <TableHead className="py-3 px-5"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(payment => (
                <TableRow key={payment.payment_id} className="hover:bg-slate-50/60 transition-colors group">
                  <TableCell className="px-5 py-4">
                    <p className="text-[13px] font-bold text-slate-900 font-mono">{payment.claim_id}</p>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">{payment.patient_name}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 max-w-[180px]">
                    <p className="text-[13px] font-bold text-slate-800 truncate">{payment.payer}</p>
                    <p className="text-xs text-slate-500 truncate" title={payment.procedure}>{payment.procedure}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <p className="text-[13px] font-semibold text-slate-600">${payment.billed_amount.toLocaleString()}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <p className="text-[13px] font-bold text-emerald-600">${payment.paid_amount.toLocaleString()}</p>
                    {payment.payment_date && (
                      <p className="text-[10px] text-slate-400 mt-0.5">{new Date(payment.payment_date).toLocaleDateString()}</p>
                    )}
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <p className="text-[13px] font-semibold text-slate-700">${payment.patient_responsibility.toLocaleString()}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4">
                    <Badge variant={statusVariantMap[payment.status] || 'default'} className="px-2 py-0.5 text-[11px] font-bold">
                      {payment.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <button
                      onClick={() => navigate(`/hospital/claims/${payment.claim_id}`)}
                      className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 justify-end w-full group-hover:underline"
                    >
                      View <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={7} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                        <Banknote className="w-6 h-6 text-slate-400" />
                      </div>
                      <p className="text-slate-500 font-medium text-sm">No payments found</p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {filtered.length > 0 && (
            <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-medium text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of <span className="font-semibold text-slate-700">{payments.length}</span> payments
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
