import { mockHospitalDashboard, mockInsuranceDashboard } from './dashboard';
// Need to combine this into a single mockDashboard object to fix import above
export const mockDashboard = {
  hospital: mockHospitalDashboard,
  insurance: mockInsuranceDashboard
};
