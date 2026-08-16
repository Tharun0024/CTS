import { useNavigate } from 'react-router-dom';
import { Search, Bell, User, ChevronDown } from 'lucide-react';
import { useState, useEffect } from 'react';
import { getNotifications } from '../../services/notificationsApi';
import { clsx } from 'clsx';

interface HeaderProps {
  portal: 'hospital' | 'insurance';
  title?: string;
}

export function Header({ portal, title }: HeaderProps) {
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    getNotifications().then(n => setUnread(n.filter(x => !x.read).length));
  }, []);

  const isHospital = portal === 'hospital';
  const notifPath = isHospital ? '/hospital/notifications' : '/insurance/notifications';
  const userName = isHospital ? 'Dr. Sarah Jenkins' : 'Alex Rivera';
  const userSub = isHospital ? 'City General Hospital' : 'HealthShield Inc.';
  const avatarGrad = isHospital ? 'from-emerald-500 to-teal-600' : 'from-indigo-500 to-violet-600';
  const bellHover = isHospital ? 'hover:bg-emerald-50 hover:text-emerald-700' : 'hover:bg-indigo-50 hover:text-indigo-700';
  const badgeBg = isHospital ? 'bg-emerald-600' : 'bg-indigo-600';
  const searchFocus = isHospital
    ? 'focus:border-emerald-400 focus:ring-emerald-100'
    : 'focus:border-indigo-400 focus:ring-indigo-100';

  return (
    <header
      className="h-16 flex items-center justify-between px-5 lg:px-7 sticky top-0 z-20 flex-shrink-0"
      style={{
        background: 'rgba(255,255,255,0.82)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        borderBottom: '1px solid rgba(15,23,42,0.07)',
        boxShadow: '0 1px 3px rgba(15,23,42,0.04)',
      }}
    >
      {/* Left */}
      <div className="flex items-center gap-4">
        <div className="w-7 lg:hidden" />
        {title && <h1 className="hidden lg:block text-sm font-extrabold text-slate-800 tracking-tight">{title}</h1>}

        <div className="hidden lg:flex items-center relative group">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 z-10 pointer-events-none group-focus-within:text-slate-600 transition-colors" />
          <input
            type="text"
            placeholder="Search"
            className={clsx(
              'w-80 pl-10 pr-4 py-2 bg-slate-50/80 border border-slate-200 rounded-xl text-[13px] font-medium text-slate-700 placeholder:text-slate-400 transition-all shadow-sm focus:ring-2 outline-none',
              searchFocus
            )}
            style={{ backdropFilter: 'none' }}
          />
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        {/* Notification bell */}
        <button
          onClick={() => navigate(notifPath)}
          className={clsx('relative p-2.5 rounded-xl border border-transparent text-slate-500 transition-all', bellHover)}
          aria-label="Notifications"
        >
          <Bell className="w-[18px] h-[18px]" />
          {unread > 0 && (
            <span className={clsx('absolute top-1.5 right-1.5 w-4 h-4 rounded-full text-[9px] font-black text-white flex items-center justify-center border-2 border-white leading-none', badgeBg)}>
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </button>

        <div className="w-px h-6 bg-slate-200 mx-1" />

        {/* User pill */}
        <button className="flex items-center gap-2.5 py-1.5 pl-1.5 pr-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50 transition-all group">
          <div className={clsx('w-8 h-8 rounded-lg bg-gradient-to-br flex items-center justify-center flex-shrink-0 shadow-sm', avatarGrad)}>
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="hidden md:block text-left">
            <p className="text-[12px] font-bold text-slate-800 leading-none">{userName}</p>
            <p className="text-[10px] font-medium text-slate-400 leading-none mt-0.5">{userSub}</p>
          </div>
          <ChevronDown className="hidden md:block w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>
    </header>
  );
}
