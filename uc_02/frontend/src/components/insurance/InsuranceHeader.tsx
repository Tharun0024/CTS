import { Search, Bell, Menu, ChevronDown, LogOut, Settings, Home } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface InsuranceHeaderProps {
  setIsMobileOpen: (open: boolean) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

function getBreadcrumb(pathname: string): string {
  const map: Record<string, string> = {
    '/insurance/dashboard': 'Dashboard',
    '/insurance/claims': 'Claims Processing',
    '/insurance/policies': 'Policies',
    '/insurance/reports': 'Reports',
    '/insurance/settings': 'Settings',
  };
  if (pathname.startsWith('/insurance/claims/')) {
    return 'Claim Details';
  }
  return map[pathname] ?? 'Insurance';
}

export function InsuranceHeader({ setIsMobileOpen, isCollapsed, setIsCollapsed }: InsuranceHeaderProps) {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [notifCount] = useState(5);
  const [searchVal, setSearchVal] = useState('');
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const breadcrumb = getBreadcrumb(location.pathname);

  useEffect(() => {
    const storedUser = localStorage.getItem('orca_logged_user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getInitials = (name: string) => {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const handleSearch = () => {
    if (!searchVal.trim()) return;
    let cleanVal = searchVal.trim().toUpperCase();
    if (/^\d+$/.test(cleanVal)) {
      cleanVal = `CLM-${cleanVal.padStart(3, '0')}`;
    } else if (/^CLM\d+$/.test(cleanVal)) {
      cleanVal = `CLM-${cleanVal.slice(3)}`;
    }
    navigate(`/insurance/claims/${cleanVal}`);
    setSearchVal('');
  };

  return (
    <header
      className="h-16 flex items-center justify-between px-4 sticky top-0 z-10 border-b"
      style={{
        background: 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(20px) saturate(180%)',
        borderColor: 'rgba(226,232,240,0.8)',
        boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
      }}
    >
      <div className="flex items-center gap-3 flex-1">
        <button
          onClick={() => setIsMobileOpen(true)}
          className="lg:hidden p-2 rounded-xl text-slate-500 hover:bg-slate-100 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="hidden lg:flex p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => navigate('/insurance/dashboard')}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <Home className="w-3.5 h-3.5" />
          </button>
          <span className="text-slate-300">/</span>
          <span className="font-bold text-slate-700">{breadcrumb}</span>
        </div>

        <div className="hidden md:flex relative w-full max-w-xs ml-4">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSearch();
              }
            }}
            className="block w-full pl-9 pr-3 py-1.5 border border-slate-200 rounded-xl leading-5 bg-slate-50 placeholder-slate-400 focus:outline-none focus:bg-white focus:ring-1 focus:ring-indigo-400 focus:border-indigo-400 text-sm transition-all"
            placeholder="Search"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">

        <button
          onClick={() => navigate('/insurance/notifications')}
          className="relative p-2 rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
        >
          <Bell className="w-5 h-5" />
          {notifCount > 0 && (
            <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-rose-500 text-white text-[9px] font-black flex items-center justify-center ring-2 ring-white">
              {notifCount}
            </span>
          )}
        </button>

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-slate-100 transition-colors border border-transparent hover:border-slate-200"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-xs shadow-sm">
              {user ? getInitials(user.name) : 'AR'}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-[12px] font-bold text-slate-700 leading-none">{user ? user.name : 'A. Reynolds'}</p>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 hidden sm:block transition-transform ${showProfileMenu ? 'rotate-180' : ''}`} />
          </button>

          {showProfileMenu && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl shadow-xl border border-slate-100 py-1 z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-50 bg-gradient-to-r from-indigo-50 to-purple-50">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-sm">
                    {user ? getInitials(user.name) : 'AR'}
                  </div>
                  <div>
                    <p className="text-[13px] font-bold text-slate-900">{user ? user.name : 'Alex Reynolds'}</p>
                    <p className="text-[11px] text-indigo-600 font-medium">{user ? user.email : 'alex.r@aetna.com'}</p>
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/insurance/settings');
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors text-left"
              >
                <Settings className="w-4 h-4 text-slate-400" />
                Settings
              </button>
              <button
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/');
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors text-left border-t border-slate-50"
              >
                <LogOut className="w-4 h-4 text-red-400" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
