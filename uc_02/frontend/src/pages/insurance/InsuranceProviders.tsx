import { useState, useEffect } from 'react';
import { UserCheck, Search, Star, Mail, Phone, Calendar as CalendarIcon } from 'lucide-react';
import { getProviders } from '../../services/providersApi';
import type { Provider } from '../../types/provider';
import { Card, CardContent } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';

export function InsuranceProviders() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSpecialty, setSelectedSpecialty] = useState('All');

  useEffect(() => {
    getProviders().then(data => {
      setProviders(data);
      setLoading(false);
    });
  }, []);

  const specialties = ['All', ...Array.from(new Set(providers.map(p => p.specialty)))];
  
  const selectOptions = specialties.map(s => ({ label: s, value: s }));

  const filtered = providers.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.npi.includes(searchTerm);
    const matchesSpecialty = selectedSpecialty === 'All' || p.specialty === selectedSpecialty;
    return matchesSearch && matchesSpecialty;
  });

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up pb-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
          <UserCheck className="w-6 h-6 text-emerald-600" /> Providers
        </h1>
        <p className="text-sm text-slate-500 font-medium mt-1">Medical staff directory and performance metrics</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <Input 
            type="text" 
            placeholder="Search by name or NPI..." 
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="pl-9 w-full"
          />
        </div>
        <div className="w-full sm:w-64">
          <Select 
            value={selectedSpecialty}
            onChange={e => setSelectedSpecialty(e.target.value)}
            options={selectOptions}
          />
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-500 font-medium">Loading providers...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filtered.map(p => (
            <Card key={p.provider_id} className="overflow-hidden hover:shadow-md transition-shadow group border-slate-200">
              <div className={`h-2 w-full ${p.accent}`} />
              <CardContent className="p-5">
                <div className="flex items-start gap-4 mb-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-sm flex-shrink-0 ${p.accent}`}>
                    {p.avatar_initials}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900 leading-tight tracking-tight">{p.name}</h3>
                    <p className="text-sm text-emerald-600 font-semibold">{p.specialty}</p>
                  </div>
                </div>
                
                <div className="space-y-2 mb-5">
                  <div className="flex items-center gap-2 text-[13px] text-slate-600 font-medium">
                    <Phone className="w-4 h-4 text-slate-400" /> {p.phone}
                  </div>
                  <div className="flex items-center gap-2 text-[13px] text-slate-600 font-medium">
                    <Mail className="w-4 h-4 text-slate-400" /> {p.email}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">Auth Approval Rate</p>
                    <p className="text-lg font-bold text-slate-800 flex items-center gap-1 tracking-tight">
                      {p.approval_rate}% <Star className={`w-4 h-4 ${p.approval_rate >= 90 ? 'text-amber-400 fill-amber-400' : 'text-slate-300'}`} />
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">Active Claims</p>
                    <p className="text-lg font-bold text-slate-800 tracking-tight">{p.claims_count}</p>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <Badge variant={p.status === 'Active' ? 'success' : 'default'} className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider">
                    {p.status}
                  </Badge>
                  <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                    <CalendarIcon className="w-3 h-3" /> NPI: {p.npi}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-2xl border border-slate-200 border-dashed">
              No providers found matching your criteria.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
