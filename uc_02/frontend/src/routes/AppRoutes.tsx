import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { RoleSelect } from '../pages/RoleSelect';

// Hospital pages
import { HospitalDashboard }   from '../pages/hospital/HospitalDashboard';
import { CreateClaim }         from '../pages/hospital/CreateClaim';
import { ClaimsList }          from '../pages/hospital/ClaimsList';
import { HospitalClaimDetails }from '../pages/hospital/ClaimDetails';
import { Notifications }       from '../pages/hospital/Notifications';
import { Authorizations }      from '../pages/hospital/Authorizations';
import { Settings }            from '../pages/hospital/Settings';
import { HospitalReviewQueue } from '../pages/hospital/HospitalReviewQueue';

// Insurance pages
import { InsuranceDashboard }     from '../pages/insurance/InsuranceDashboard';
import { IncomingClaims }         from '../pages/insurance/IncomingClaims';
import { InsuranceClaimDetails }  from '../pages/insurance/InsuranceClaimDetails';
import { ReviewQueue }            from '../pages/insurance/ReviewQueue';
import { ReviewDetail }           from '../pages/insurance/ReviewDetail';
import { InsuranceNotifications } from '../pages/insurance/InsuranceNotifications';
import { InsuranceSettings }      from '../pages/insurance/InsuranceSettings';

import { HospitalLayout } from '../layouts/HospitalLayout';
import { InsuranceLayout } from '../layouts/InsuranceLayout';

function PageTitleUpdater() {
  const location = useLocation();
  
  useEffect(() => {
    const path = location.pathname;
    let title = 'AuthFlow';
    
    // Map paths to tab titles
    if (path.startsWith('/hospital')) {
      if (path.includes('dashboard')) title = 'Dashboard - Hospital Portal';
      else if (path.includes('patients')) title = 'Patients - Hospital Portal';
      else if (path.includes('providers')) title = 'Providers - Hospital Portal';
      else if (path.includes('claims/new')) title = 'New Claim - Hospital Portal';
      else if (path.includes('claims')) title = 'Claims - Hospital Portal';
      else if (path.includes('review')) title = 'Review Queue - Hospital Portal';
      else if (path.includes('settings')) title = 'Settings - Hospital Portal';
      else title = 'Hospital Portal - AuthFlow';
    } else if (path.startsWith('/insurance')) {
      if (path.includes('dashboard')) title = 'Dashboard - Insurance Portal';
      else if (path.includes('analytics')) title = 'Analytics - Insurance Portal';
      else if (path.includes('claims')) title = 'Claims - Insurance Portal';
      else if (path.includes('review')) title = 'Review Queue - Insurance Portal';
      else if (path.includes('providers')) title = 'Providers - Insurance Portal';
      else if (path.includes('members')) title = 'Members - Insurance Portal';
      else if (path.includes('fraud')) title = 'Fraud Detection - Insurance Portal';
      else if (path.includes('settings')) title = 'Settings - Insurance Portal';
      else title = 'Insurance Portal - AuthFlow';
    }
    
    document.title = title;
  }, [location.pathname]);
  
  return null;
}

export function AppRoutes() {
  return (
    <>
      <PageTitleUpdater />
      <Routes>
        {/* Role Select */}
        <Route path="/" element={<RoleSelect />} />

      {/* Hospital */}
      <Route element={<HospitalLayout />}>
        <Route path="/hospital/dashboard"        element={<HospitalDashboard />} />
        <Route path="/hospital/claims/new"       element={<CreateClaim />} />
        <Route path="/hospital/claims"           element={<ClaimsList />} />
        <Route path="/hospital/claims/:id"       element={<HospitalClaimDetails />} />
        <Route path="/hospital/review"           element={<HospitalReviewQueue />} />
        <Route path="/hospital/authorizations"   element={<Authorizations />} />
        <Route path="/hospital/notifications"    element={<Notifications />} />
        <Route path="/hospital/settings"         element={<Settings />} />
      </Route>

      {/* Insurance */}
      <Route element={<InsuranceLayout />}>
        <Route path="/insurance/dashboard"       element={<InsuranceDashboard />} />
        <Route path="/insurance/claims"          element={<IncomingClaims />} />
        <Route path="/insurance/claims/:id"      element={<InsuranceClaimDetails />} />
        <Route path="/insurance/review"          element={<ReviewQueue />} />
        <Route path="/insurance/review/:id"      element={<ReviewDetail />} />
        <Route path="/insurance/notifications"   element={<InsuranceNotifications />} />
        <Route path="/insurance/settings"        element={<InsuranceSettings />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  );
}
