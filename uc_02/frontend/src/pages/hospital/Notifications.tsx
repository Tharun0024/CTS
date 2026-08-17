import { useState, useEffect } from 'react';
import { Bell, AlertTriangle, Info, ShieldAlert, Check, Search, Users, XCircle } from 'lucide-react';
import { getNotifications, markAsRead as apiMarkAsRead, markAllRead as apiMarkAllRead } from '../../services/notificationsApi';
import type { Notification } from '../../types/claim';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('All');
  const navigate = useNavigate();

  useEffect(() => {
    getNotifications().then(data => { setNotifications(data); setLoading(false); });
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  const markAllRead = () => {
    apiMarkAllRead();
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const markAsRead = (id: string) => {
    apiMarkAsRead(id);
    setNotifications(prev => prev.map(n => n.notification_id === id ? { ...n, read: true } : n));
  };

  const filtered = notifications.filter(n => {
    const matchesSearch = n.message.toLowerCase().includes(searchTerm.toLowerCase());
    let matchesTab = true;
    if (activeTab === 'Unread') matchesTab = !n.read;
    else if (activeTab === 'Denial') matchesTab = n.type === 'DECISION' || n.type === 'PROVIDER_DECLINE' || n.type === 'RECOVERY_FAILED';
    else if (activeTab === 'Review') matchesTab = n.type === 'HUMAN_REVIEW';
    else if (activeTab === 'More Info') matchesTab = n.type === 'MORE_INFO';
    return matchesSearch && matchesTab;
  });

  // Icon config keyed by the real derived notification types (alarming
  // events only — approvals never produce notifications).
  const getIconConfig = (type: string) => {
    switch (type) {
      case 'DECISION': return { icon: ShieldAlert, bg: 'bg-rose-100', color: 'text-rose-600', border: 'border-rose-200' };
      case 'PROVIDER_DECLINE': return { icon: XCircle, bg: 'bg-rose-100', color: 'text-rose-600', border: 'border-rose-200' };
      case 'RECOVERY_FAILED': return { icon: XCircle, bg: 'bg-rose-100', color: 'text-rose-600', border: 'border-rose-200' };
      case 'HUMAN_REVIEW': return { icon: Users, bg: 'bg-blue-100', color: 'text-blue-600', border: 'border-blue-200' };
      case 'MORE_INFO': return { icon: AlertTriangle, bg: 'bg-amber-100', color: 'text-amber-600', border: 'border-amber-200' };
      default: return { icon: Info, bg: 'bg-slate-100', color: 'text-slate-600', border: 'border-slate-200' };
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md relative">
              <Bell className="w-4 h-4 text-white" />
              {unreadCount > 0 && <span className="absolute -top-1 -right-1 w-3 h-3 bg-rose-500 rounded-full border-2 border-white animate-pulse" />}
            </div>
            Notifications Center
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Alerts for denials, human review, information requests, and recovery failures</p>
        </div>
        <Button
          onClick={markAllRead}
          className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 shadow-sm w-max"
        >
          <Check className="w-4 h-4 mr-2" /> Mark all as read
        </Button>
      </div>

      <Card className="overflow-hidden flex flex-col min-h-[500px]">
        {/* Toolbar */}
        <CardHeader className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row justify-between gap-4">
          <div className="flex overflow-x-auto no-scrollbar gap-1.5 p-1 bg-white border border-slate-200 rounded-xl">
            {['All', 'Unread', 'Denial', 'Review', 'More Info'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={clsx(
                  'px-4 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap',
                  activeTab === tab ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                )}
              >
                {tab}
                {tab === 'Unread' && unreadCount > 0 && (
                  <span className="ml-1.5 bg-rose-500 text-white px-1.5 py-0.5 rounded text-[9px]">{unreadCount}</span>
                )}
              </button>
            ))}
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search notifications..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 w-full"
            />
          </div>
        </CardHeader>

        {/* List */}
        <CardContent className="p-0 flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="flex gap-4 p-4 rounded-xl border border-slate-100 animate-pulse">
                  <div className="w-10 h-10 rounded-full bg-slate-200" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-slate-200 rounded w-1/4" />
                    <div className="h-3 bg-slate-100 rounded w-3/4" />
                  </div>
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-20 text-center">
              <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <Bell className="w-8 h-8 text-slate-300" />
              </div>
              <h3 className="text-sm font-bold text-slate-800 mb-1">All caught up!</h3>
              <p className="text-slate-500 font-medium text-xs">No notifications match your current filters.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {filtered.map(notif => {
                const config = getIconConfig(notif.type);
                const Icon = config.icon;
                return (
                  <div
                    key={notif.notification_id}
                    onClick={() => {
                      if (!notif.read) markAsRead(notif.notification_id);
                      if (notif.claim_id) navigate(`/hospital/claims/${notif.claim_id}`);
                    }}
                    className={clsx(
                      'p-5 flex gap-4 transition-colors cursor-pointer group',
                      notif.read ? 'bg-white hover:bg-slate-50/50' : 'bg-indigo-50/30 hover:bg-indigo-50'
                    )}
                  >
                    <div className={clsx('w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border shadow-sm', config.bg, config.border)}>
                      <Icon className={clsx('w-5 h-5', config.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1 gap-4">
                        <h3 className={clsx('text-sm truncate', notif.read ? 'font-semibold text-slate-700' : 'font-bold text-slate-900')}>
                          Update on {notif.claim_id}
                        </h3>
                        <span className="text-[10px] font-semibold text-slate-400 whitespace-nowrap pt-0.5">
                          {new Date(notif.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className={clsx('text-xs leading-relaxed', notif.read ? 'text-slate-500 font-medium' : 'text-slate-700 font-semibold')}>
                        {notif.message}
                      </p>
                      {notif.claim_id && (
                        <p className="text-xs font-bold text-indigo-600 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          View details →
                        </p>
                      )}
                    </div>
                    {!notif.read && (
                      <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
