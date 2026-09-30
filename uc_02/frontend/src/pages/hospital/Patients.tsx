import { useState, useEffect } from 'react';
import { Users, Search, ChevronRight, UserCheck, Activity, Heart } from 'lucide-react';
import { getPatients } from '../../services/patientsApi';
import type { Patient } from '../../types/patient';
import { Modal } from '../../components/common/Modal';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';

export function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [statusFilter, setStatusFilter] = useState('All');

  useEffect(() => {
    getPatients().then(data => { setPatients(data); setLoading(false); });
  }, []);

  const statuses = ['All', 'Active', 'Inactive', 'Critical'];
  const filtered = patients.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.patient_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchStatus = statusFilter === 'All' || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'error' | 'info'; dot: string }> = {
    Active: { variant: 'success', dot: 'bg-emerald-500' },
    Inactive: { variant: 'default', dot: 'bg-slate-400' },
    Critical: { variant: 'error', dot: 'bg-rose-500' },
  };

  const statCounts = {
    total: patients.length,
    active: patients.filter(p => p.status === 'Active').length,
    critical: patients.filter(p => p.status === 'Critical').length,
  };

  const getInitials = (name: string) => name.split(' ').map(n => n[0]).join('').slice(0, 2);
  const getAvatarGradient = (name: string) => {
    const gradients = [
      'from-emerald-500 to-teal-600',
      'from-blue-500 to-indigo-600',
      'from-violet-500 to-purple-600',
      'from-rose-500 to-pink-600',
      'from-amber-500 to-orange-600',
    ];
    const index = name.charCodeAt(0) % gradients.length;
    return gradients[index];
  };

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md">
              <Users className="w-4 h-4 text-white" />
            </div>
            Patient Directory
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Manage and view patient records and insurance coverage</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Patients', value: statCounts.total, icon: Users, gradient: 'from-slate-600 to-slate-800' },
          { label: 'Active', value: statCounts.active, icon: UserCheck, gradient: 'from-emerald-500 to-teal-700' },
          { label: 'Critical', value: statCounts.critical, icon: Heart, gradient: 'from-rose-500 to-red-700' },
        ].map(stat => (
          <Card key={stat.label} className={`bg-gradient-to-br ${stat.gradient} border-0 shadow-md`}>
            <CardContent className="p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center">
                  <stat.icon className="w-4 h-4 text-white/90" />
                </div>
              </div>
              <p className="text-3xl font-bold text-white tracking-tight">{stat.value}</p>
              <p className="text-xs font-semibold text-white/70 uppercase tracking-wide mt-1">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table Panel */}
      <Card className="overflow-hidden">
        {/* Filters */}
        <CardHeader className="py-4 px-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="relative w-full sm:max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search by name or patient ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 w-full"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {statuses.map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
                  statusFilter === s
                    ? 'bg-slate-800 text-white border-slate-800 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {loading ? (
            <div className="p-8">
              <div className="space-y-4">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="flex items-center gap-4 animate-pulse">
                    <div className="w-10 h-10 rounded-full bg-slate-200" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-slate-200 rounded w-1/3" />
                      <div className="h-3 bg-slate-100 rounded w-1/4" />
                    </div>
                    <div className="w-20 h-6 bg-slate-200 rounded-full" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <Table className="min-w-[700px]">
                <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="py-3 px-5">Patient</TableHead>
                    <TableHead className="py-3 px-5">ID & Demographics</TableHead>
                    <TableHead className="py-3 px-5">Insurance</TableHead>
                    <TableHead className="py-3 px-5">Status</TableHead>
                    <TableHead className="py-3 px-5 text-right"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map(p => (
                    <TableRow
                      key={p.patient_id}
                      className="hover:bg-emerald-50/50 transition-colors cursor-pointer group"
                      onClick={() => setSelectedPatient(p)}
                    >
                      <TableCell className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${getAvatarGradient(p.name)} flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-sm`}>
                            {getInitials(p.name)}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">{p.name}</p>
                            <p className="text-xs text-slate-500 font-medium">{p.email}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <p className="text-[13px] font-bold text-slate-700 font-mono">{p.patient_id}</p>
                        <p className="text-xs text-slate-500 font-medium mt-0.5">{p.age} yrs • {p.gender}</p>
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <p className="text-[13px] font-bold text-slate-800">{p.payer}</p>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{p.policy_id}</p>
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <Badge variant={statusConfig[p.status]?.variant || 'default'} className="flex items-center gap-1.5 w-fit">
                          <span className={`w-1.5 h-1.5 rounded-full ${statusConfig[p.status]?.dot || 'bg-slate-400'}`} />
                          {p.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-5 py-4 text-right">
                        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-500 transition-colors inline-block" />
                      </TableCell>
                    </TableRow>
                  ))}
                  {filtered.length === 0 && (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={5} className="px-6 py-16 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                            <Users className="w-6 h-6 text-slate-400" />
                          </div>
                          <p className="text-slate-500 font-medium text-sm">No patients found matching "{searchTerm}"</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              
              {!loading && filtered.length > 0 && (
                <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-medium text-slate-500">
                  Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of <span className="font-semibold text-slate-700">{patients.length}</span> patients
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Patient Modal */}
      <Modal isOpen={!!selectedPatient} onClose={() => setSelectedPatient(null)} title="Patient Profile" size="lg">
        {selectedPatient && (
          <div className="space-y-5">
            <div className="flex items-center gap-4 p-5 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl border border-emerald-100">
              <div className={`w-14 h-14 rounded-full bg-gradient-to-br ${getAvatarGradient(selectedPatient.name)} flex items-center justify-center text-white font-bold text-xl shadow-sm`}>
                {getInitials(selectedPatient.name)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-slate-900 tracking-tight">{selectedPatient.name}</h2>
                <p className="text-sm text-slate-500 font-medium mt-1">{selectedPatient.patient_id} • {selectedPatient.gender} • {selectedPatient.age} yrs</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={statusConfig[selectedPatient.status]?.variant || 'default'} className="px-3 py-1 text-sm font-semibold flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${statusConfig[selectedPatient.status]?.dot}`} />
                  {selectedPatient.status}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card className="shadow-sm">
                <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Contact Info</h3>
                </CardHeader>
                <CardContent className="p-4 space-y-3 text-sm text-slate-700">
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">Phone:</span>
                    <span className="font-medium">{selectedPatient.phone}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">Email:</span>
                    <span className="font-medium">{selectedPatient.email}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">Address:</span>
                    <span className="font-medium">{selectedPatient.address}</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Medical Info</h3>
                </CardHeader>
                <CardContent className="p-4 space-y-3 text-sm text-slate-700">
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">Blood Type:</span>
                    <span className="font-bold text-rose-600 text-lg">{selectedPatient.blood_type}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">DOB:</span>
                    <span className="font-medium">{selectedPatient.dob}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-500 text-xs block mb-0.5">Primary MD:</span>
                    <span className="font-medium">{selectedPatient.primary_physician}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="shadow-sm">
              <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="w-4 h-4" /> Active Diagnoses
                </h3>
              </CardHeader>
              <CardContent className="p-4">
                <div className="flex flex-wrap gap-2">
                  {selectedPatient.diagnoses.map(d => (
                    <Badge key={d} className="text-slate-700 bg-white border-slate-200">
                      {d}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="flex items-center justify-between p-5 bg-gradient-to-r from-emerald-600 to-teal-700 rounded-2xl text-white shadow-md">
              <div>
                <p className="text-xs font-bold text-emerald-200 uppercase tracking-wider mb-1">Insurance Coverage</p>
                <p className="text-base font-bold">{selectedPatient.payer}</p>
                <p className="text-sm text-emerald-200 font-mono mt-0.5">{selectedPatient.policy_id}</p>
              </div>
              <div className="text-right">
                <p className="text-xs font-bold text-emerald-200 uppercase tracking-wider mb-1">Active Claims</p>
                <p className="text-4xl font-bold tracking-tight">{selectedPatient.claims_count}</p>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
