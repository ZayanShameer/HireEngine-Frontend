import React, { useState, useEffect } from 'react';
import { 
  Building2, Users, FileUp, ClipboardList, BarChart3, Plus, 
  MapPin, Globe, Sparkles, Database, Layers, CheckCircle2, ArrowRight 
} from 'lucide-react';
import { Requisition, Candidate, HiringStage } from './types';
import { BulkUploadQueue } from './components/BulkUploadQueue';
import { CandidateDirectory } from './components/CandidateDirectory';
import { ExcelExporter } from './components/ExcelExporter';

// Initial Requisitions (Jobs Seed)
const SEED_REQUISITIONS: Requisition[] = [
  {
    id: 101,
    job_title: 'Petroleum Pipeline Engineer',
    location: 'Dubai, UAE',
    target_domain: 'Oil & Gas',
    job_description_text: 'Looking for a Senior Pipeline Engineer. Must have experience in petroleum pipelines, drilling simulation, gas reservoirs, refining operations, offshore wellhead setups, and hydrocarbon transport. Requires HSE certifications.',
    created_at: new Date(Date.now() - 86400000 * 5).toISOString()
  },
  {
    id: 102,
    job_title: 'Infrastructure & Rolling Stock Lead',
    location: 'Chicago, US',
    target_domain: 'Railway',
    job_description_text: 'Requires lead rail engineer for track layout, signaling systems, rolling stock maintenance, CBTC (Communication Based Train Control), bogie designs, and transit safety compliance. Railway industry experience is strictly mandatory.',
    created_at: new Date(Date.now() - 86400000 * 4).toISOString()
  },
  {
    id: 103,
    job_title: 'High-Voltage Switchgear Operator',
    location: 'Berlin, Germany',
    target_domain: 'Electrical/Testing',
    job_description_text: 'Seeking switchgear technicians with expertise in high voltage relay testing, substation GIS maintenance, SCADA control systems, transformers calibration, and CT/VT ratio inspections. Safety certified.',
    created_at: new Date(Date.now() - 86400000 * 3).toISOString()
  },
  {
    id: 104,
    job_title: 'Senior Frontend Developer',
    location: 'London, UK',
    target_domain: 'Information Technology',
    job_description_text: 'We are hiring a React developer with TypeScript, HTML/CSS layout capabilities, Redux state handling, and Git control skills. Docker and AWS deployment is a plus.',
    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
  }
];

// Initial Candidate Seeds showcasing the context domain matches & mismatch penalties
const SEED_CANDIDATES = (reqId101: number, reqId102: number, reqId104: number): Candidate[] => [
  {
    id: 1,
    requisition_id: reqId101,
    full_name: 'Robert Miller',
    email: 'robert.miller@shell.com',
    phone: '+971 50 123 4567',
    passport_number: 'N8491028',
    current_stage: 'Screening',
    total_experience_years: 8.0,
    relevant_experience_years: 8.0,
    match_score: 94,
    skills_matrix: ['PETROLEUM PIPING', 'DRILLING SIMULATION', 'HSE RISK MANAGEMENT', 'AUTOCAD'],
    specialization_tags: ['Deepwater Drilling', 'HSE Certified'],
    industry_remarks: 'Strong Domain Match. Candidate has 8.0 years of direct Oil & Gas experience at Shell. Highly relevant background in petroleum drilling and pipelines.',
    created_at: new Date(Date.now() - 3600000 * 12).toISOString()
  },
  {
    id: 2,
    requisition_id: reqId101,
    full_name: 'Arthur Pendelton',
    email: 'arthur.p@nationalrail.org',
    phone: '+1 312 555 8920',
    passport_number: 'A9201934',
    current_stage: 'Screening',
    total_experience_years: 8.0,
    relevant_experience_years: 1.2,
    match_score: 31,
    skills_matrix: ['ROLLING STOCK MAINTENANCE', 'SIGNALING SYSTEMS', 'PROJECT MANAGEMENT'],
    specialization_tags: ['CBTC Systems'],
    industry_remarks: 'Domain Mismatch Penalty. Candidate has 8.0 years of overall experience, but their footprint is heavily concentrated in the Railway industry (track signaling, rolling stock maintenance). Lacks the required Oil & Gas drilling/refining domain experience.',
    created_at: new Date(Date.now() - 3600000 * 10).toISOString()
  },
  {
    id: 3,
    requisition_id: reqId104,
    full_name: 'Jane Doe',
    email: 'jane.doe@reactjs.io',
    phone: '+44 7911 123456',
    passport_number: null,
    current_stage: 'Shortlist',
    total_experience_years: 6.0,
    relevant_experience_years: 6.0,
    match_score: 92,
    skills_matrix: ['REACT', 'TYPESCRIPT', 'JAVASCRIPT', 'GIT'],
    specialization_tags: [],
    industry_remarks: 'Strong Domain Match. Candidate demonstrates robust frontend capabilities with 6.0 years experience. Highly aligned with core TS/React stack.',
    created_at: new Date(Date.now() - 3600000 * 8).toISOString()
  },
  {
    id: 4,
    requisition_id: reqId104,
    full_name: 'David Kim',
    email: 'david.k@gmail.com',
    phone: '+44 7911 987654',
    passport_number: null,
    current_stage: 'Screening',
    total_experience_years: 2.0,
    relevant_experience_years: 2.0,
    match_score: 55,
    skills_matrix: ['REACT', 'JAVASCRIPT', 'FIGMA'],
    specialization_tags: [],
    industry_remarks: 'Partial Match. High potential React candidate but possesses only 2.0 years of experience. Lacks TypeScript skillset.',
    created_at: new Date(Date.now() - 3600000 * 6).toISOString()
  },
  {
    id: 5,
    requisition_id: reqId102,
    full_name: 'Marcus Chen',
    email: 'm.chen@bhel.com',
    phone: '+91 98765 43210',
    passport_number: 'P7291039',
    current_stage: 'Screening',
    total_experience_years: 5.0,
    relevant_experience_years: 5.0,
    match_score: 90,
    skills_matrix: ['ROLLING STOCK MAINTENANCE', 'SIGNALING SYSTEMS', 'AUTOCAD'],
    specialization_tags: ['CBTC Systems'],
    industry_remarks: 'Strong Domain Match. 5.0 years of rolling stock engineering. Deep competency in CBTC signaling and transit maintenance.',
    created_at: new Date(Date.now() - 3600000 * 4).toISOString()
  },
  {
    id: 6,
    requisition_id: reqId101,
    full_name: 'Emily Watson',
    email: 'emily.w@clinic.com',
    phone: '+1 617 555 0199',
    passport_number: null,
    current_stage: 'Rejected',
    total_experience_years: 5.0,
    relevant_experience_years: 0.0,
    match_score: 15,
    skills_matrix: ['NURSING CARE', 'CLINICAL TRIALS'],
    specialization_tags: [],
    industry_remarks: 'Domain Mismatch Penalty. Candidate has 5.0 years of experience in the Healthcare sector (nursing, clinical trials). Zero relevance to Oil & Gas pipeline layouts.',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString()
  }
];

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'screener' | 'directory' | 'requisitions'>('dashboard');
  const [requisitions, setRequisitions] = useState<Requisition[]>(SEED_REQUISITIONS);
  const [activeReqId, setActiveReqId] = useState<number>(101);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  
  // Custom Toast Alerts State
  const [toasts, setToasts] = useState<{ id: string; message: string; type: 'success' | 'info' | 'warning' }[]>([]);

  // Initialize candidates with seed data
  useEffect(() => {
    setCandidates(SEED_CANDIDATES(101, 102, 104));
  }, []);

  const activeRequisition = requisitions.find(r => r.id === activeReqId) || null;

  // Toast System trigger helper
  const addToast = (message: string, type: 'success' | 'info' | 'warning' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Requisitions Form State
  const [newTitle, setNewTitle] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [newDomain, setNewDomain] = useState<'Oil & Gas' | 'Railway' | 'Information Technology' | 'Healthcare' | 'Electrical/Testing'>('Oil & Gas');
  const [newDesc, setNewDesc] = useState('');

  const handleCreateRequisition = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newLocation || !newDesc) {
      alert('Please fill out all fields.');
      return;
    }
    const newReq: Requisition = {
      id: Math.floor(Math.random() * 10000),
      job_title: newTitle,
      location: newLocation,
      target_domain: newDomain,
      job_description_text: newDesc,
      created_at: new Date().toISOString()
    };
    setRequisitions(prev => [newReq, ...prev]);
    setActiveReqId(newReq.id);
    addToast(`Job profile for "${newTitle}" created successfully!`, 'success');
    
    // Reset Form
    setNewTitle('');
    setNewLocation('');
    setNewDesc('');
  };

  // Directory Actions
  const handleUpdateCandidateStage = (id: number, stage: HiringStage) => {
    setCandidates(prev => 
      prev.map(c => c.id === id ? { ...c, current_stage: stage } : c)
    );
    const cand = candidates.find(c => c.id === id);
    addToast(`${cand?.full_name} moved to "${stage}" stage.`, 'info');
  };

  const handleDeleteCandidate = (id: number) => {
    setCandidates(prev => prev.filter(c => c.id !== id));
    addToast('Candidate record deleted.', 'warning');
  };

  const handleCandidatesParsed = (newCandidates: Candidate[]) => {
    setCandidates(prev => [...newCandidates, ...prev]);
    addToast(`Successfully ingested & screened ${newCandidates.length} candidate CV(s).`, 'success');
  };

  // Inject Mock Seeds Helper (Manual Inject)
  const injectMockSeeds = () => {
    const seeds = SEED_CANDIDATES(101, 102, 104);
    // filter duplicates
    const nonDuplicated = seeds.filter(s => !candidates.some(c => c.email === s.email));
    if (nonDuplicated.length === 0) {
      addToast('Seed CVs already exist in active database.', 'info');
      return;
    }
    setCandidates(prev => [...nonDuplicated, ...prev]);
    addToast(`Injected ${nonDuplicated.length} demo candidate CV records.`, 'success');
  };

  // Dashboard calculations
  const totalCVs = candidates.length;
  const avgScore = totalCVs > 0 ? Math.round(candidates.reduce((sum, c) => sum + c.match_score, 0) / totalCVs) : 0;
  const shortlistedRate = totalCVs > 0 ? Math.round((candidates.filter(c => c.current_stage === 'Shortlist' || c.current_stage === 'Hired').length / totalCVs) * 100) : 0;
  const pendingScreen = candidates.filter(c => c.current_stage === 'Screening').length;

  // Custom SVG Chart calculations
  const domainStats = candidates.reduce((acc, c) => {
    const reqObj = requisitions.find(r => r.id === c.requisition_id);
    const domainName = reqObj?.target_domain || 'General';
    acc[domainName] = (acc[domainName] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="app-container">
      
      {/* 1. Dashboard Fixed Left Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo select-none">
            <span className="logo-icon">⚡</span>
            Hirengine AI
          </div>
        </div>

        <nav className="nav-menu">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          >
            <BarChart3 className="h-4.5 w-4.5" /> Dashboard Analytics
          </button>
          <button
            onClick={() => setActiveTab('screener')}
            className={`nav-item ${activeTab === 'screener' ? 'active' : ''}`}
          >
            <FileUp className="h-4.5 w-4.5" /> Batch CV Screener
          </button>
          <button
            onClick={() => setActiveTab('directory')}
            className={`nav-item ${activeTab === 'directory' ? 'active' : ''}`}
          >
            <Users className="h-4.5 w-4.5" /> Talent Directory
          </button>
          <button
            onClick={() => setActiveTab('requisitions')}
            className={`nav-item ${activeTab === 'requisitions' ? 'active' : ''}`}
          >
            <ClipboardList className="h-4.5 w-4.5" /> Job Requisitions
          </button>

          <div className="border-t border-[var(--border-light)] my-4 pt-4 px-2">
            <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase block mb-2.5">
              Active Requisition Selection
            </span>
            <select
              value={activeReqId}
              onChange={e => {
                setActiveReqId(parseInt(e.target.value, 10));
                addToast(`Active Job changed to: ${requisitions.find(r => r.id === parseInt(e.target.value, 10))?.job_title}`, 'info');
              }}
              className="w-full text-xs bg-black/[0.04] border border-[var(--border-light)] rounded-[var(--radius-md)] px-2.5 py-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]"
            >
              {requisitions.map(req => (
                <option key={req.id} value={req.id} className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  {req.job_title} ({req.target_domain})
                </option>
              ))}
            </select>
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="user-avatar">HR</div>
          <div className="user-info">
            <span className="user-name">HireEngine Operator</span>
            <span className="user-role">Lead Recruiter</span>
          </div>
        </div>
      </aside>

      {/* 2. Main Workspace Layout */}
      <main className="main-content">
        
        {/* Workspace Header */}
        <header className="header select-none">
          <h2 className="header-title flex items-center gap-4">
            {activeTab === 'dashboard' && 'Enterprise Dashboard'}
            {activeTab === 'screener' && 'Client-Side Batch CV Screener'}
            {activeTab === 'directory' && 'Faceted Talent Directory'}
            {activeTab === 'requisitions' && 'Job Requisitions Board'}
            {activeRequisition && (
              <span className="text-xs font-normal text-[var(--text-secondary)] bg-black/[0.04] px-2.5 py-1 rounded-[var(--radius-sm)] border border-[var(--border-light)]">
                Active Job: <span className="text-[var(--primary)] font-bold">{activeRequisition.job_title}</span>
              </span>
            )}
          </h2>

          <div className="header-actions">
            {activeTab === 'directory' && (
              <ExcelExporter 
                candidates={candidates} 
                activeRequisition={activeRequisition} 
              />
            )}
            <button 
              onClick={injectMockSeeds}
              className="btn btn-secondary flex items-center gap-1.5 text-xs py-2 px-3 border-dashed hover:border-[var(--primary)] hover:text-[var(--text-primary)]"
            >
              <Sparkles className="h-4 w-4 text-[var(--primary)] animate-bounce" />
              Inject Demo CVs
            </button>
          </div>
        </header>

        {/* Scrollable Main Area */}
        <div className="content-body select-none">
          
          {/* TAB 1: DASHBOARD ANALYTICS */}
          {activeTab === 'dashboard' && (
            <div className="animate-fade-in">
              
              {/* Stat Cards Grid */}
              <div className="stats-grid">
                <div className="stat-card glass primary">
                  <div className="stat-header">
                    <span>Total CVs Evaluated</span>
                    <div className="stat-icon-wrapper"><Database className="h-4 w-4" /></div>
                  </div>
                  <div className="stat-value">{totalCVs}</div>
                  <div className="stat-footer">
                    <span className="stat-trend up">↑ 22%</span> from last cycle
                  </div>
                </div>

                <div className="stat-card glass success">
                  <div className="stat-header">
                    <span>Avg Match Score</span>
                    <div className="stat-icon-wrapper"><Sparkles className="h-4 w-4" /></div>
                  </div>
                  <div className="stat-value">{avgScore}%</div>
                  <div className="stat-footer">
                    Target threshold: <span className="font-bold text-white">75%</span>
                  </div>
                </div>

                <div className="stat-card glass warning">
                  <div className="stat-header">
                    <span>Shortlisted / In-Play</span>
                    <div className="stat-icon-wrapper"><Users className="h-4 w-4" /></div>
                  </div>
                  <div className="stat-value">{shortlistedRate}%</div>
                  <div className="stat-footer">
                    Passed initial screening pipeline
                  </div>
                </div>

                <div className="stat-card glass info">
                  <div className="stat-header">
                    <span>Pending Evaluation</span>
                    <div className="stat-icon-wrapper"><Layers className="h-4 w-4 animate-pulse" /></div>
                  </div>
                  <div className="stat-value">{pendingScreen}</div>
                  <div className="stat-footer">
                    Awaiting manual review decisions
                  </div>
                </div>
              </div>

              {/* Charts Panel Grid */}
              <div className="dashboard-grid">
                
                {/* Chart 1: Candidate Distribution by Domain */}
                <div className="chart-card glass">
                  <div className="card-title-bar">
                    <h3 className="card-title"><BarChart3 className="h-4.5 w-4.5 text-[var(--primary)]" /> Candidate Pipeline by Domain</h3>
                  </div>
                  <div className="flex flex-col gap-4">
                    {Object.keys(SEED_REQUISITIONS.reduce((acc, r) => ({ ...acc, [r.target_domain]: 0 }), {} as Record<string, number>)).map(domain => {
                      const count = domainStats[domain] || 0;
                      const maxCount = Math.max(...Object.values(domainStats), 1);
                      const percent = Math.round((count / maxCount) * 100);
                      return (
                        <div key={domain} className="bar-chart-row">
                          <span className="bar-chart-label text-xs font-semibold text-[var(--text-secondary)]">{domain}</span>
                          <div className="bar-chart-track flex-1 bg-black/5 h-2 rounded-full overflow-hidden">
                            <div 
                              className="bar-chart-fill h-full bg-gradient-to-r from-[var(--primary)] to-[var(--primary-light)] rounded-full transition-all duration-1000"
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                          <span className="bar-chart-value text-xs font-bold text-[var(--text-primary)]">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Quick Actions Panel */}
                <div className="chart-card glass flex flex-col justify-between">
                  <div>
                    <h3 className="card-title mb-3">Quick Navigation</h3>
                    <p className="text-xs text-[var(--text-secondary)] mb-4">
                      Direct shortcuts to launch screener tasks, filter parsed profiles, and inspect job targets.
                    </p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button 
                      onClick={() => setActiveTab('screener')}
                      className="btn btn-primary text-xs w-full justify-between"
                    >
                      Launch Screener <ArrowRight className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={() => setActiveTab('directory')}
                      className="btn btn-secondary text-xs w-full text-left"
                    >
                      View Faceted Directory
                    </button>
                    <button 
                      onClick={() => setActiveTab('requisitions')}
                      className="btn btn-secondary text-xs w-full text-left"
                    >
                      Manage Job Requisitions
                    </button>
                  </div>
                </div>

              </div>

              {/* Deep Analysis SVG Spline and Skill-Gap Section */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* SVG Spline: Score Distribution Spline Curve */}
                <div className="chart-card glass">
                  <h3 className="card-title mb-4">Match Score Distribution Density</h3>
                  <div className="relative h-44 w-full border border-[var(--border-light)] bg-black/[0.02] rounded-[var(--radius-md)] p-3">
                    <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="var(--primary-light)" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      <path 
                        d="M 0 100 Q 15 90 25 80 T 50 60 T 75 20 T 100 100" 
                        fill="url(#scoreGrad)" 
                      />
                      <path 
                        d="M 0 100 Q 15 90 25 80 T 50 60 T 75 20 T 100 100" 
                        fill="none" 
                        stroke="var(--primary)" 
                        strokeWidth="2.5" 
                      />
                      <circle cx="25" cy="80" r="3" fill="var(--text-secondary)" />
                      <circle cx="50" cy="60" r="3" fill="var(--primary)" />
                      <circle cx="75" cy="20" r="3" fill="var(--primary-light)" />
                    </svg>
                    
                    <div className="absolute bottom-2 left-2 right-2 flex justify-between text-[9px] text-[var(--text-muted)]">
                      <span>Low Match (&lt;50)</span>
                      <span>Mid Match (50-79)</span>
                      <span>High Match (80+)</span>
                    </div>
                  </div>
                </div>

                {/* Skill alignment matrix gaps */}
                <div className="chart-card glass">
                  <h3 className="card-title mb-4">Extracted Technical Skills Density</h3>
                  <div className="flex flex-wrap gap-2">
                    {['REACT', 'TYPESCRIPT', 'ROLLING STOCK MAINTENANCE', 'PETROLEUM PIPING', 'SIGNALING SYSTEMS', 'AUTOCAD', 'HSE RISK MANAGEMENT'].map((skill) => {
                      const count = candidates.filter(c => c.skills_matrix.includes(skill)).length;
                      return (
                        <div 
                          key={skill} 
                          className="flex items-center justify-between text-[11px] font-bold px-3 py-1.5 rounded-[var(--radius-md)] bg-black/[0.02] border border-[var(--border-light)] w-full"
                        >
                          <span className="text-[var(--text-secondary)]">{skill}</span>
                          <span className="bg-[var(--primary-glow)] text-[var(--primary)] px-2 py-0.5 rounded border border-[var(--primary)]/30">
                            {count} CVs
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* TAB 2: BATCH CV SCREENER */}
          {activeTab === 'screener' && (
            <div className="screener-grid animate-fade-in">
              <div className="job-config-card glass">
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2.5">
                  <Building2 className="h-5 w-5 text-[var(--primary)]" />
                  Target Job Spec
                </h3>
                
                {activeRequisition ? (
                  <div className="flex flex-col gap-6 text-xs">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Title</span>
                      <div className="font-bold text-[var(--text-primary)] text-base mt-1">{activeRequisition.job_title}</div>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Target Domain / Industry</span>
                      <div className="text-xs bg-[var(--primary-glow)] border border-[var(--primary)]/20 px-3 py-1 rounded-full text-[var(--primary)] font-semibold inline-block mt-1">
                        {activeRequisition.target_domain}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Work Location</span>
                      <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)] mt-1">
                        <MapPin className="h-3.5 w-3.5 text-[var(--primary)]" /> {activeRequisition.location}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">JD Core Excerpts</span>
                      <p className="text-sm text-[var(--text-secondary)] leading-relaxed italic bg-black/[0.03] p-4 rounded-xl border border-[var(--border-light)] mt-1.5">
                        "{activeRequisition.job_description_text}"
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-[var(--text-muted)]">No active requisition selected.</div>
                )}
              </div>

              <div className="flex flex-col">
                <BulkUploadQueue 
                  activeRequisition={activeRequisition} 
                  onCandidatesParsed={handleCandidatesParsed} 
                />
              </div>
            </div>
          )}

          {/* TAB 3: TALENT DIRECTORY */}
          {activeTab === 'directory' && (
            <div className="h-full overflow-hidden">
              <CandidateDirectory 
                candidates={candidates} 
                onUpdateCandidateStage={handleUpdateCandidateStage}
                onDeleteCandidate={handleDeleteCandidate}
              />
            </div>
          )}

          {/* TAB 4: JOB REQUISITIONS BOARD */}
          {activeTab === 'requisitions' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 animate-fade-in">
              <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-8 h-fit md:col-span-1">
                <h3 className="font-bold text-lg mb-6 text-[var(--text-primary)]">Create Job Requisition</h3>
                <form onSubmit={handleCreateRequisition} className="flex flex-col gap-6 text-xs">
                  <div>
                    <label className="form-label">Job Title</label>
                    <input
                      type="text"
                      required
                      value={newTitle}
                      onChange={e => setNewTitle(e.target.value)}
                      placeholder="e.g. Lead Refinery Superintendent"
                      className="form-input text-sm"
                    />
                  </div>
                  <div>
                    <label className="form-label">Location</label>
                    <input
                      type="text"
                      required
                      value={newLocation}
                      onChange={e => setNewLocation(e.target.value)}
                      placeholder="e.g. Houston, US"
                      className="form-input text-sm"
                    />
                  </div>
                  <div>
                    <label className="form-label">Industry Classification Domain</label>
                    <select
                      value={newDomain}
                      onChange={e => setNewDomain(e.target.value as any)}
                      className="form-select text-sm"
                    >
                      <option value="Oil & Gas">Oil & Gas</option>
                      <option value="Railway">Railway</option>
                      <option value="Electrical/Testing">Electrical/Testing</option>
                      <option value="Information Technology">Information Technology</option>
                      <option value="Healthcare">Healthcare</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Job Description text</label>
                    <textarea
                      required
                      rows={5}
                      value={newDesc}
                      onChange={e => setNewDesc(e.target.value)}
                      placeholder="Specify required experience and domains..."
                      className="form-textarea text-sm"
                    />
                  </div>
                  <button type="submit" className="btn btn-primary text-xs w-full font-bold py-3.5 rounded-full cursor-pointer uppercase tracking-wider">
                    <Plus className="h-4 w-4" /> Create Requisition
                  </button>
                </form>
              </div>

              <div className="md:col-span-2 flex flex-col gap-2">
                <h3 className="font-bold text-lg text-[var(--text-primary)] mb-6">Active Job Requisitions ({requisitions.length})</h3>
                <div className="grid grid-cols-1 gap-6">
                  {requisitions.map(req => {
                    const reqCandidatesCount = candidates.filter(c => c.requisition_id === req.id).length;
                    return (
                      <div 
                        key={req.id}
                        className={`glass border rounded-[var(--radius-lg)] p-8 hover:border-[var(--primary)] transition-colors flex justify-between items-start gap-6 ${
                          activeReqId === req.id ? 'border-[var(--primary)] bg-[var(--primary-glow)]' : 'border-[var(--border-light)]'
                        }`}
                      >
                        <div className="flex flex-col gap-3">
                           <div className="flex items-center gap-3 flex-wrap">
                            <h4 className="font-bold text-base text-[var(--text-primary)]">{req.job_title}</h4>
                            <span className="text-xs bg-black/5 border border-black/10 px-3 py-1 rounded-full text-[var(--text-secondary)] font-medium">
                              {req.target_domain}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
                            <span className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5 text-[var(--primary)]" /> {req.location}</span>
                            <span className="text-slate-700 font-bold">•</span>
                            <span>Added {new Date(req.created_at).toLocaleDateString()}</span>
                          </div>
                          <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-[620px] mt-1">
                            {req.job_description_text}
                          </p>
                        </div>

                        <div className="flex flex-col items-end gap-3 flex-shrink-0">
                          <span className="text-xs font-semibold text-[var(--primary)] bg-[var(--primary-glow)] px-3.5 py-2 rounded-full border border-[var(--primary)]/30">
                            {reqCandidatesCount} Applicant(s)
                          </span>
                          <button
                            onClick={() => {
                              setActiveReqId(req.id);
                              addToast(`Active job requisition set to: ${req.job_title}`, 'info');
                            }}
                            disabled={activeReqId === req.id}
                            className={`px-4 py-2.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                              activeReqId === req.id 
                                ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 cursor-default' 
                                : 'bg-black/5 text-[var(--text-primary)] border border-black/10 hover:border-black/20 hover:bg-black/10'
                            }`}
                          >
                            {activeReqId === req.id ? 'Selected Active' : 'Set as Active'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* 3. Toast alerts display overlay */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div 
            key={toast.id} 
            className={`toast flex items-center gap-2 ${
              toast.type === 'success' ? 'success' :
              toast.type === 'warning' ? 'warning' : 'info'
            }`}
          >
            <CheckCircle2 className="h-4.5 w-4.5 text-inherit flex-shrink-0" />
            <span className="text-xs font-semibold text-[var(--text-primary)]">{toast.message}</span>
          </div>
        ))}
      </div>

    </div>
  );
}

export default App;
