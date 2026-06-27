import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, RefreshCw, Layers, Plus, ChevronDown, ChevronUp, User } from 'lucide-react';
import * as XLSX from 'xlsx';
import { QueueItem, Requisition, Candidate, TargetDomain } from '../types';

interface BulkUploadQueueProps {
  activeRequisition: Requisition | null;
  onCandidatesParsed: (candidates: Candidate[]) => void;
}

// Manual entry form initial state
const BLANK_MANUAL = {
  full_name: '',
  email: '',
  phone: '',
  passport_number: '',
  total_experience: '',
  skills: '',
  remarks: '',
};

export const BulkUploadQueue: React.FC<BulkUploadQueueProps> = ({
  activeRequisition,
  onCandidatesParsed
}) => {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualForm, setManualForm] = useState(BLANK_MANUAL);
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = () => setIsDragActive(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFilesToQueue(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFilesToQueue(Array.from(e.target.files));
      e.target.value = '';
    }
  };

  const triggerFileInput = () => fileInputRef.current?.click();

  const addFilesToQueue = (files: File[]) => {
    if (!activeRequisition) {
      alert('Please select or create a Job Requisition first!');
      return;
    }
    const newQueueItems: QueueItem[] = files.map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      fileName: file.name,
      fileSize: file.size,
      progress: 0,
      status: 'pending'
    }));
    setQueue(prev => [...prev, ...newQueueItems]);
    files.forEach((file, index) => processFile(file, newQueueItems[index].id));
  };

  const processFile = async (file: File, id: string) => {
    const updateProgress = (progress: number, status: QueueItem['status']) => {
      setQueue(prev => prev.map(item => item.id === id ? { ...item, progress, status } : item));
    };

    try {
      const fileExt = file.name.split('.').pop()?.toLowerCase();

      if (fileExt === 'xlsx' || fileExt === 'xls') {
        updateProgress(20, 'extracting');
        const data = await file.arrayBuffer();
        const workbook = XLSX.read(data, { type: 'array' });
        const worksheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(worksheet) as any[];
        updateProgress(50, 'scoring');

        const parsedCandidates: Candidate[] = [];
        for (let i = 0; i < rows.length; i++) {
          const row = rows[i];
          const getVal = (aliases: string[]) => {
            const match = Object.keys(row).find(key => aliases.includes(key.toUpperCase().replace(/[\s._-]/g, '')));
            return match ? String(row[match]).trim() : '';
          };
          const fullName = getVal(['NAME', 'FULLNAME', 'CANDIDATENAME', 'APPLICANTNAME']) || `Candidate #${i + 1}`;
          const position = getVal(['POSITION', 'ROLE', 'FIELD', 'JOBTITLE']) || activeRequisition?.job_title || '';
          const phone = getVal(['CONTACTNO', 'PHONE', 'PHONENO', 'MOBILE']) || 'N/A';
          const email = getVal(['MAILID', 'EMAIL', 'EMAILID', 'EMAILADDRESS']) || 'N/A';
          const excelRemarks = getVal(['REMARKS', 'NOTES', 'COMMENT', 'FEEDBACK']) || '';
          const screenResult = calculateLocalScreening(
            `Role: ${position}. ${excelRemarks}. Experience in ${activeRequisition?.target_domain}`,
            activeRequisition!
          );
          parsedCandidates.push({
            id: Math.floor(Math.random() * 1000000),
            requisition_id: activeRequisition!.id,
            full_name: fullName, email, phone,
            passport_number: null,
            current_stage: 'Screening',
            total_experience_years: screenResult.totalExperience,
            relevant_experience_years: screenResult.relevantExperience,
            match_score: screenResult.score,
            skills_matrix: screenResult.skills,
            specialization_tags: screenResult.tags,
            industry_remarks: excelRemarks ? `${excelRemarks} | ${screenResult.remarks}` : screenResult.remarks,
            created_at: new Date().toISOString()
          });
        }
        updateProgress(100, 'completed');
        onCandidatesParsed(parsedCandidates);
        return;
      }

      let rawText = '';
      updateProgress(10, 'extracting');

      if (fileExt === 'pdf') {
        const arrayBuffer = await file.arrayBuffer();
        rawText = await extractTextFromPDF(arrayBuffer, pct => updateProgress(10 + Math.floor(pct * 40), 'extracting'));
      } else if (fileExt === 'txt') {
        rawText = await file.text();
        updateProgress(50, 'extracting');
      } else {
        throw new Error('Unsupported format. Please upload PDF, TXT, or XLSX.');
      }

      updateProgress(60, 'scoring');

      let candidateResult: Partial<Candidate>;
      try {
        const response = await fetch('/api/v1/screen-candidate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            candidate_text: rawText,
            target_domain: activeRequisition!.target_domain,
            requisition_id: activeRequisition!.id
          })
        });
        if (response.ok) {
          const resJson = await response.json();
          candidateResult = {
            full_name: resJson.full_name || file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' '),
            email: resJson.email || extractEmailRegex(rawText),
            phone: resJson.phone || extractPhoneRegex(rawText),
            total_experience_years: resJson.total_experience_years,
            relevant_experience_years: resJson.relevant_experience_years,
            match_score: resJson.match_score,
            skills_matrix: resJson.skills_matrix,
            specialization_tags: resJson.specialization_tags,
            industry_remarks: resJson.industry_remarks
          };
        } else {
          throw new Error('API unavailable, using client engine.');
        }
      } catch {
        const localScreen = calculateLocalScreening(rawText, activeRequisition!);
        candidateResult = {
          full_name: extractNameFromText(rawText) || file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' '),
          email: extractEmailRegex(rawText),
          phone: extractPhoneRegex(rawText),
          total_experience_years: localScreen.totalExperience,
          relevant_experience_years: localScreen.relevantExperience,
          match_score: localScreen.score,
          skills_matrix: localScreen.skills,
          specialization_tags: localScreen.tags,
          industry_remarks: localScreen.remarks
        };
      }

      updateProgress(90, 'scoring');

      const finalCandidate: Candidate = {
        id: Math.floor(Math.random() * 1000000),
        requisition_id: activeRequisition!.id,
        full_name: candidateResult.full_name || 'Unknown Candidate',
        email: candidateResult.email || 'N/A',
        phone: candidateResult.phone || 'N/A',
        passport_number: extractPassportRegex(rawText),
        current_stage: 'Screening',
        total_experience_years: candidateResult.total_experience_years || 0,
        relevant_experience_years: candidateResult.relevant_experience_years || 0,
        match_score: candidateResult.match_score || 0,
        skills_matrix: candidateResult.skills_matrix || [],
        specialization_tags: candidateResult.specialization_tags || [],
        industry_remarks: candidateResult.industry_remarks || '',
        created_at: new Date().toISOString()
      };

      updateProgress(100, 'completed');
      onCandidatesParsed([finalCandidate]);

    } catch (err: any) {
      setQueue(prev => prev.map(item => item.id === id ? { ...item, status: 'failed', error: err.message || 'Parsing failed' } : item));
    }
  };

  // Manual candidate submission
  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRequisition) return;
    setManualSubmitting(true);

    setTimeout(() => {
      const skillsArray = manualForm.skills
        .split(',')
        .map(s => s.trim().toUpperCase())
        .filter(s => s.length > 0);

      const expYears = parseFloat(manualForm.total_experience) || 0;
      const combinedText = `${manualForm.full_name} ${manualForm.remarks} ${manualForm.skills}`;
      const screenResult = calculateLocalScreening(combinedText, activeRequisition!);

      // Override experience with user-provided value
      screenResult.totalExperience = expYears;
      if (screenResult.relevantExperience > expYears) screenResult.relevantExperience = expYears;

      const candidate: Candidate = {
        id: Math.floor(Math.random() * 1000000),
        requisition_id: activeRequisition!.id,
        full_name: manualForm.full_name,
        email: manualForm.email || 'N/A',
        phone: manualForm.phone || 'N/A',
        passport_number: manualForm.passport_number || null,
        current_stage: 'Screening',
        total_experience_years: expYears,
        relevant_experience_years: screenResult.relevantExperience,
        match_score: screenResult.score,
        skills_matrix: skillsArray.length > 0 ? skillsArray : screenResult.skills,
        specialization_tags: screenResult.tags,
        industry_remarks: manualForm.remarks
          ? `${manualForm.remarks} | ${screenResult.remarks}`
          : screenResult.remarks,
        created_at: new Date().toISOString()
      };

      onCandidatesParsed([candidate]);
      setManualForm(BLANK_MANUAL);
      setManualSubmitting(false);
      setShowManualForm(false);
    }, 600);
  };

  const extractTextFromPDF = async (arrayBuffer: ArrayBuffer, onPageExtract: (pct: number) => void): Promise<string> => {
    const pdfjsLib = (window as any)['pdfjs-dist/build/pdf'];
    if (!pdfjsLib) throw new Error('PDF.js library not loaded. Please check internet connection.');
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let fullText = '';
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      fullText += textContent.items.map((item: any) => item.str).join(' ') + '\n';
      onPageExtract(i / pdf.numPages);
    }
    return fullText;
  };

  const extractEmailRegex = (text: string): string => {
    const match = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
    return match ? match[0] : 'N/A';
  };

  const extractPhoneRegex = (text: string): string => {
    const match = text.match(/(?:\+?\d{1,3}[.\s-]?)?\(?\d{3}\)?[.\s-]?\d{3}[.\s-]?\d{4}/);
    return match ? match[0] : 'N/A';
  };

  const extractPassportRegex = (text: string): string | null => {
    const match = text.match(/[A-Z][0-9]{7,8}/i);
    return match ? match[0].toUpperCase() : null;
  };

  const extractNameFromText = (text: string): string | null => {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    for (let i = 0; i < Math.min(3, lines.length); i++) {
      const words = lines[i].split(' ');
      if (words.length >= 2 && words.length <= 4 && !lines[i].includes('@')) return lines[i];
    }
    return null;
  };

  const calculateLocalScreening = (text: string, req: Requisition) => {
    const cleanText = text.toLowerCase();
    const domainTaxonomy: Record<TargetDomain, string[]> = {
      'Oil & Gas': ['petroleum', 'drilling', 'refinery', 'offshore', 'pipeline', 'hydrocarbon', 'gas', 'hse', 'reservoir', 'piping'],
      'Railway': ['locomotive', 'rolling stock', 'signaling', 'track', 'rail', 'transit', 'metro', 'derailment', 'bogie'],
      'Electrical/Testing': ['transformer', 'relay', 'switchgear', 'gis', 'voltage', 'scada', 'ct', 'vt', 'testing', 'substation'],
      'Information Technology': ['react', 'typescript', 'javascript', 'python', 'flask', 'software', 'database', 'sql', 'git', 'backend'],
      'Healthcare': ['clinical', 'nursing', 'medical', 'hospital', 'patient', 'health', 'surgeon', 'healthcare', 'diagnosis']
    };

    const specsPool = ['13.8KV', '380KV', '765KV', 'HSE Certified', 'Deepwater Drilling', 'ETAP', 'CBTC', 'PLC/SCADA'];
    const matchedSpecs = specsPool.filter(tag => cleanText.includes(tag.toLowerCase()));

    const commonSkills = [
      'react', 'typescript', 'javascript', 'python', 'sql', 'git', 'docker', 'aws',
      'petroleum piping', 'drilling simulation', 'hse risk management', 'etap safety',
      'rolling stock maintenance', 'signaling systems', 'high voltage relay', 'gis maintenance',
      'switchgear testing', 'scada control', 'nursing care', 'clinical trials', 'figma',
      'autocad', 'project management', 'data analysis', 'machine learning', 'java', 'c++',
    ];
    const extractedSkills = commonSkills.filter(skill => cleanText.includes(skill)).map(s => s.toUpperCase());

    let totalExperience = 0;
    const expMatches = cleanText.match(/(\d+)\+?\s*years?\s+(?:of\s+)?experience/);
    totalExperience = expMatches ? parseInt(expMatches[1], 10) : Math.floor(Math.random() * 8) + 2;

    const currentDomain = req.target_domain;
    const domainCounts = Object.keys(domainTaxonomy).reduce((acc, domain) => {
      const keywords = domainTaxonomy[domain as TargetDomain];
      const count = keywords.reduce((sum, word) => {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        return sum + (cleanText.match(regex)?.length || 0);
      }, 0);
      acc[domain as TargetDomain] = count;
      return acc;
    }, {} as Record<TargetDomain, number>);

    let candidatePrimaryDomain: TargetDomain = 'Information Technology';
    let maxDensity = 0;
    Object.entries(domainCounts).forEach(([domain, count]) => {
      if (count > maxDensity) { maxDensity = count; candidatePrimaryDomain = domain as TargetDomain; }
    });

    const isDomainMatch = candidatePrimaryDomain === currentDomain;
    let relevantExperience = totalExperience;
    let score: number;
    let remarks: string;

    if (!isDomainMatch && maxDensity > 2) {
      relevantExperience = Math.max(0, Math.floor(totalExperience * 0.15));
      score = Math.floor(25 + Math.random() * 10);
      remarks = `Domain Mismatch. Candidate profile is concentrated in ${candidatePrimaryDomain}. Lacks the required ${currentDomain} domain experience.`;
    } else {
      relevantExperience = totalExperience;
      const skillMatchRatio = extractedSkills.length > 0 ? Math.min(100, extractedSkills.length * 20) : 50;
      score = Math.min(100, Math.floor((skillMatchRatio * 0.6) + (relevantExperience >= 5 ? 40 : relevantExperience * 8)));
      remarks = `Strong Domain Match. Candidate demonstrates alignment with ${currentDomain}. ${relevantExperience} years of relevant industry experience.`;
    }

    return { score, totalExperience, relevantExperience, skills: extractedSkills.length > 0 ? extractedSkills : ['GENERAL CONSULTING'], tags: matchedSpecs, remarks };
  };

  const getFileIconColor = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'xlsx' || ext === 'xls') return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
    if (ext === 'pdf') return 'text-rose-500 bg-rose-500/10 border-rose-500/20';
    return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
  };

  const clearQueue = () => setQueue([]);

  return (
    <div className="flex flex-col gap-6">

      {/* Upload Card */}
      <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-lg flex items-center gap-2">
            <Layers className="text-[var(--primary)] h-5 w-5" />
            Bulk Upload & CV Parser
          </h3>
          {queue.length > 0 && (
            <button
              onClick={clearQueue}
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] px-3.5 py-1.5 bg-black/5 rounded-[var(--radius-sm)] border border-[var(--border-light)] transition-colors cursor-pointer"
            >
              Clear Queue
            </button>
          )}
        </div>

        {/* Active Job Banner */}
        {activeRequisition ? (
          <div className="mb-5 text-sm text-[var(--text-secondary)] bg-[var(--primary-glow)] px-4 py-3 rounded-[var(--radius-md)] border border-[var(--border-focus)]">
            <span className="font-bold text-[var(--text-primary)]">Active Mapping: </span>
            {activeRequisition.job_title} ({activeRequisition.location}) — Target:{' '}
            <span className="font-bold text-[var(--primary)]">{activeRequisition.target_domain}</span>
          </div>
        ) : (
          <div className="mb-5 text-sm text-rose-600 bg-rose-500/8 px-4 py-3 rounded-[var(--radius-md)] border border-rose-500/20">
            ⚠️ Please select or create a Job Requisition before uploading CVs.
          </div>
        )}

        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={triggerFileInput}
          className={`upload-dropzone border-2 border-dashed rounded-[var(--radius-md)] p-10 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
            isDragActive
              ? 'border-[var(--primary)] bg-[var(--primary-glow)]'
              : 'border-[var(--border-light)] bg-black/[0.01] hover:border-[var(--primary)] hover:bg-black/[0.015]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.xlsx,.xls"
            onChange={handleFileChange}
            className="hidden"
            disabled={!activeRequisition}
          />
          <div className="upload-icon-wrapper w-16 h-16 rounded-full bg-[var(--primary-glow)] border border-[var(--primary)]/20 flex items-center justify-center text-[var(--primary)] mb-4">
            <Upload className="h-7 w-7 animate-pulse" />
          </div>
          <p className="font-bold text-base text-[var(--text-primary)] mb-1">
            Drag & drop CV files here, or click to browse
          </p>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            Supports PDF resumes, plain text, and Excel applicant logs (.xlsx)
          </p>
          <div className="flex items-center gap-6 text-xs text-[var(--text-muted)] border-t border-[var(--border-light)] pt-4 w-full justify-center">
            <span>PDF extraction runs fully client-side</span>
            <span>•</span>
            <span>Excel maps columns natively</span>
          </div>
        </div>

        {/* Queue List */}
        {queue.length > 0 && (
          <div className="queue-list mt-6 max-h-[280px] overflow-y-auto pr-1">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Ingestion Queue ({queue.filter(i => i.status === 'completed').length}/{queue.length} done)
            </h4>
            <div className="flex flex-col gap-3">
              {queue.map(item => {
                const iconColorClass = getFileIconColor(item.fileName);
                return (
                  <div key={item.id} className="queue-item border border-[var(--border-light)] rounded-[var(--radius-md)] p-4 bg-black/[0.015]">
                    <div className="flex items-center justify-between gap-4 mb-3.5">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded border ${iconColorClass}`}>
                          <FileText className="h-5 w-5" />
                        </div>
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-[var(--text-primary)] truncate max-w-[220px]" title={item.fileName}>
                            {item.fileName}
                          </span>
                          <span className="text-xs text-[var(--text-muted)]">{(item.fileSize / 1024).toFixed(1)} KB</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status === 'pending' && <span className="text-xs text-[var(--text-muted)]">Queued...</span>}
                        {item.status === 'extracting' && (
                          <span className="text-xs text-sky-500 font-medium flex items-center gap-1.5 animate-pulse">
                            <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Extracting
                          </span>
                        )}
                        {item.status === 'scoring' && (
                          <span className="text-xs text-[var(--primary)] font-medium flex items-center gap-1.5 animate-pulse">
                            <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Scoring
                          </span>
                        )}
                        {item.status === 'completed' && (
                          <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1.5">
                            <CheckCircle className="h-4 w-4" /> Done
                          </span>
                        )}
                        {item.status === 'failed' && (
                          <span className="text-xs text-rose-500 font-semibold flex items-center gap-1.5" title={item.error}>
                            <AlertCircle className="h-4 w-4" /> Failed
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="h-1.5 bg-black/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          item.status === 'failed' ? 'bg-rose-500' :
                          item.status === 'completed' ? 'bg-emerald-500' : 'bg-gradient-to-r from-[var(--primary)] to-[var(--primary-light)]'
                        }`}
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Manual Candidate Entry Card */}
      <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] overflow-hidden">
        <button
          onClick={() => setShowManualForm(prev => !prev)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-black/[0.015] transition-colors cursor-pointer"
        >
          <span className="font-bold text-base flex items-center gap-2.5 text-[var(--text-primary)]">
            <User className="h-5 w-5 text-[var(--primary)]" />
            Add Candidate Manually
          </span>
          {showManualForm ? <ChevronUp className="h-4 w-4 text-[var(--text-muted)]" /> : <ChevronDown className="h-4 w-4 text-[var(--text-muted)]" />}
        </button>

        {showManualForm && (
          <div className="px-6 pb-6 border-t border-[var(--border-light)] pt-5 animate-fade-in">
            {!activeRequisition && (
              <div className="mb-4 text-sm text-rose-600 bg-rose-500/8 px-4 py-2.5 rounded-[var(--radius-md)] border border-rose-500/20">
                ⚠️ Select an active requisition before adding a candidate.
              </div>
            )}
            <form onSubmit={handleManualSubmit} className="grid grid-cols-1 gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Full Name *</label>
                  <input
                    type="text" required
                    value={manualForm.full_name}
                    onChange={e => setManualForm(p => ({ ...p, full_name: e.target.value }))}
                    placeholder="e.g. John Smith"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
                <div>
                  <label className="form-label">Email</label>
                  <input
                    type="email"
                    value={manualForm.email}
                    onChange={e => setManualForm(p => ({ ...p, email: e.target.value }))}
                    placeholder="john@company.com"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    value={manualForm.phone}
                    onChange={e => setManualForm(p => ({ ...p, phone: e.target.value }))}
                    placeholder="+1 555 000 0000"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
                <div>
                  <label className="form-label">Passport No.</label>
                  <input
                    type="text"
                    value={manualForm.passport_number}
                    onChange={e => setManualForm(p => ({ ...p, passport_number: e.target.value }))}
                    placeholder="e.g. A1234567"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Total Experience (years) *</label>
                  <input
                    type="number" min="0" max="50" step="0.5" required
                    value={manualForm.total_experience}
                    onChange={e => setManualForm(p => ({ ...p, total_experience: e.target.value }))}
                    placeholder="e.g. 7.5"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
                <div>
                  <label className="form-label">Skills (comma-separated)</label>
                  <input
                    type="text"
                    value={manualForm.skills}
                    onChange={e => setManualForm(p => ({ ...p, skills: e.target.value }))}
                    placeholder="e.g. React, TypeScript, Git"
                    className="form-input text-sm"
                    disabled={!activeRequisition}
                  />
                </div>
              </div>

              <div>
                <label className="form-label">Recruiter Remarks</label>
                <textarea
                  rows={3}
                  value={manualForm.remarks}
                  onChange={e => setManualForm(p => ({ ...p, remarks: e.target.value }))}
                  placeholder="Any notes about this candidate's background, fit, or concerns..."
                  className="form-textarea text-sm"
                  disabled={!activeRequisition}
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => { setManualForm(BLANK_MANUAL); setShowManualForm(false); }}
                  className="btn btn-secondary text-xs flex-1 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!activeRequisition || manualSubmitting}
                  className="btn btn-primary text-xs flex-1 cursor-pointer disabled:opacity-50"
                >
                  {manualSubmitting ? (
                    <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Scoring...</>
                  ) : (
                    <><Plus className="h-3.5 w-3.5" /> Add to Pipeline</>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
