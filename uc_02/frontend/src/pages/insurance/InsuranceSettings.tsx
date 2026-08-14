import { useState } from 'react';
import { Settings as SettingsIcon, User, Bell, Shield, Building, Save, CheckCircle2, ChevronRight, Smartphone } from 'lucide-react';
import { clsx } from 'clsx';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';


export function InsuranceSettings() {
  const [activeTab, setActiveTab] = useState('profile');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const tabs = [
    { id: 'profile', name: 'My Profile', icon: User, desc: 'Personal info & avatar' },
    { id: 'hospital', name: 'Insurance Company Details', icon: Building, desc: 'Org info & NPI' },
    { id: 'notifications', name: 'Notifications', icon: Bell, desc: 'Alert preferences' },
    { id: 'security', name: 'Security & Access', icon: Shield, desc: 'Passwords & 2FA' },
  ];

  const LABEL = 'block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2';
  const FIELD_INPUT = 'w-full bg-slate-50 border border-slate-200 focus:bg-white focus:border-emerald-500 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none';

  return (
    <div className="max-w-6xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center shadow-md">
            <SettingsIcon className="w-4 h-4 text-white" />
          </div>
          Settings & Preferences
        </h1>
        <p className="text-sm text-slate-500 font-medium mt-1">Manage your account, insurance company, and security settings</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Tabs */}
        <div className="w-full lg:w-72 flex-shrink-0 space-y-2">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "w-full flex items-center gap-4 p-4 rounded-2xl transition-all border group text-left",
                  isActive
                    ? "bg-slate-900 border-slate-900 shadow-xl"
                    : "bg-white border-slate-200 hover:border-slate-300 hover:bg-white shadow-sm"
                )}
              >
                <div className={clsx(
                  "w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors",
                  isActive ? "bg-white/10" : "bg-slate-100 group-hover:bg-slate-200"
                )}>
                  <Icon className={clsx("w-5 h-5", isActive ? "text-white" : "text-slate-500")} />
                </div>
                <div className="flex-1">
                  <h3 className={clsx("font-semibold text-sm", isActive ? "text-white" : "text-slate-900")}>{tab.name}</h3>
                  <p className={clsx("text-xs font-medium mt-0.5", isActive ? "text-slate-400" : "text-slate-500")}>{tab.desc}</p>
                </div>
                <ChevronRight className={clsx("w-4 h-4", isActive ? "text-slate-600" : "text-slate-300 group-hover:text-slate-400")} />
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <Card className="flex-1 overflow-hidden flex flex-col">
          <CardContent className="p-6 sm:p-8 flex-1">
            {activeTab === 'profile' && (
              <div className="space-y-8 animate-fade-in-up">
                <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Profile Information</h2>
                <div className="flex items-center gap-6 p-6 bg-slate-50/50 rounded-2xl border border-slate-100">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-3xl font-bold shadow-lg shadow-emerald-200">
                    SJ
                  </div>
                  <div>
                    <button className="px-5 py-2.5 bg-white border border-slate-200 hover:border-slate-300 rounded-xl text-sm font-semibold text-slate-700 shadow-sm transition-all active:scale-95">
                      Upload Avatar
                    </button>
                    <p className="text-xs text-slate-500 mt-2 font-medium">JPG, GIF or PNG. Max size 2MB</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <label className={LABEL}>First Name</label>
                    <input type="text" defaultValue="Sarah" className={FIELD_INPUT} />
                  </div>
                  <div>
                    <label className={LABEL}>Last Name</label>
                    <input type="text" defaultValue="Jenkins" className={FIELD_INPUT} />
                  </div>
                  <div className="sm:col-span-2">
                    <label className={LABEL}>Email Address</label>
                    <input type="email" defaultValue="sarah.j@citygeneral.com" className={FIELD_INPUT} />
                  </div>
                  <div className="sm:col-span-2">
                    <label className={LABEL}>Job Title / Role</label>
                    <input type="text" defaultValue="Chief Medical Officer" className={FIELD_INPUT} />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'hospital' && (
              <div className="space-y-8 animate-fade-in-up">
                <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Insurance Company Details</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="sm:col-span-2">
                    <label className={LABEL}>Hospital Name</label>
                    <input type="text" defaultValue="Aetna Insurance" className={FIELD_INPUT} />
                  </div>
                  <div>
                    <label className={LABEL}>Tax ID / EIN</label>
                    <input type="text" defaultValue="12-3456789" className={`${FIELD_INPUT} font-mono`} />
                  </div>
                  <div>
                    <label className={LABEL}>NPI Number (Organization)</label>
                    <input type="text" defaultValue="1987654321" className={`${FIELD_INPUT} font-mono`} />
                  </div>
                  <div className="sm:col-span-2">
                    <label className={LABEL}>Address</label>
                    <input type="text" defaultValue="100 Medical Plaza, Chicago, IL 60601" className={FIELD_INPUT} />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-8 animate-fade-in-up">
                <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Notification Preferences</h2>
                <div className="space-y-4">
                  {[
                    { title: 'Claim Approvals', desc: 'Notify me when a prior authorization is approved' },
                    { title: 'Claim Denials', desc: 'Notify me immediately upon rejection or appeal request' },
                    { title: 'Information Requests', desc: 'Alert me when insurers request additional documents' },
                    { title: 'Payment Reconciliations', desc: 'Weekly summary of paid and outstanding claims' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-start justify-between p-5 bg-white border border-slate-200 hover:border-slate-300 rounded-2xl transition-colors shadow-sm">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
                        <p className="text-xs text-slate-500 mt-1 font-medium">{item.desc}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer mt-1">
                        <input type="checkbox" defaultChecked={i !== 3} className="sr-only peer" />
                        <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-8 animate-fade-in-up">
                <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Security & Access</h2>
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-r from-slate-50 to-white border border-slate-200 rounded-2xl">
                    <div className="flex items-center gap-3 mb-2">
                      <Smartphone className="w-5 h-5 text-indigo-500" />
                      <h3 className="text-sm font-semibold text-slate-900">Two-Factor Authentication (2FA)</h3>
                    </div>
                    <p className="text-xs text-slate-500 mb-4 font-medium max-w-md">Add an extra layer of security to your account. We'll ask for a code from your mobile device every time you log in.</p>
                    <button className="px-5 py-2.5 bg-indigo-50 text-indigo-700 border border-indigo-200 hover:border-indigo-300 rounded-xl text-sm font-semibold transition-colors">
                      Set up 2FA
                    </button>
                  </div>
                  
                  <div className="p-6 bg-white border border-slate-200 rounded-2xl">
                    <h3 className="text-sm font-semibold text-slate-900 mb-4">Change Password</h3>
                    <div className="space-y-4 max-w-md">
                      <input type="password" placeholder="Current Password" className={FIELD_INPUT} />
                      <input type="password" placeholder="New Password" className={FIELD_INPUT} />
                      <input type="password" placeholder="Confirm New Password" className={FIELD_INPUT} />
                      <button className="w-full py-3 bg-slate-900 text-white rounded-xl text-sm font-semibold hover:bg-slate-800 transition-colors shadow-sm mt-2">
                        Update Password
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>

          <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-4">
            {saved && (
              <span className="flex items-center gap-1.5 text-sm font-bold text-emerald-600 animate-fade-in-up">
                <CheckCircle2 className="w-4 h-4" /> Changes saved
              </span>
            )}
            <Button
              onClick={handleSave}
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-200 border-0"
            >
              <Save className="w-4 h-4 mr-2" /> Save Preferences
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
