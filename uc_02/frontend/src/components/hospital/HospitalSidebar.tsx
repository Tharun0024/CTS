
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FilePlus2, List,
  ShieldCheck,
  Bell, Settings,
  X, Activity, ChevronRight
} from 'lucide-react';
import { clsx } from 'clsx';

interface HospitalSidebarProps {
  isMobileOpen: boolean;
  setIsMobileOpen: (open: boolean) => void;
  isCollapsed: boolean;
}

const navGroups = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', path: '/hospital/dashboard', icon: LayoutDashboard },
    ]
  },
  {
    title: 'Claims',
    items: [
      { name: 'New Claim', path: '/hospital/claims/new', icon: FilePlus2 },
      { name: 'All Claims', path: '/hospital/claims', icon: List },
    ]
  },
  {
    title: 'Care Operations',
    items: [
      { name: 'Authorizations', path: '/hospital/authorizations', icon: ShieldCheck },
    ]
  },
  {
    title: 'System',
    items: [
      { name: 'Alerts', path: '/hospital/notifications', icon: Bell },
      { name: 'Settings', path: '/hospital/settings', icon: Settings },
    ]
  }
];

export function HospitalSidebar({ isMobileOpen, setIsMobileOpen, isCollapsed }: HospitalSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNav = (path: string) => {
    navigate(path);
    setIsMobileOpen(false);
  };

  const isActive = (path: string) => {
    if (path === '/hospital/claims' && location.pathname === '/hospital/claims') return true;
    if (path === '/hospital/claims/new' && location.pathname === '/hospital/claims/new') return true;
    if (path !== '/hospital/dashboard' && path !== '/hospital/claims' && path !== '/hospital/claims/new') {
      return location.pathname.startsWith(path);
    }
    return location.pathname === path;
  };

  const NavContent = () => (
    <div className="flex flex-col h-full" style={{ background: 'linear-gradient(180deg, #0f1629 0%, #0d1424 50%, #0a1020 100%)' }}>
      {/* Logo Area */}
      <div
        className="h-16 flex items-center px-4 flex-shrink-0 cursor-pointer relative overflow-hidden border-b border-white/5"
        onClick={() => handleNav('/')}
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 50%, #047857 100%)' }}
      >
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 70% 50%, rgba(167,243,208,0.4) 0%, transparent 60%)' }} />
        <div className="w-9 h-9 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center flex-shrink-0 border border-white/20 shadow-lg relative z-10">
          <Activity className="w-5 h-5 text-emerald-300" />
        </div>
        {!isCollapsed && (
          <div className="ml-3 overflow-hidden whitespace-nowrap relative z-10">
            <h1 className="font-black text-[16px] text-white leading-none tracking-tight">AuthFlow</h1>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-300/80 leading-none mt-1">Hospital Portal</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 no-scrollbar">
        {navGroups.map((group) => (
          <div key={group.title} className={clsx('mb-5', isCollapsed ? 'px-2' : 'px-3')}>
            {!isCollapsed && (
              <h3 className="text-[9px] font-black text-white/25 uppercase tracking-widest mb-2 px-3">
                {group.title}
              </h3>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = isActive(item.path);
                const Icon = item.icon;

                return (
                  <button
                    key={item.name}
                    onClick={() => handleNav(item.path)}
                    title={isCollapsed ? item.name : undefined}
                    className={clsx(
                      'w-full flex items-center rounded-xl transition-all duration-200 group relative',
                      isCollapsed ? 'justify-center p-2.5' : 'px-3 py-2.5 gap-3',
                      active
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'text-white/40 hover:text-white/80 hover:bg-white/5'
                    )}
                  >
                    {active && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-emerald-400 rounded-r-full shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
                    )}

                    <div className={clsx(
                      'flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all',
                      active
                        ? 'bg-emerald-500/20 shadow-[0_0_12px_rgba(52,211,153,0.2)]'
                        : 'bg-white/5 group-hover:bg-white/10'
                    )}>
                      <Icon className={clsx(
                        'transition-colors',
                        isCollapsed ? 'w-4 h-4' : 'w-3.5 h-3.5',
                        active ? 'text-emerald-400' : 'text-white/40 group-hover:text-white/70'
                      )} />
                    </div>

                    {!isCollapsed && (
                      <>
                        <span className="text-[13px] font-semibold whitespace-nowrap overflow-hidden text-ellipsis flex-1 text-left">
                          {item.name}
                        </span>
                        {active && <ChevronRight className="w-3 h-3 text-emerald-400/60 flex-shrink-0" />}
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      {!isCollapsed && (
        <div className="px-3 py-4 border-t border-white/5 flex-shrink-0">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/5 border border-white/5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-black text-xs flex-shrink-0">
              SJ
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[12px] font-bold text-white/80 truncate">Dr. S. Jenkins</p>
              <p className="text-[10px] text-white/30 truncate">City General Hospital</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Mobile Drawer */}
      <div className={clsx(
        'lg:hidden fixed inset-y-0 left-0 z-50 w-72 shadow-2xl transition-transform duration-300 ease-in-out',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <button
          onClick={() => setIsMobileOpen(false)}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 z-50 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
        <NavContent />
      </div>

      {/* Desktop Sidebar */}
      <aside className={clsx(
        'hidden lg:block h-screen sticky top-0 z-20 transition-all duration-300 flex-shrink-0',
        isCollapsed ? 'w-16' : 'w-64'
      )}>
        <NavContent />
      </aside>
    </>
  );
}
