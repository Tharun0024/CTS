import { useState } from 'react';
import { FileText, Search, Upload, Download, Eye, File, FileImage, ShieldAlert, FolderHeart, Activity, CheckCircle2 } from 'lucide-react';
import { mockDocuments } from '../../mock/documents';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

export function Documents() {
  const [documents] = useState(mockDocuments);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('All');

  const categories = ['All', 'Clinical', 'Imaging', 'Lab', 'Administrative', 'Legal'];

  const filtered = documents.filter(doc => {
    const matchesSearch = doc.file_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          (doc.patient_name && doc.patient_name.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesTab = activeTab === 'All' || doc.category === activeTab;
    return matchesSearch && matchesTab;
  });

  const getIcon = (type: string, category: string) => {
    if (category === 'Imaging') return <FileImage className="w-5 h-5 text-purple-500" />;
    if (category === 'Lab') return <Activity className="w-5 h-5 text-amber-500" />;
    if (category === 'Legal') return <ShieldAlert className="w-5 h-5 text-rose-500" />;
    if (type === 'PDF') return <FileText className="w-5 h-5 text-blue-500" />;
    return <File className="w-5 h-5 text-slate-500" />;
  };

  const getIconBg = (category: string) => {
    if (category === 'Imaging') return 'bg-purple-100';
    if (category === 'Lab') return 'bg-amber-100';
    if (category === 'Legal') return 'bg-rose-100';
    return 'bg-blue-100';
  };

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center shadow-md">
              <FolderHeart className="w-4 h-4 text-white" />
            </div>
            Document Center
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Manage clinical and administrative records centrally</p>
        </div>
        <Button className="bg-slate-900 hover:bg-slate-800 text-white shadow-md w-max border-0">
          <Upload className="w-4 h-4 mr-2" /> Upload Document
        </Button>
      </div>

      <Card className="flex flex-col min-h-[600px] overflow-hidden">
        {/* Toolbar */}
        <CardHeader className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap gap-1.5 p-1 bg-white border border-slate-200 rounded-xl max-w-fit">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveTab(cat)}
                  className={clsx(
                    "px-4 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap",
                    activeTab === cat 
                      ? "bg-slate-800 text-white shadow-sm" 
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
            
            <div className="relative w-full md:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <Input 
                type="text" 
                placeholder="Search files or patients..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-9 w-full shadow-sm"
              />
            </div>
          </div>
        </CardHeader>

        {/* Table */}
        <CardContent className="p-0 flex-1 flex flex-col">
          <Table className="min-w-[700px] flex-1">
            <TableHeader className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-semibold">
              <TableRow className="hover:bg-transparent">
                <TableHead className="py-3 px-5">File Name & Info</TableHead>
                <TableHead className="py-3 px-5">Patient / Context</TableHead>
                <TableHead className="py-3 px-5">Category</TableHead>
                <TableHead className="py-3 px-5">Date & Uploader</TableHead>
                <TableHead className="py-3 px-5 text-right"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(doc => (
                <TableRow key={doc.doc_id} className="hover:bg-slate-50/60 transition-colors group cursor-pointer">
                  <TableCell className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm", getIconBg(doc.category))}>
                        {getIcon(doc.file_type, doc.category)}
                      </div>
                      <div className="min-w-0 max-w-[250px]">
                        <p className="text-[13px] font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors" title={doc.file_name}>{doc.file_name}</p>
                        <p className="text-xs text-slate-500 font-medium mt-0.5">{doc.file_type} • {(doc.size_kb/1024).toFixed(1)} MB</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="px-5 py-4">
                    {doc.patient_name ? (
                      <>
                        <p className="text-[13px] font-bold text-slate-700">{doc.patient_name}</p>
                        {doc.claim_id && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <Badge variant="success" className="px-1.5 py-0 text-[10px] uppercase font-bold tracking-wider">
                              Claim: {doc.claim_id}
                            </Badge>
                          </div>
                        )}
                      </>
                    ) : (
                      <Badge variant="default" className="px-2 py-0.5 text-[10px] font-medium italic">Administrative</Badge>
                    )}
                  </TableCell>
                  <TableCell className="px-5 py-4">
                    <span className="px-2.5 py-1 bg-white border border-slate-200 shadow-sm rounded-lg text-xs font-semibold text-slate-600">
                      {doc.category}
                    </span>
                  </TableCell>
                  <TableCell className="px-5 py-4">
                    <p className="text-[13px] font-bold text-slate-700">{new Date(doc.uploaded_at).toLocaleDateString()}</p>
                    <p className="text-xs text-slate-500 truncate mt-0.5 font-medium">{doc.uploaded_by}</p>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Preview">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" title="Download">
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={5} className="px-6 py-20 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mx-auto mb-4 border border-slate-100">
                        <FileText className="w-8 h-8 text-slate-300" />
                      </div>
                      <h3 className="text-sm font-bold text-slate-800 mb-1">No documents found</h3>
                      <p className="text-slate-500 font-medium text-xs">Try adjusting your filters or search term.</p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          
          {filtered.length > 0 && (
            <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between mt-auto">
              <span className="text-xs font-semibold text-slate-500">
                Showing <span className="font-bold text-slate-700">{filtered.length}</span> of <span className="font-bold text-slate-700">{documents.length}</span> files
              </span>
              <div className="flex items-center gap-1 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-100">
                <CheckCircle2 className="w-4 h-4" /> Secure Vault Active
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
