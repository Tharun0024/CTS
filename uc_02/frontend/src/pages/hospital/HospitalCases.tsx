import { mockCases } from '../../mock/cases';
import { StatusBadge } from '../../components/common/StatusBadge';
import { useNavigate } from 'react-router-dom';
import type { ClaimStatus } from '../../types/claim';

export function HospitalCases() {
  const navigate = useNavigate();

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <main className="flex-1 p-8 overflow-auto">
        <div className="flex items-center justify-between mb-8">
            <h1 className="text-2xl font-bold text-slate-900">Active Requests</h1>
            <div className="flex gap-2">
              <select className="border border-slate-300 rounded-lg px-3 py-2 bg-white text-sm outline-none focus:border-brand-500">
                <option>All Statuses</option>
                <option>Approved</option>
                <option>Rejected</option>
                <option>Processing</option>
              </select>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Case ID</th>
                  <th className="px-6 py-3">Patient</th>
                  <th className="px-6 py-3">Procedure</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {mockCases.map(c => (
                  <tr key={c.authorization_id} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/hospital/cases/${c.authorization_id}`)}>
                    <td className="px-6 py-4 font-medium text-slate-900">{c.authorization_id}</td>
                    <td className="px-6 py-4 text-slate-600">{c.patient.patient_id}</td>
                    <td className="px-6 py-4 text-slate-600">{c.request.procedure}</td>
                    <td className="px-6 py-4"><StatusBadge status={(c.status as any) as ClaimStatus} /></td>
                    <td className="px-6 py-4 text-slate-500">{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
    </div>
  );
}
