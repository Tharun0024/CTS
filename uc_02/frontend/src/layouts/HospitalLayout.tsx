import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { HospitalSidebar } from '../components/hospital/HospitalSidebar';
import { HospitalHeader } from '../components/hospital/HospitalHeader';

export function HospitalLayout() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen" style={{ background: 'linear-gradient(135deg, #f0fdf4 0%, #f8fafc 40%, #eff6ff 100%)' }}>
      <HospitalSidebar 
        isMobileOpen={isMobileOpen} 
        setIsMobileOpen={setIsMobileOpen} 
        isCollapsed={isCollapsed} 
      />
      
      <div className="flex-1 flex flex-col min-w-0 transition-all duration-300 relative">
        <HospitalHeader 
          setIsMobileOpen={setIsMobileOpen} 
          isCollapsed={isCollapsed}
          setIsCollapsed={setIsCollapsed}
        />
        
        <main className="flex-1 p-6 overflow-x-hidden overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
