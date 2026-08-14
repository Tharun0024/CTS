import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FilePlus2, List, Bell, Menu, X,
  ShieldCheck, ClipboardList, Users, ChevronRight,
} from 'lucide-react';
import { clsx } from 'clsx';

interface SidebarProps {
  portal: 'hospital' | 'insurance';
}

const hospitalLinks = [
  { name: 'Dashboard',     path: '/hospital/dashboard',     icon: LayoutDashboard, desc: 'Overview & metrics' },
  { name: 'New Claim',     path: '/hospital/claims/new',    icon: FilePlus2,        desc: 'Submit a claim' },
  { name: 'All Claims',    path: '/hospital/claims',        icon: List,             desc: 'Manage claims' },
  { name: 'Notifications', path: '/hospital/notifications', icon: Bell,             desc: 'Alerts & updates' },
];

const insuranceLinks = [
  { name: 'Dashboard',      path: '/insurance/dashboard',     icon: LayoutDashboard, desc: 'Overview & metrics' },
  { name: 'Incoming Claims',path: '/insurance/claims',        icon: ClipboardList,   desc: 'Review queue' },
  { name: 'Review Queue',   path: '/insurance/review',        icon: Users,           desc: 'Assigned to you' },
  { name: 'Notifications',  path: '/insurance/notifications', icon: Bell,            desc: 'Alerts & updates' },
];

export function Sidebar({ portal }: SidebarProps) {
  const navigate   = useNavigate();
  const location   = useLocation();
  const [open, setOpen] = useState(false);

  const isHospital    = portal === 'hospital';
  const links         = isHospital ? hospitalLinks : insuranceLinks;
  const accent        = isHospital ? '#059669' : '#4f46e5';
  const accentText    = isHospital ? 'text-emerald-700'       : 'text-indigo-700';
  const accentBg      = isHospital ? 'bg-emerald-50'          : 'bg-indigo-50';
  const accentBorder  = isHospital ? 'border-emerald-200'     : 'border-indigo-200';
  const logoGrad      = isHospital
    ? 'from-emerald-500 to-teal-600'
    : 'from-indigo-500 to-violet-600';
  const portalLabel   = isHospital ? '🏥 Hospital Workspace'  : '🛡 Insurance Workspace';

  const NavContent = () => (
    <div className="flex flex-col h-full"
      style={{
        background: 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        borderRight: '1px solid rgba(15,23,42,0.07)',
      }}
    >
      {/* Logo */}
      <button
        className="h-16 flex items-center gap-3 px-5 border-b border-slate-100/80 flex-shrink-0 hover:bg-slate-50/80 transition-colors w-full text-left"
        onClick={() => { navigate('/'); setOpen(false); }}
      >
        <div className={clsx('w-9 h-9 rounded-xl bg-gradient-to-br flex items-center justify-center shadow-md flex-shrink-0', logoGrad)}>
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="font-black text-[15px] text-slate-900 leading-none tracking-tight">ORCA</p>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 leading-none mt-1">{portal} portal</p>
        </div>
      </button>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest px-2 mb-3">Navigation</p>
        {links.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          const Icon = item.icon;
          
          return (
            <button
              key={item.path}
              onClick={() => { navigate(item.path); setOpen(false); }}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all group border',
                isActive
                  ? `${accentBg} ${accentText} ${accentBorder} shadow-sm`
                  : 'border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-700'
              )}
              style={isActive ? { borderLeftWidth: '3px', borderLeftColor: accent } : {}}
            >
              <Icon className={clsx('w-4 h-4 flex-shrink-0 transition-colors', isActive ? accentText : 'text-slate-400 group-hover:text-slate-600')} />
              <div className="flex-1 min-w-0">
                <p className={clsx('text-[13px] font-bold leading-none', isActive ? accentText : 'text-slate-700 group-hover:text-slate-900')}>{item.name}</p>
                <p className="text-[10px] text-slate-400 font-medium mt-0.5">{item.desc}</p>
              </div>
              {isActive && <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" style={{ color: accent }} />}
            </button>
          );
        })}
      </nav>

      {/* Bottom badge */}
      <div className="p-4 border-t border-slate-100 flex-shrink-0">
        <div className={clsx('text-[11px] font-bold px-3 py-2.5 rounded-xl text-center uppercase tracking-wider border', accentBg, accentText, accentBorder)}>
          {portalLabel}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-40 p-2 bg-white rounded-xl border border-slate-200 shadow-md"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5 text-slate-600" />
      </button>

      {open && (
        <div className="lg:hidden fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-40" onClick={() => setOpen(false)} />
      )}

      <div className={clsx(
        'lg:hidden fixed inset-y-0 left-0 z-50 w-72 shadow-2xl transition-transform duration-300',
        open ? 'translate-x-0' : '-translate-x-full'
      )}>
        <button onClick={() => setOpen(false)} className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 z-10">
          <X className="w-4 h-4" />
        </button>
        <NavContent />
      </div>

      <aside className="hidden lg:flex flex-col w-72 min-h-screen flex-shrink-0 z-20">
        <NavContent />
      </aside>
    </>
  );
}
