import React, { useState } from 'react';
import { Download, FileSpreadsheet, Loader2, Check } from 'lucide-react';
import { Candidate, Requisition } from '../types';

interface ExcelExporterProps {
  candidates: Candidate[];
  activeRequisition: Requisition | null;
}

export const ExcelExporter: React.FC<ExcelExporterProps> = ({
  candidates,
  activeRequisition
}) => {
  const [exportState, setExportState] = useState<'idle' | 'preparing' | 'downloading' | 'completed'>('idle');

  // String Sanitization Filter: Ensures safe-string parsing for Microsoft Excel
  const sanitizeCell = (val: string | number | null | undefined): string => {
    if (val === null || val === undefined) return '';
    let str = String(val).trim();
    
    // Excel-compliant escaping rules:
    // 1. Double quotes inside a field must be escaped by doubling them (e.g. ""text"")
    // 2. Fields with commas, double quotes, or newlines must be enclosed in double quotes
    if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
      str = str.replace(/"/g, '""');
      return `"${str}"`;
    }
    return str;
  };

  const handleExport = () => {
    if (candidates.length === 0) {
      alert('No candidate records found in active directory to export.');
      return;
    }

    setExportState('preparing');

    // Simulate short loader delay for UI micro-animations and feedback
    setTimeout(() => {
      setExportState('downloading');

      // 1. Explicit 8-Column Schema Header
      const headers = [
        'Name',
        'Email',
        'Phone',
        'Candidate Field / Role',
        'Years of Experience',
        'Relevant Experience',
        'Match Score',
        'Remarks'
      ];

      // 2. Build rows mapping candidate records
      const csvRows = [headers.join(',')];

      candidates.forEach(candidate => {
        const row = [
          sanitizeCell(candidate.full_name),
          sanitizeCell(candidate.email),
          sanitizeCell(candidate.phone),
          sanitizeCell(activeRequisition?.job_title || 'General Pipeline'),
          sanitizeCell(candidate.total_experience_years),
          sanitizeCell(candidate.relevant_experience_years),
          sanitizeCell(`${candidate.match_score}%`),
          sanitizeCell(candidate.industry_remarks)
        ];
        csvRows.push(row.join(','));
      });

      // 3. Assemble complete CSV payload with UTF-8 BOM for Excel compatibility
      const csvContent = '\uFEFF' + csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      
      // 4. Download trigger
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const requisitionName = activeRequisition ? activeRequisition.job_title.replace(/\s+/g, '_') : 'Master';
      const dateStamp = new Date().toISOString().split('T')[0];
      
      link.href = url;
      link.setAttribute('download', `Hirengine_${requisitionName}_Talent_Sheet_${dateStamp}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportState('completed');

      // Reset to idle state after notification display
      setTimeout(() => {
        setExportState('idle');
      }, 2500);

    }, 1200);
  };

  return (
    <div className="flex items-center">
      <button
        onClick={handleExport}
        disabled={candidates.length === 0 || exportState !== 'idle'}
        className={`btn flex items-center gap-2 text-xs font-bold transition-all px-4 py-2.5 rounded-[var(--radius-md)] border cursor-pointer ${
          exportState === 'completed'
            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/25'
            : candidates.length === 0
            ? 'bg-white/5 text-[var(--text-muted)] border-white/5 cursor-not-allowed'
            : 'btn-primary border-transparent hover:-translate-y-0.5'
        }`}
      >
        {exportState === 'idle' && (
          <>
            <FileSpreadsheet className="h-4.5 w-4.5" />
            Export Master Talent Sheet
          </>
        )}
        {exportState === 'preparing' && (
          <>
            <Loader2 className="h-4.5 w-4.5 animate-spin" />
            Formatting Records...
          </>
        )}
        {exportState === 'downloading' && (
          <>
            <Loader2 className="h-4.5 w-4.5 animate-spin text-[var(--primary)]" />
            Compiling CSV...
          </>
        )}
        {exportState === 'completed' && (
          <>
            <Check className="h-4.5 w-4.5 text-emerald-400" />
            Talent Sheet Downloaded!
          </>
        )}
      </button>
    </div>
  );
};
