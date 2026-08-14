import { mockCases } from '../../mock/cases';
import { StatusBadge } from '../../components/common/StatusBadge';
import { FileText, Clock, User, Shield, Stethoscope } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import type { ClaimStatus } from '../../types/claim';

export function HospitalCaseDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  // In a real app we'd fetch this. We'll use the first mock case or find by ID
  const caseData = mockCases.find(c => c.authorization_id === id) || mockCases[0];

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <main className="flex-1 p-8 overflow-auto">
        {/* Header */}
        <div className="mb-8">
            <button onClick={() => navigate(-1)} className="text-sm font-medium text-slate-500 hover:text-slate-700 mb-4">&larr; Back to Active Requests</button>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{caseData.authorization_id}</h1>
                <p className="text-slate-500 mt-1">{caseData.request.procedure}</p>
              </div>
              <StatusBadge status={(caseData.status as any) as ClaimStatus} className="text-sm px-4 py-1.5" />
            </div>
            <p className="text-sm text-slate-400 mt-2">Created: {new Date(caseData.created_at).toLocaleString()}</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              
              {/* Patient & Insurance */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <User className="w-5 h-5 text-slate-400" />
                    <h2 className="font-semibold text-slate-800">Patient Details</h2>
                  </div>
                  <dl className="space-y-3 text-sm">
                    <div className="flex justify-between"><dt className="text-slate-500">ID:</dt> <dd className="font-medium text-slate-900">{caseData.patient.patient_id}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-500">Age:</dt> <dd className="font-medium text-slate-900">{caseData.patient.age}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-500">Gender:</dt> <dd className="font-medium text-slate-900">{caseData.patient.gender}</dd></div>
                  </dl>
                </div>

                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Shield className="w-5 h-5 text-slate-400" />
                    <h2 className="font-semibold text-slate-800">Insurance Details</h2>
                  </div>
                  <dl className="space-y-3 text-sm">
                    <div className="flex justify-between"><dt className="text-slate-500">Provider:</dt> <dd className="font-medium text-slate-900">{caseData.insurance.provider}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-500">Member ID:</dt> <dd className="font-medium text-slate-900">{caseData.insurance.member_id}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-500">Plan:</dt> <dd className="font-medium text-slate-900">{caseData.insurance.plan}</dd></div>
                  </dl>
                </div>
              </div>

              {/* Authorization Request */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Stethoscope className="w-5 h-5 text-slate-400" />
                  <h2 className="font-semibold text-slate-800">Authorization Request</h2>
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-slate-500 font-medium mb-1">Diagnosis</p>
                    <p className="text-slate-900 text-sm">{caseData.request.diagnosis}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-medium mb-1">Procedure</p>
                    <p className="text-slate-900 text-sm">{caseData.request.procedure}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-medium mb-1">Reason</p>
                    <p className="text-slate-900 text-sm">{caseData.request.reason}</p>
                  </div>
                  {caseData.request.previous_treatment && (
                    <div>
                      <p className="text-xs text-slate-500 font-medium mb-1">Previous Treatment</p>
                      <p className="text-slate-900 text-sm">{caseData.request.previous_treatment}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Documents */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-slate-400" />
                  <h2 className="font-semibold text-slate-800">Documents</h2>
                </div>
                {caseData.documents.length === 0 ? (
                  <p className="text-sm text-slate-500 italic">No documents uploaded.</p>
                ) : (
                  <ul className="space-y-2">
                    {caseData.documents.map(doc => (
                      <li key={doc.document_id} className="flex items-center justify-between p-3 border border-slate-100 rounded-lg bg-slate-50 text-sm">
                        <span className="font-medium text-slate-700">{doc.file_name}</span>
                        <a href="#" className="text-brand-600 hover:underline">View</a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Sidebar Timeline */}
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-100 pb-4">
                  <Clock className="w-5 h-5 text-slate-400" />
                  <h2 className="font-semibold text-slate-800">Processing Timeline</h2>
                </div>
                
                <div className="relative border-l-2 border-slate-200 ml-3 mt-4 space-y-6">
                  {/* Mock Timeline steps */}
                  <div className="relative pl-6">
                    <div className="absolute w-3 h-3 bg-brand-500 rounded-full -left-[7px] top-1.5 ring-4 ring-white"></div>
                    <p className="text-sm font-medium text-slate-900">Request Received</p>
                    <p className="text-xs text-slate-500 mt-1">10:30 AM</p>
                  </div>
                  <div className="relative pl-6">
                    <div className="absolute w-3 h-3 bg-brand-500 rounded-full -left-[7px] top-1.5 ring-4 ring-white"></div>
                    <p className="text-sm font-medium text-slate-900">Documents Stored</p>
                    <p className="text-xs text-slate-500 mt-1">10:30 AM</p>
                  </div>
                  <div className="relative pl-6">
                    <div className="absolute w-3 h-3 bg-brand-500 rounded-full -left-[7px] top-1.5 ring-4 ring-white"></div>
                    <p className="text-sm font-medium text-slate-900">Data Extracted</p>
                    <p className="text-xs text-slate-500 mt-1">10:31 AM</p>
                  </div>
                  <div className="relative pl-6">
                    <div className="absolute w-3 h-3 bg-brand-500 rounded-full -left-[7px] top-1.5 ring-4 ring-white"></div>
                    <p className="text-sm font-medium text-slate-900">Policy Analysis</p>
                    <p className="text-xs text-slate-500 mt-1">10:32 AM</p>
                  </div>
                  <div className="relative pl-6">
                    <div className="absolute w-3 h-3 border-2 border-brand-500 bg-white rounded-full -left-[7px] top-1.5 ring-4 ring-white"></div>
                    <p className="text-sm font-medium text-slate-900">Final Result</p>
                    <p className="text-xs text-brand-600 mt-1 font-medium">{caseData.status}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
    </div>
  );
}
