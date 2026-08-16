import { useState, useEffect } from 'react';
import { Calendar, Plus, Clock, Video, Stethoscope, Activity, FileText, Filter, ChevronRight } from 'lucide-react';
import { getAppointments } from '../../services/appointmentsApi';
import type { Appointment } from '../../types/appointment';
import { clsx } from 'clsx';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export function Appointments() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('All');

  useEffect(() => {
    getAppointments().then(data => { setAppointments(data); setLoading(false); });
  }, []);

  const types = ['All', 'Consultation', 'Procedure', 'Follow-up', 'Lab', 'Imaging', 'Emergency'];

  const filtered = appointments.filter(a => {
    const matchDate = !dateFilter || a.date === dateFilter;
    const matchType = typeFilter === 'All' || a.type === typeFilter;
    return matchDate && matchType;
  });

  const sorted = [...filtered].sort((a, b) => a.time.localeCompare(b.time));

  const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'error' | 'info'; dot: string }> = {
    'Scheduled': { variant: 'info', dot: 'bg-blue-500' },
    'In Progress': { variant: 'success', dot: 'bg-emerald-500' },
    'Completed': { variant: 'default', dot: 'bg-slate-400' },
    'Cancelled': { variant: 'error', dot: 'bg-rose-500' },
    'No Show': { variant: 'warning', dot: 'bg-amber-500' },
  };

  const typeIcons: Record<string, any> = {
    'Consultation': Stethoscope,
    'Procedure': Activity,
    'Follow-up': Clock,
    'Lab': FileText,
    'Imaging': Video,
    'Emergency': Activity,
  };

  const typeColors: Record<string, string> = {
    'Consultation': 'from-emerald-500 to-teal-600',
    'Procedure': 'from-blue-500 to-indigo-600',
    'Follow-up': 'from-violet-500 to-purple-600',
    'Lab': 'from-amber-500 to-orange-600',
    'Imaging': 'from-pink-500 to-rose-600',
    'Emergency': 'from-rose-600 to-red-700',
  };

  const todayCount = appointments.filter(a => a.date === new Date().toISOString().split('T')[0]).length;
  const scheduledCount = appointments.filter(a => a.status === 'Scheduled').length;
  const inProgressCount = appointments.filter(a => a.status === 'In Progress').length;

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
              <Calendar className="w-4 h-4 text-white" />
            </div>
            Appointments
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Manage patient schedules and room allocations</p>
        </div>
        <Button className="shadow-lg shadow-emerald-200 hover:shadow-xl w-max">
          <Plus className="w-4 h-4 mr-2" /> Schedule New
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Today's Appointments", value: todayCount, gradient: 'from-blue-600 to-indigo-700' },
          { label: 'Scheduled', value: scheduledCount, gradient: 'from-violet-600 to-purple-700' },
          { label: 'In Progress', value: inProgressCount, gradient: 'from-emerald-600 to-teal-700' },
        ].map(s => (
          <Card key={s.label} className={`bg-gradient-to-br ${s.gradient} border-0 shadow-md`}>
            <CardContent className="p-5">
              <p className="text-3xl font-bold text-white tracking-tight">{s.value}</p>
              <p className="text-xs font-semibold text-white/70 uppercase tracking-wide mt-1">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table/List */}
      <Card className="overflow-hidden">
        {/* Filters */}
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-3">
          <div className="flex flex-col sm:flex-row gap-3 items-center">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500">Date:</span>
              <input
                type="date"
                value={dateFilter}
                onChange={e => setDateFilter(e.target.value)}
                className="bg-white border border-slate-200 focus:border-emerald-500 rounded-lg text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                style={{ colorScheme: 'light' }}
              />
              {dateFilter && (
                <button onClick={() => setDateFilter('')} className="text-xs font-bold text-emerald-600 hover:underline">Clear</button>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {types.map(t => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
                  typeFilter === t
                    ? 'bg-slate-800 text-white border-slate-800 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="divide-y divide-slate-50">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="p-5 flex items-center gap-4 animate-pulse">
                <div className="w-14 h-14 rounded-2xl bg-slate-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-200 rounded w-1/3" />
                  <div className="h-3 bg-slate-100 rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {sorted.map(appt => {
              const Icon = typeIcons[appt.type] || Calendar;
              const grad = typeColors[appt.type] || 'from-slate-500 to-slate-700';
              const sc = statusConfig[appt.status];
              return (
                <div key={appt.appointment_id} className="p-4 sm:p-5 hover:bg-slate-50/50 transition-colors flex flex-col sm:flex-row sm:items-center gap-4 group cursor-pointer">
                  {/* Time */}
                  <div className="flex-shrink-0 text-center sm:text-left sm:w-20">
                    <p className="text-lg font-bold text-slate-900 tracking-tight">{appt.time}</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{appt.duration_minutes} min</p>
                  </div>

                  {/* Icon */}
                  <div className={`w-11 h-11 rounded-2xl bg-gradient-to-br ${grad} flex items-center justify-center flex-shrink-0 shadow-sm`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-bold text-slate-900">{appt.patient_name}</h3>
                      {appt.priority === 'Emergency' && (
                        <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 text-[9px] uppercase font-black tracking-wider">Emergency</span>
                      )}
                    </div>
                    <p className="text-[12px] font-medium text-slate-600 mt-0.5">
                      {appt.type} with <span className="font-bold">{appt.provider_name}</span>
                    </p>
                    {appt.notes && <p className="text-[11px] text-slate-400 mt-1 truncate">{appt.notes}</p>}
                  </div>

                  {/* Right */}
                  <div className="flex items-center gap-4 sm:justify-end">
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Room</p>
                      <p className="text-sm font-bold text-slate-800">{appt.room || 'TBD'}</p>
                    </div>
                    <Badge variant={sc?.variant || 'default'} className="flex items-center gap-1.5 w-fit">
                      <span className={`w-1.5 h-1.5 rounded-full ${sc?.dot || 'bg-slate-400'}`} />
                      {appt.status}
                    </Badge>
                    <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-500 transition-colors hidden sm:block" />
                  </div>
                </div>
              );
            })}
            {sorted.length === 0 && (
              <div className="py-16 text-center">
                <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                  <Calendar className="w-6 h-6 text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium text-sm">No appointments scheduled</p>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
