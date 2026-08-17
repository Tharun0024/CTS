import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { getNotifications, markAsRead, markAllRead } from '../../services/notificationsApi';
import type { Notification } from '../../types/claim';
import { Bell, CheckCheck } from 'lucide-react';
import { clsx } from 'clsx';

const TYPE_STYLES: Record<string, string> = {
  DECISION:         'bg-rose-50 border-rose-200',
  PROVIDER_DECLINE: 'bg-rose-50 border-rose-200',
  RECOVERY_FAILED:  'bg-rose-50 border-rose-200',
  HUMAN_REVIEW:     'bg-brand-50 border-brand-200',
  MORE_INFO:        'bg-amber-50 border-amber-200',
  STATUS_CHANGE:    'bg-slate-50 border-slate-200',
  RESUBMISSION:     'bg-purple-50 border-purple-200',
};
const TYPE_DOT: Record<string, string> = {
  DECISION:         'bg-rose-500',
  PROVIDER_DECLINE: 'bg-rose-500',
  RECOVERY_FAILED:  'bg-rose-500',
  HUMAN_REVIEW:     'bg-brand-500',
  MORE_INFO:        'bg-amber-500',
  STATUS_CHANGE:    'bg-slate-400',
  RESUBMISSION:     'bg-purple-500',
};

export function InsuranceNotifications() {
  const navigate = useNavigate();
  const [notifs, setNotifs]   = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const fetchData = () => {
    setLoading(true); setError('');
    getNotifications()
      .then(setNotifs)
      .catch(() => setError('Failed to load notifications.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleRead = async (id: string) => {
    await markAsRead(id);
    setNotifs(prev => prev.map(n => n.notification_id === id ? { ...n, read: true } : n));
  };

  const handleMarkAll = async () => {
    await markAllRead();
    setNotifs(prev => prev.map(n => ({ ...n, read: true })));
  };

  const unread = notifs.filter(n => !n.read).length;

  return (
    <div className="max-w-2xl mx-auto w-full pb-10">
      <div className="flex items-center justify-between mb-4 animate-fade-in-up">
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-slate-900">Notifications</h1>
              {unread > 0 && <p className="text-[11px] text-slate-500 mt-0.5">{unread} unread notifications</p>}
            </div>
            {unread > 0 && (
              <button
                onClick={handleMarkAll}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>

          {loading ? <LoadingState message="Loading notifications…" /> :
           error   ? <ErrorState message={error} onRetry={fetchData} /> :
           notifs.length === 0 ? (
            <div className="text-center py-12 animate-fade-in-up">
              <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No notifications yet.</p>
            </div>
           ) : (
            <div className="space-y-1.5">
              {notifs.map((n, index) => (
                <div
                  key={n.notification_id}
                  className={clsx(
                    'flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover-card-trigger transition-all duration-150 shadow-sm',
                    n.read ? 'bg-white border-slate-200 opacity-70' : (TYPE_STYLES[n.type] ?? 'bg-white border-slate-200'),
                    `stagger-${(index % 5) + 1}`
                  )}
                  onClick={() => {
                    handleRead(n.notification_id);
                    navigate(`/insurance/claims/${n.claim_id}`);
                  }}
                >
                  <span className={clsx('w-2 h-2 rounded-full flex-shrink-0 mt-1', TYPE_DOT[n.type] ?? 'bg-slate-400', n.read && 'opacity-30')} />
                  <div className="flex-1 min-w-0">
                    <p className={clsx('text-xs md:text-[13px] leading-snug', n.read ? 'text-slate-500' : 'text-slate-850 font-semibold')}>{n.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-slate-400 font-medium">
                        {new Date(n.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span className="text-[10px] text-brand-600 font-semibold">{n.claim_id}</span>
                    </div>
                  </div>
                  {!n.read && (
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-brand-500 mt-1.5" />
                  )}
                </div>
              ))}
            </div>
          )}
    </div>
  );
}
