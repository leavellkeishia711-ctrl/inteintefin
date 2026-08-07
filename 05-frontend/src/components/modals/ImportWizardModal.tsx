import { useState, useRef } from 'react';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadCsv, commitImport } from '@/lib/api/client';
import { X, Loader2, Upload, AlertCircle, CheckCircle2 } from 'lucide-react';

interface Props {
  onClose: () => void;
}

export function ImportWizardModal({ onClose }: Props) {

  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [step, setStep] = useState<1 | 2>(1);
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  const uploadMutation = useMutation({
    mutationFn: (f: File) => uploadCsv(f),
    onSuccess: (data) => {
      setPreviewData(data);
      
      // Auto-map columns with exact names
      const initialMap: Record<string, string> = {};
      const targetFields = ['type', 'category', 'amount', 'currency', 'occurred_on', 'description'];
      data.columns.forEach((col: string) => {
        const lower = col.toLowerCase();
        if (targetFields.includes(lower)) {
          initialMap[lower] = col;
        }
      });
      setMapping(initialMap);
      setStep(2);
    }
  });

  const commitMutation = useMutation({
    mutationFn: () => commitImport(previewData.batch_id, mapping),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      onClose();
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (file) uploadMutation.mutate(file);
  };

  const handleCommit = () => {
    commitMutation.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-xl border border-border w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-content-primary">Import CSV Wizard</h2>
          <button onClick={onClose} className="text-content-secondary hover:text-content-primary">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {step === 1 ? (
            <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-border rounded-xl">
              <Upload className="w-12 h-12 text-content-tertiary mb-4" />
              <h3 className="text-lg font-medium text-content-primary mb-2">Upload your CSV file</h3>
              <p className="text-content-secondary mb-6 text-center max-w-md">
                Ensure your CSV has headers. The file must contain date, amount, currency, and type.
              </p>
              <input 
                type="file" 
                accept=".csv" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileChange}
              />
              <div className="flex items-center gap-4">
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 bg-background border border-border rounded-lg text-content-primary hover:bg-surface-hover transition-colors"
                >
                  {file ? file.name : "Select File"}
                </button>
                <button 
                  onClick={handleUpload}
                  disabled={!file || uploadMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
                >
                  {uploadMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Upload & Next
                </button>
              </div>
              {uploadMutation.isError && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {(uploadMutation.error as Error).message}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-primary-500/10 border border-primary-500/20 p-4 rounded-lg flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-primary-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-primary-500">File uploaded successfully</h4>
                  <p className="text-sm text-content-secondary mt-1">We detected {previewData.row_count} rows and {previewData.columns.length} columns. Please map your columns below.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h4 className="font-medium text-content-primary">Column Mapping</h4>
                  <p className="text-sm text-content-secondary">Map the required fields to the columns found in your CSV.</p>
                  
                  {['amount', 'currency', 'type', 'category', 'occurred_on', 'description', 'external_id'].map(field => (
                    <div key={field} className="flex items-center justify-between gap-4">
                      <label className="text-sm font-medium text-content-primary w-1/3">
                        {field} {['amount', 'currency', 'type', 'category', 'occurred_on'].includes(field) && <span className="text-red-500">*</span>}
                      </label>
                      <select 
                        value={mapping[field] || ''}
                        onChange={(e) => setMapping({...mapping, [field]: e.target.value})}
                        className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                      >
                        <option value="">-- Ignore --</option>
                        {previewData.columns.map((col: string) => (
                          <option key={col} value={col}>{col}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium text-content-primary">Data Preview</h4>
                  <div className="border border-border rounded-lg overflow-hidden bg-background max-h-[400px] overflow-y-auto">
                    <table className="w-full text-left text-xs whitespace-nowrap">
                      <thead className="bg-surface sticky top-0 border-b border-border">
                        <tr>
                          {previewData.columns.map((col: string) => (
                            <th key={col} className="px-3 py-2 font-medium text-content-secondary">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {previewData.preview.map((row: any, i: number) => (
                          <tr key={i} className="hover:bg-surface transition-colors">
                            {previewData.columns.map((col: string) => (
                              <td key={col} className="px-3 py-2 text-content-primary truncate max-w-[150px]">
                                {row[col]}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-border flex justify-between bg-surface">
          {step === 2 && (
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-border text-content-secondary rounded-lg hover:text-content-primary transition-colors"
            >
              Back
            </button>
          )}
          <div className="flex gap-3 ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-border text-content-secondary rounded-lg hover:text-content-primary transition-colors"
            >
              Cancel
            </button>
            {step === 2 && (
              <button
                onClick={handleCommit}
                disabled={commitMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {commitMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Import Data
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


