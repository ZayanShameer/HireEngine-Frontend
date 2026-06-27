import React, { useState, useEffect, useCallback } from 'react';
import { 
  Building2, Users, FileUp, ClipboardList, BarChart3, Plus, 
  MapPin, Database, Layers, CheckCircle2, ArrowRight, Trash2,
  AlertTriangle, TrendingUp, Clock, Target
} from 'lucide-react';
import { Requisition, Candidate, HiringStage } from './types';
import { BulkUploadQueue } from './components/BulkUploadQueue';
import { CandidateDirectory } from './components/CandidateDirectory';
import { ExcelExporter } from './components/ExcelExporter';

// Seed Requisitions — shown on first launch; user can delete them
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

// localStorage persistence hook
function useLocalStorage<T>(key: string, initialValue: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue: React.Dispatch<React.SetStateAction<T>> = useCallback((value) => {
    setStoredValue(prev => {
      const valueToStore = value instanceof Function ? value(prev) : value;
      try {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      } catch { /* ignore */ }
      return valueToStore;
    });
  }, [key]);

  return [storedValue, setValue];
}

const STAGES: HiringStage[] = ['Screening', 'Shortlist', 'Interviewing', 'Offered', 'Hired', 'Rejected'];

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'screener' | 'directory' | 'requisitions'>('dashboard');

  // Persisted state
  const [requisitions, setRequisitions] = useLocalStorage<Requisition[]>('hireengine_requisitions', SEED_REQUISITIONS);
  const [candidates, setCandidates] = useLocalStorage<Candidate[]>('hireengine_candidates', []);
  const [activeReqId, setActiveReqId] = useLocalStorage<number>('hireengine_active_req', 101);

  // Toast state
  const [toasts, setToasts] = useState<{ id: string; message: string; type: 'success' | 'info' | 'warning' | 'error' }[]>([]);

  // Clear all confirm modal
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // Ensure activeReqId is always valid
  useEffect(() => {
    if (requisitions.length > 0 && !requisitions.find(r => r.id === activeReqId)) {
      setActiveReqId(requisitions[0].id);
    }
  }, [requisitions, activeReqId, setActiveReqId]);

  const activeRequisition = requisitions.find(r => r.id === activeReqId) || null;

  // Toast helper
  const addToast = (message: string, type: 'success' | 'info' | 'warning' | 'error' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4500);
  };

  // Requisition form state
  const [newTitle, setNewTitle] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [newDomain, setNewDomain] = useState<'Oil & Gas' | 'Railway' | 'Information Technology' | 'Healthcare' | 'Electrical/Testing'>('Oil & Gas');
  const [newDesc, setNewDesc] = useState('');

  const handleCreateRequisition = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newLocation || !newDesc) {
      addToast('Please fill out all fields.', 'error');
      return;
    }
    const newReq: Requisition = {
      id: Math.floor(Math.random() * 10000) + 200,
      job_title: newTitle,
      location: newLocation,
      target_domain: newDomain,
      job_description_text: newDesc,
      created_at: new Date().toISOString()
    };
    setRequisitions(prev => [newReq, ...prev]);
    setActiveReqId(newReq.id);
    addToast(`Job requisition "${newTitle}" created & set as active.`, 'success');
    setNewTitle('');
    setNewLocation('');
    setNewDesc('');
  };

  const handleDeleteRequisition = (reqId: number) => {
    const req = requisitions.find(r => r.id === reqId);
    const cascadeCount = candidates.filter(c => c.requisition_id === reqId).length;
    setCandidates(prev => prev.filter(c => c.requisition_id !== reqId));
    setRequisitions(prev => prev.filter(r => r.id !== reqId));
    addToast(`"${req?.job_title}" deleted. ${cascadeCount > 0 ? `${cascadeCount} associated candidate(s) removed.` : ''}`, 'warning');
  };

  // Candidate actions
  const handleUpdateCandidateStage = (id: number, stage: HiringStage) => {
    setCandidates(prev => prev.map(c => c.id === id ? { ...c, current_stage: stage } : c));
    const cand = candidates.find(c => c.id === id);
    addToast(`${cand?.full_name} moved to "${stage}".`, 'info');
  };

  const handleDeleteCandidate = (id: number) => {
    setCandidates(prev => prev.filter(c => c.id !== id));
    addToast('Candidate record deleted.', 'warning');
  };

  const handleCandidatesParsed = (newCandidates: Candidate[]) => {
    setCandidates(prev => [...newCandidates, ...prev]);
    addToast(`Successfully screened ${newCandidates.length} candidate CV(s).`, 'success');
  };

  const handleClearAllCandidates = () => {
    setCandidates([]);
    setShowClearConfirm(false);
    addToast('All candidate records cleared from the system.', 'warning');
  };

  // Dashboard calculations — real data
  const totalCVs = candidates.length;
  const avgScore = totalCVs > 0 ? Math.round(candidates.reduce((sum, c) => sum + c.match_score, 0) / totalCVs) : 0;
  const shortlistedCount = candidates.filter(c => c.current_stage === 'Shortlist' || c.current_stage === 'Hired' || c.current_stage === 'Offered' || c.current_stage === 'Interviewing').length;
  const pendingScreen = candidates.filter(c => c.current_stage === 'Screening').length;
  const rejectedCount = candidates.filter(c => c.current_stage === 'Rejected').length;

  const oneWeekAgo = new Date(Date.now() - 86400000 * 7).toISOString();
  const newThisWeek = candidates.filter(c => c.created_at >= oneWeekAgo).length;

  const domainStats = candidates.reduce((acc, c) => {
    const reqObj = requisitions.find(r => r.id === c.requisition_id);
    const domainName = reqObj?.target_domain || 'General';
    acc[domainName] = (acc[domainName] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const stageStats = STAGES.reduce((acc, stage) => {
    acc[stage] = candidates.filter(c => c.current_stage === stage).length;
    return acc;
  }, {} as Record<HiringStage, number>);

  const highMatchCount = candidates.filter(c => c.match_score >= 80).length;

  return (
    <div className="app-container">
      
      {/* Confirm Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowClearConfirm(false)}
          />
          <div className="relative bg-[var(--bg-surface)] border border-[var(--border-light)] rounded-[var(--radius-lg)] p-8 max-w-sm w-full mx-4 shadow-2xl animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-rose-500/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-rose-500" />
              </div>
              <div>
                <h3 className="font-bold text-base text-[var(--text-primary)]">Clear All Candidates?</h3>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-6 leading-relaxed">
              This will permanently delete all <strong>{totalCVs}</strong> candidate records from the system. Job requisitions will remain intact.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="flex-1 btn btn-secondary text-sm py-2.5 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleClearAllCandidates}
                className="flex-1 btn text-sm py-2.5 cursor-pointer bg-rose-500 text-white hover:bg-rose-600 border-transparent"
              >
                Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Left Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo select-none">
            <span className="logo-icon">⚡</span>
            HireEngine AI
          </div>
        </div>

        <nav className="nav-menu">
          <button onClick={() => setActiveTab('dashboard')} className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}>
            <BarChart3 className="h-4 w-4" /> Dashboard Analytics
          </button>
          <button onClick={() => setActiveTab('screener')} className={`nav-item ${activeTab === 'screener' ? 'active' : ''}`}>
            <FileUp className="h-4 w-4" /> Batch CV Screener
          </button>
          <button onClick={() => setActiveTab('directory')} className={`nav-item ${activeTab === 'directory' ? 'active' : ''}`}>
            <Users className="h-4 w-4" /> Talent Directory
          </button>
          <button onClick={() => setActiveTab('requisitions')} className={`nav-item ${activeTab === 'requisitions' ? 'active' : ''}`}>
            <ClipboardList className="h-4 w-4" /> Job Requisitions
          </button>

          {/* Active Requisition Selector */}
          <div className="border-t border-[var(--border-light)] mt-4 pt-4 px-2">
            <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase block mb-2.5 tracking-wider">
              Active Job Context
            </span>
            {requisitions.length > 0 ? (
              <select
                value={activeReqId}
                onChange={e => {
                  const id = parseInt(e.target.value, 10);
                  setActiveReqId(id);
                  addToast(`Active context switched to: ${requisitions.find(r => r.id === id)?.job_title}`, 'info');
                }}
                className="w-full text-xs bg-black/[0.04] border border-[var(--border-light)] rounded-[var(--radius-md)] px-2.5 py-2.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
              >
                {requisitions.map(req => (
                  <option key={req.id} value={req.id} className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                    {req.job_title} ({req.target_domain})
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-[var(--text-muted)] italic">No requisitions yet.</p>
            )}
          </div>

          {/* System Stats */}
          {totalCVs > 0 && (
            <div className="px-2 mt-4 pt-4 border-t border-[var(--border-light)]">
              <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase block mb-2.5 tracking-wider">
                System Stats
              </span>
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[var(--text-muted)]">Total CVs</span>
                  <span className="font-bold text-[var(--text-primary)]">{totalCVs}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[var(--text-muted)]">Avg Score</span>
                  <span className={`font-bold ${avgScore >= 75 ? 'text-emerald-600' : avgScore >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>{avgScore}%</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[var(--text-muted)]">Shortlisted</span>
                  <span className="font-bold text-emerald-600">{shortlistedCount}</span>
                </div>
              </div>
            </div>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-avatar">HR</div>
          <div className="user-info">
            <span className="user-name">HireEngine Operator</span>
            <span className="user-role">Lead Recruiter</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        
        {/* Header */}
        <header className="header select-none">
          <h2 className="header-title flex items-center gap-4">
            {activeTab === 'dashboard' && 'Enterprise Dashboard'}
            {activeTab === 'screener' && 'Batch CV Screener'}
            {activeTab === 'directory' && 'Talent Directory'}
            {activeTab === 'requisitions' && 'Job Requisitions Board'}
            {activeRequisition && (
              <span className="text-xs font-normal text-[var(--text-secondary)] bg-black/[0.04] px-2.5 py-1 rounded-[var(--radius-sm)] border border-[var(--border-light)]">
                Active: <span className="text-[var(--primary)] font-bold">{activeRequisition.job_title}</span>
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
            {activeTab === 'directory' && totalCVs > 0 && (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="btn btn-secondary flex items-center gap-1.5 text-xs py-2 px-3 text-rose-500 border-rose-200 hover:bg-rose-50 cursor-pointer"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Clear All
              </button>
            )}
            <button
              onClick={() => setActiveTab('screener')}
              className={`btn btn-primary text-xs py-2 px-4 cursor-pointer ${activeTab === 'screener' ? 'opacity-50 pointer-events-none' : ''}`}
            >
              <FileUp className="h-3.5 w-3.5" /> Screen CVs
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="content-body">

          {/* ── TAB 1: DASHBOARD ── */}
          {activeTab === 'dashboard' && (
            <div className="animate-fade-in">

              {totalCVs === 0 ? (
                /* Empty State */
                <div className="empty-state-container">
                  <div className="empty-state-icon">
                    <Database className="h-10 w-10" />
                  </div>
                  <h3 className="empty-state-title">No candidate data yet</h3>
                  <p className="empty-state-desc">
                    Your analytics dashboard will populate automatically as you screen CVs. Upload your first batch to get started.
                  </p>
                  <button
                    onClick={() => setActiveTab('screener')}
                    className="btn btn-primary text-sm px-6 py-3 cursor-pointer"
                  >
                    <FileUp className="h-4 w-4" /> Go to CV Screener
                  </button>
                </div>
              ) : (
                <>
                  {/* Stat Cards */}
                  <div className="stats-grid">
                    <div className="stat-card glass primary">
                      <div className="stat-header">
                        <span>Total CVs Evaluated</span>
                        <div className="stat-icon-wrapper"><Database className="h-4 w-4" /></div>
                      </div>
                      <div className="stat-value">{totalCVs}</div>
                      <div className="stat-footer">
                        <TrendingUp className="h-3 w-3 text-emerald-500" />
                        <span className="text-emerald-600 font-bold">{newThisWeek} new</span> this week
                      </div>
                    </div>

                    <div className="stat-card glass success">
                      <div className="stat-header">
                        <span>Avg Match Score</span>
                        <div className="stat-icon-wrapper"><Target className="h-4 w-4" /></div>
                      </div>
                      <div className="stat-value">{avgScore}%</div>
                      <div className="stat-footer">
                        <span className="font-bold" style={{ color: avgScore >= 75 ? 'var(--success)' : 'var(--warning)' }}>
                          {avgScore >= 75 ? '✓ Above threshold' : '↓ Below 75% target'}
                        </span>
                      </div>
                    </div>

                    <div className="stat-card glass warning">
                      <div className="stat-header">
                        <span>In Active Pipeline</span>
                        <div className="stat-icon-wrapper"><Users className="h-4 w-4" /></div>
                      </div>
                      <div className="stat-value">{shortlistedCount}</div>
                      <div className="stat-footer">
                        <span>{highMatchCount} high-match (80%+)</span>
                      </div>
                    </div>

                    <div className="stat-card glass info">
                      <div className="stat-header">
                        <span>Pending Screening</span>
                        <div className="stat-icon-wrapper"><Clock className="h-4 w-4" /></div>
                      </div>
                      <div className="stat-value">{pendingScreen}</div>
                      <div className="stat-footer">
                        <span>{rejectedCount} rejected this cycle</span>
                      </div>
                    </div>
                  </div>

                  {/* Charts Row */}
                  <div className="dashboard-grid">

                    {/* Domain Distribution */}
                    <div className="chart-card glass">
                      <div className="card-title-bar">
                        <h3 className="card-title"><BarChart3 className="h-4 w-4 text-[var(--primary)]" /> Candidate Pipeline by Domain</h3>
                      </div>
                      <div className="flex flex-col gap-4">
                        {Object.entries(domainStats).sort((a, b) => b[1] - a[1]).map(([domain, count]) => {
                          const maxCount = Math.max(...Object.values(domainStats), 1);
                          const percent = Math.round((count / maxCount) * 100);
                          return (
                            <div key={domain} className="bar-chart-row">
                              <span className="bar-chart-label">{domain}</span>
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
                        {Object.keys(domainStats).length === 0 && (
                          <p className="text-xs text-[var(--text-muted)] text-center py-4">No domain data available.</p>
                        )}
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="chart-card glass flex flex-col justify-between">
                      <div>
                        <h3 className="card-title mb-3">Quick Navigation</h3>
                        <p className="text-xs text-[var(--text-secondary)] mb-4">
                          Direct shortcuts to launch screener tasks, filter parsed profiles, and inspect job targets.
                        </p>
                      </div>
                      <div className="flex flex-col gap-2">
                        <button onClick={() => setActiveTab('screener')} className="btn btn-primary text-xs w-full justify-between cursor-pointer">
                          Screen More CVs <ArrowRight className="h-4 w-4" />
                        </button>
                        <button onClick={() => setActiveTab('directory')} className="btn btn-secondary text-xs w-full text-left cursor-pointer">
                          View Talent Directory
                        </button>
                        <button onClick={() => setActiveTab('requisitions')} className="btn btn-secondary text-xs w-full text-left cursor-pointer">
                          Manage Requisitions
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Stage Pipeline Funnel */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="chart-card glass">
                      <h3 className="card-title mb-5">Hiring Stage Pipeline</h3>
                      <div className="flex flex-col gap-3">
                        {STAGES.map(stage => {
                          const count = stageStats[stage] || 0;
                          const maxStageCount = Math.max(...Object.values(stageStats), 1);
                          const pct = Math.round((count / maxStageCount) * 100);
                          const stageColor: Record<HiringStage, string> = {
                            'Screening': 'bg-slate-400',
                            'Shortlist': 'bg-emerald-500',
                            'Interviewing': 'bg-sky-500',
                            'Offered': 'bg-[var(--primary)]',
                            'Hired': 'bg-teal-500',
                            'Rejected': 'bg-rose-400',
                          };
                          return (
                            <div key={stage} className="flex items-center gap-3">
                              <span className="text-xs font-semibold text-[var(--text-secondary)] w-24 flex-shrink-0">{stage}</span>
                              <div className="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-700 ${stageColor[stage]}`} style={{ width: `${pct}%` }} />
                              </div>
                              <span className="text-xs font-bold text-[var(--text-primary)] w-6 text-right">{count}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Score Distribution */}
                    <div className="chart-card glass">
                      <h3 className="card-title mb-4">Match Score Distribution</h3>
                      <div className="flex flex-col gap-3">
                        {[
                          { label: 'High Match (80–100)', count: candidates.filter(c => c.match_score >= 80).length, color: 'bg-emerald-500' },
                          { label: 'Mid Match (50–79)', count: candidates.filter(c => c.match_score >= 50 && c.match_score < 80).length, color: 'bg-amber-500' },
                          { label: 'Low Match (0–49)', count: candidates.filter(c => c.match_score < 50).length, color: 'bg-rose-400' },
                        ].map(({ label, count, color }) => {
                          const pct = totalCVs > 0 ? Math.round((count / totalCVs) * 100) : 0;
                          return (
                            <div key={label}>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                                <span className="text-xs font-bold text-[var(--text-primary)]">{count} <span className="text-[var(--text-muted)] font-normal">({pct}%)</span></span>
                              </div>
                              <div className="h-2 bg-black/5 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Top Skills */}
                      <div className="mt-6 border-t border-[var(--border-light)] pt-5">
                        <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase tracking-wider mb-3">Top Extracted Skills</h4>
                        <div className="flex flex-wrap gap-2">
                          {(() => {
                            const skillMap: Record<string, number> = {};
                            candidates.forEach(c => c.skills_matrix.forEach(s => { skillMap[s] = (skillMap[s] || 0) + 1; }));
                            return Object.entries(skillMap).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([skill, count]) => (
                              <span key={skill} className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/20">
                                {skill} <span className="opacity-60">×{count}</span>
                              </span>
                            ));
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── TAB 2: SCREENER ── */}
          {activeTab === 'screener' && (
            <div className="screener-grid animate-fade-in">
              {/* Left: Job Spec Panel */}
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
                    <button
                      onClick={() => setActiveTab('requisitions')}
                      className="btn btn-secondary text-xs w-full cursor-pointer mt-1"
                    >
                      <ClipboardList className="h-3.5 w-3.5" /> Switch Job Context
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    <p className="text-sm text-[var(--text-muted)]">No active requisition. Create one first.</p>
                    <button
                      onClick={() => setActiveTab('requisitions')}
                      className="btn btn-primary text-xs w-full cursor-pointer"
                    >
                      <Plus className="h-3.5 w-3.5" /> Create Requisition
                    </button>
                  </div>
                )}
              </div>

              {/* Right: Upload Queue */}
              <div className="flex flex-col">
                <BulkUploadQueue 
                  activeRequisition={activeRequisition} 
                  onCandidatesParsed={handleCandidatesParsed} 
                />
              </div>
            </div>
          )}

          {/* ── TAB 3: DIRECTORY ── */}
          {activeTab === 'directory' && (
            <div className="h-full overflow-hidden">
              <CandidateDirectory 
                candidates={candidates}
                requisitions={requisitions}
                onUpdateCandidateStage={handleUpdateCandidateStage}
                onDeleteCandidate={handleDeleteCandidate}
                onNavigateToScreener={() => setActiveTab('screener')}
              />
            </div>
          )}

          {/* ── TAB 4: REQUISITIONS ── */}
          {activeTab === 'requisitions' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 animate-fade-in">
              {/* Create Form */}
              <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-8 h-fit md:col-span-1">
                <h3 className="font-bold text-lg mb-6 text-[var(--text-primary)]">Create Job Requisition</h3>
                <form onSubmit={handleCreateRequisition} className="flex flex-col gap-5 text-xs">
                  <div>
                    <label className="form-label">Job Title</label>
                    <input
                      type="text" required value={newTitle}
                      onChange={e => setNewTitle(e.target.value)}
                      placeholder="e.g. Lead Refinery Superintendent"
                      className="form-input text-sm"
                    />
                  </div>
                  <div>
                    <label className="form-label">Location</label>
                    <input
                      type="text" required value={newLocation}
                      onChange={e => setNewLocation(e.target.value)}
                      placeholder="e.g. Houston, US"
                      className="form-input text-sm"
                    />
                  </div>
                  <div>
                    <label className="form-label">Industry Domain</label>
                    <select value={newDomain} onChange={e => setNewDomain(e.target.value as any)} className="form-select text-sm">
                      <option value="Oil & Gas">Oil & Gas</option>
                      <option value="Railway">Railway</option>
                      <option value="Electrical/Testing">Electrical/Testing</option>
                      <option value="Information Technology">Information Technology</option>
                      <option value="Healthcare">Healthcare</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Job Description</label>
                    <textarea
                      required rows={5} value={newDesc}
                      onChange={e => setNewDesc(e.target.value)}
                      placeholder="Specify required experience and domain keywords..."
                      className="form-textarea text-sm"
                    />
                  </div>
                  <button type="submit" className="btn btn-primary text-xs w-full font-bold py-3.5 rounded-full cursor-pointer uppercase tracking-wider">
                    <Plus className="h-4 w-4" /> Create Requisition
                  </button>
                </form>
              </div>

              {/* Requisition List */}
              <div className="md:col-span-2 flex flex-col gap-2">
                <h3 className="font-bold text-lg text-[var(--text-primary)] mb-4">
                  Active Requisitions <span className="text-[var(--text-muted)] font-normal text-base">({requisitions.length})</span>
                </h3>
                {requisitions.length === 0 ? (
                  <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-12 text-center">
                    <ClipboardList className="h-10 w-10 text-[var(--text-muted)] mx-auto mb-3" />
                    <p className="text-sm text-[var(--text-muted)]">No job requisitions yet. Create one to get started.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4">
                    {requisitions.map(req => {
                      const reqCandidatesCount = candidates.filter(c => c.requisition_id === req.id).length;
                      return (
                        <div
                          key={req.id}
                          className={`glass border rounded-[var(--radius-lg)] p-6 hover:border-[var(--primary)] transition-colors flex justify-between items-start gap-6 ${
                            activeReqId === req.id ? 'border-[var(--primary)] bg-[var(--primary-glow)]' : 'border-[var(--border-light)]'
                          }`}
                        >
                          <div className="flex flex-col gap-2.5 min-w-0">
                            <div className="flex items-center gap-3 flex-wrap">
                              <h4 className="font-bold text-base text-[var(--text-primary)]">{req.job_title}</h4>
                              <span className="text-xs bg-black/5 border border-black/10 px-3 py-0.5 rounded-full text-[var(--text-secondary)] font-medium">
                                {req.target_domain}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
                              <span className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5 text-[var(--primary)]" /> {req.location}</span>
                              <span className="text-slate-400">•</span>
                              <span>Added {new Date(req.created_at).toLocaleDateString()}</span>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-[520px] mt-0.5 line-clamp-2">
                              {req.job_description_text}
                            </p>
                          </div>

                          <div className="flex flex-col items-end gap-2.5 flex-shrink-0">
                            <span className="text-xs font-semibold text-[var(--primary)] bg-[var(--primary-glow)] px-3 py-1.5 rounded-full border border-[var(--primary)]/30">
                              {reqCandidatesCount} Applicant{reqCandidatesCount !== 1 ? 's' : ''}
                            </span>
                            <button
                              onClick={() => {
                                setActiveReqId(req.id);
                                addToast(`Active context: ${req.job_title}`, 'info');
                              }}
                              disabled={activeReqId === req.id}
                              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                                activeReqId === req.id
                                  ? 'bg-emerald-500/10 text-emerald-700 border border-emerald-500/30 cursor-default'
                                  : 'bg-black/5 text-[var(--text-primary)] border border-black/10 hover:border-black/20 hover:bg-black/10'
                              }`}
                            >
                              {activeReqId === req.id ? '✓ Active' : 'Set Active'}
                            </button>
                            <button
                              onClick={() => {
                                if (window.confirm(`Delete "${req.job_title}"? This will also remove ${reqCandidatesCount} associated candidate(s).`)) {
                                  handleDeleteRequisition(req.id);
                                }
                              }}
                              className="text-rose-400/70 hover:text-rose-500 p-1.5 hover:bg-rose-50 rounded-md transition-colors cursor-pointer"
                              title="Delete Requisition"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </main>

      {/* Toast Overlay */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`toast flex items-center gap-2 ${
              toast.type === 'success' ? 'success' :
              toast.type === 'warning' ? 'warning' :
              toast.type === 'error' ? 'error' : 'info'
            }`}
          >
            <CheckCircle2 className="h-4 w-4 text-inherit flex-shrink-0" />
            <span className="text-xs font-semibold text-[var(--text-primary)]">{toast.message}</span>
          </div>
        ))}
      </div>

    </div>
  );
}

export default App;
