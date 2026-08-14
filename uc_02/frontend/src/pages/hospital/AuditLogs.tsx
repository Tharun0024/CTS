import { useState, useEffect } from 'react';
import { Terminal, Search, Database, Clock, User, Activity, Download } from 'lucide-react';
import { getAuditLogs } from '../../services/auditApi';
import type { AuditLog } from '../../services/auditApi';
import { clsx } from 'clsx';
import { Card, CardContent } from '../../components/ui/Card';


export function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [actionFilter, setActionFilter] = useState('All');

  useEffect(() => {
    getAuditLogs().then(data => { setLogs(data); setLoading(false); });
  }, []);

  const actions = ['All', 'LOGIN', 'VIEW', 'UPDATE', 'CREATE', 'DELETE', 'EXPORT'];

  const filtered = logs.filter(log => {
    const matchesSearch = log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          log.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          log.ip_address.includes(searchTerm);
    const matchesAction = actionFilter === 'All' || log.action === actionFilter;
    return matchesSearch && matchesAction;
  });

  const actionColors: Record<string, string> = {
    'LOGIN': 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    'VIEW': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    'UPDATE': 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    'CREATE': 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    'DELETE': 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    'EXPORT': 'text-violet-400 bg-violet-500/10 border-violet-500/20',
  };

  const stats = [
    { label: 'Total Events (24h)', value: '14,289', icon: Activity },
    { label: 'Active Users', value: '142', icon: User },
    { label: 'DB Operations', value: '8.4k', icon: Database },
    { label: 'Avg Latency', value: '42ms', icon: Clock },
  ];

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center shadow-md">
              <Terminal className="w-4 h-4 text-white" />
            </div>
            System Audit Logs
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Immutable record of all system activity and data access</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Logging Active
          </span>
          <button className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-2">
            <Download className="w-3.5 h-3.5" /> Export Logs
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(stat => (
          <Card key={stat.label} className="p-4">
            <CardContent className="p-0 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 flex-shrink-0">
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">{stat.value}</p>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">{stat.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Terminal View */}
      <div className="bg-[#0B1120] rounded-2xl shadow-xl overflow-hidden border border-slate-800">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-[#0F172A]">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-rose-500" />
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="grep search..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-8 py-1 bg-slate-900 border border-slate-700 focus:border-slate-500 rounded text-xs text-slate-300 w-48 font-mono placeholder:text-slate-600 focus:outline-none transition-colors"
              />
            </div>
            <select
              value={actionFilter}
              onChange={e => setActionFilter(e.target.value)}
              className="py-1 px-2 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 font-mono focus:outline-none focus:border-slate-500"
            >
              {actions.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>

        <div className="p-4 overflow-x-auto min-h-[400px]">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex gap-4 opacity-50 animate-pulse">
                  <div className="w-32 h-4 bg-slate-800 rounded" />
                  <div className="w-16 h-4 bg-slate-800 rounded" />
                  <div className="flex-1 h-4 bg-slate-800 rounded" />
                </div>
              ))}
            </div>
          ) : (
            <table className="w-full text-left font-mono text-[11px] whitespace-nowrap">
              <thead>
                <tr className="text-slate-500 border-b border-slate-800/50">
                  <th className="pb-2 font-normal w-40">TIMESTAMP</th>
                  <th className="pb-2 font-normal w-24">ACTION</th>
                  <th className="pb-2 font-normal w-32">USER</th>
                  <th className="pb-2 font-normal">DETAILS</th>
                  <th className="pb-2 font-normal w-32 text-right">IP ADDRESS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filtered.map(log => (
                  <tr key={log.log_id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="py-2.5 text-slate-400">
                      {new Date(log.timestamp).toISOString().replace('T', ' ').slice(0, 19)}
                    </td>
                    <td className="py-2.5">
                      <span className={clsx('px-1.5 py-0.5 rounded border', actionColors[log.action] || 'text-slate-400 bg-slate-800 border-slate-700')}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 text-emerald-400">{log.user}</td>
                    <td className="py-2.5 text-slate-300 truncate max-w-md" title={log.description}>
                      <span className="text-slate-500 mr-2">&gt;</span>{log.description}
                    </td>
                    <td className="py-2.5 text-slate-500 text-right">{log.ip_address}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-600">
                      $ grep "{searchTerm}" /var/log/audit.log<br/>
                      No matches found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
