import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { InsuranceSidebar } from '../components/insurance/InsuranceSidebar';
import { InsuranceHeader } from '../components/insurance/InsuranceHeader';

export function InsuranceLayout() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen" style={{ background: 'linear-gradient(135deg, #f5f3ff 0%, #faf5ff 40%, #f0f9ff 100%)' }}>
      <InsuranceSidebar 
        isMobileOpen={isMobileOpen} 
        setIsMobileOpen={setIsMobileOpen} 
        isCollapsed={isCollapsed} 
      />
      
      <div className="flex-1 flex flex-col min-w-0">
        <InsuranceHeader 
          setIsMobileOpen={setIsMobileOpen}
          isCollapsed={isCollapsed}
          setIsCollapsed={setIsCollapsed}
        />
        <main className="flex-1 overflow-x-hidden overflow-y-auto">
          <div className="container mx-auto px-4 py-8 max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
