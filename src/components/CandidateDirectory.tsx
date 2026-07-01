import React, { useState, useRef, useCallback, useEffect } from 'react';
import { 
  Search, SlidersHorizontal, Table, LayoutDashboard, User, Mail, 
  Phone, Briefcase, Award, X, Trash2, Shield, FileUp, Users, Download,
  Sparkles, Loader2, Zap
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { Candidate, HiringStage, TargetDomain, Requisition } from '../types';

interface CandidateDirectoryProps {
  candidates: Candidate[];
  requisitions: Requisition[];
  onUpdateCandidateStage: (id: number, stage: HiringStage) => void;
  onDeleteCandidate: (id: number) => void;
  onNavigateToScreener: () => void;
}

const STAGES: HiringStage[] = ['Screening', 'Shortlist', 'Interviewing', 'Offered', 'Hired', 'Rejected'];
const DOMAINS: TargetDomain[] = [
  'Oil & Gas', 'Petrochemical', 'Construction & Infrastructure',
  'Energy', 'Hospitality', 'Facilities Management', 'Maritime & Shipping',
  'Power Plants', 'Engineering Services', 'Manufacturing', 'EPC'
];
const SPECIALIZATIONS = [
  'NEBOSH', 'IOSH', 'OSHA 30', 'BOSIET', 'H2S Alive', 'API 510', 'CSWIP 3.1',
  'PMP', 'Primavera P6', 'AutoCAD', 'Six Sigma', 'Lean Manufacturing', 'HAZOP',
  'ETAP', 'SCADA', 'PLC', 'BIM', 'Revit', 'HACCP', 'Food Safety', 'ServSafe',
  'IFMA CFM', 'LEED', 'HVAC Certification', 'STCW', 'DP Operator', 'MARPOL',
  'Boiler Operator', 'DCS', 'SolidWorks', 'ANSYS', 'ISO 9001', 'CQE'
];

export const CandidateDirectory: React.FC<CandidateDirectoryProps> = ({
  candidates,
  requisitions,
  onUpdateCandidateStage,
  onDeleteCandidate,
  onNavigateToScreener
}) => {
  // Navigation & View Toggles
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('list');
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  // Faceted Search Filters State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomains, setSelectedDomains] = useState<TargetDomain[]>([]);
  const [selectedSpecs, setSelectedSpecs] = useState<string[]>([]);
  const [minScore, setMinScore] = useState(0);
  const [maxScore, setMaxScore] = useState(100);

  // Magic Search state
  const [searchMode, setSearchMode] = useState<'quick' | 'magic'>('quick');
  const [magicQuery, setMagicQuery] = useState('');
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicResults, setMagicResults] = useState<(Candidate & { relevance_score?: number; matched_signals?: string[] })[]>([]);
  const [magicSignals, setMagicSignals] = useState<{ skills?: string[]; domains?: string[]; specs?: string[]; exp_years?: number | null } | null>(null);
  const magicDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Kanban board ref for horizontal wheel-scroll listener
  const kanbanRef = useRef<HTMLDivElement>(null);

  // Translate vertical mouse-wheel events into horizontal scroll on the kanban board
  useEffect(() => {
    const el = kanbanRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (e.deltaY === 0) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [viewMode]);

  // Toggle Filters
  const handleDomainFilter = (domain: TargetDomain) => {
    setSelectedDomains(prev => 
      prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]
    );
  };

  const handleSpecFilter = (spec: string) => {
    setSelectedSpecs(prev => 
      prev.includes(spec) ? prev.filter(s => s !== spec) : [...prev, spec]
    );
  };

  // Reset Filters
  const resetFilters = () => {
    setSearchQuery('');
    setSelectedDomains([]);
    setSelectedSpecs([]);
    setMinScore(0);
    setMaxScore(100);
    setMagicQuery('');
    setMagicResults([]);
    setMagicSignals(null);
  };

  // Magic Search â€” debounced call to backend
  const runMagicSearch = useCallback((query: string) => {
    if (magicDebounce.current) clearTimeout(magicDebounce.current);
    if (!query.trim()) {
      setMagicResults([]);
      setMagicSignals(null);
      setMagicLoading(false);
      return;
    }
    setMagicLoading(true);
    magicDebounce.current = setTimeout(async () => {
      try {
        const resp = await fetch('http://localhost:5000/api/v1/semantic-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, candidates })
        });
        if (resp.ok) {
          const data = await resp.json();
          setMagicResults(data.results || []);
          setMagicSignals(data.signals || null);
        }
      } catch {
        // fallback: keep showing all candidates
        setMagicResults([]);
      } finally {
        setMagicLoading(false);
      }
    }, 500);
  }, [candidates]);

  const handleMagicQueryChange = (q: string) => {
    setMagicQuery(q);
    runMagicSearch(q);
  };

  const switchMode = (mode: 'quick' | 'magic') => {
    setSearchMode(mode);
    if (mode === 'quick') { setMagicQuery(''); setMagicResults([]); setMagicSignals(null); }
    if (mode === 'magic') { setSearchQuery(''); }
  };

  // Filtering Logic â€” uses magic-ranked list when in magic mode
  const baseList = searchMode === 'magic' && magicResults.length > 0
    ? magicResults
    : searchMode === 'magic' && magicQuery.trim() && !magicLoading
      ? [] // query entered but no results
      : candidates;

  const filteredCandidates = baseList.filter(candidate => {
    // 1. Quick-filter search query (only in quick mode)
    const matchSearch = searchMode === 'magic' || (
      candidate.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      candidate.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      candidate.skills_matrix.some(s => s.toLowerCase().includes(searchQuery.toLowerCase())) ||
      candidate.industry_remarks.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // 2. Domain Match
    const matchDomain = selectedDomains.length === 0 || selectedDomains.some(d => {
      const remarks = candidate.industry_remarks.toLowerCase();
      if (d === 'Oil & Gas' && (remarks.includes('petroleum') || remarks.includes('drilling') || remarks.includes('offshore') || remarks.includes('pipeline') || remarks.includes('wellhead') || remarks.includes('hydrocarbon') || remarks.includes('oil') || remarks.includes('gas'))) return true;
      if (d === 'Petrochemical' && (remarks.includes('petrochemical') || remarks.includes('chemical plant') || remarks.includes('distillation') || remarks.includes('cracking') || remarks.includes('feedstock'))) return true;
      if (d === 'Construction & Infrastructure' && (remarks.includes('civil') || remarks.includes('structural') || remarks.includes('mep') || remarks.includes('construction') || remarks.includes('quantity surveyor') || remarks.includes('site engineer'))) return true;
      if (d === 'Energy' && (remarks.includes('renewable') || remarks.includes('solar') || remarks.includes('wind') || remarks.includes('grid') || remarks.includes('power systems') || remarks.includes('energy'))) return true;
      if (d === 'Hospitality' && (remarks.includes('hotel') || remarks.includes('resort') || remarks.includes('barista') || remarks.includes('f&b') || remarks.includes('housekeeping') || remarks.includes('restaurant'))) return true;
      if (d === 'Facilities Management' && (remarks.includes('facilities') || remarks.includes('hvac') || remarks.includes('building maintenance') || remarks.includes('property management') || remarks.includes('fm'))) return true;
      if (d === 'Maritime & Shipping' && (remarks.includes('maritime') || remarks.includes('shipping') || remarks.includes('vessel') || remarks.includes('marine') || remarks.includes('port') || remarks.includes('seafarer'))) return true;
      if (d === 'Power Plants' && (remarks.includes('power plant') || remarks.includes('turbine') || remarks.includes('boiler') || remarks.includes('generator') || remarks.includes('dcs') || remarks.includes('commissioning'))) return true;
      if (d === 'Engineering Services' && (remarks.includes('design engineer') || remarks.includes('application engineer') || remarks.includes('sales engineer') || remarks.includes('mechatronics') || remarks.includes('engineering services'))) return true;
      if (d === 'Manufacturing' && (remarks.includes('manufacturing') || remarks.includes('production') || remarks.includes('quality engineer') || remarks.includes('six sigma') || remarks.includes('lean'))) return true;
      if (d === 'EPC' && (remarks.includes('epc') || remarks.includes('procurement') || remarks.includes('construction engineer') || remarks.includes('engineering procurement'))) return true;
      return false;
    });

    // 3. Specialization Tag Match
    const matchSpec = selectedSpecs.length === 0 || selectedSpecs.some(spec => 
      candidate.specialization_tags.includes(spec) || candidate.skills_matrix.includes(spec.toUpperCase())
    );

    // 4. Match Score Range Match
    const matchScore = candidate.match_score >= minScore && candidate.match_score <= maxScore;

    return matchSearch && matchDomain && matchSpec && matchScore;
  });

  // HTML5 Drag and Drop Handlers for Kanban Workspace
  const handleDragStart = (e: React.DragEvent, id: number) => {
    e.dataTransfer.setData('text/plain', id.toString());
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetStage: HiringStage) => {
    e.preventDefault();
    const idStr = e.dataTransfer.getData('text/plain');
    if (idStr) {
      const candidateId = parseInt(idStr, 10);
      onUpdateCandidateStage(candidateId, targetStage);

      if (targetStage === 'Shortlist' || targetStage === 'Hired') {
        triggerConfettiBlast();
      }
    }
  };

  const triggerConfettiBlast = () => {
    confetti({
      particleCount: 150,
      spread: 80,
      origin: { y: 0.65 },
      colors: ['#bca38b', '#e1d6cc', '#8f7052', '#6e5740']
    });
  };

  // Helper score card styling
  const getScoreColorClass = (score: number) => {
    if (score >= 80) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (score >= 50) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-rose-700 bg-rose-50 border-rose-200';
  };

  const getStageColorClass = (stage: HiringStage) => {
    switch (stage) {
      case 'Screening': return 'bg-slate-100 text-slate-700 border border-slate-200';
      case 'Shortlist': return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
      case 'Interviewing': return 'bg-sky-50 text-sky-700 border border-sky-200';
      case 'Offered': return 'bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/20';
      case 'Hired': return 'bg-teal-50 text-teal-700 border border-teal-200';
      case 'Rejected': return 'bg-rose-50 text-rose-700 border border-rose-200';
    }
  };

  // Empty state
  if (candidates.length === 0) {
    return (
      <div className="empty-state-container">
        <div className="empty-state-icon">
          <Users className="h-10 w-10" />
        </div>
        <h3 className="empty-state-title">No candidates yet</h3>
        <p className="empty-state-desc">
          Your talent directory will populate as you screen CVs or add candidates manually. Upload your first batch to get started.
        </p>
        <button
          onClick={onNavigateToScreener}
          className="btn btn-primary text-sm px-6 py-3 cursor-pointer"
        >
          <FileUp className="h-4 w-4" /> Go to CV Screener
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* View Toolbar Controls */}
      <div className="flex items-center justify-between mb-8 flex-shrink-0 bg-black/[0.015] border border-[var(--border-light)] p-4 rounded-[var(--radius-lg)]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-semibold transition-all border cursor-pointer ${
              viewMode === 'list' 
                ? 'bg-[var(--primary)] text-white border-transparent shadow-lg' 
                : 'text-[var(--text-secondary)] border-transparent hover:bg-black/5'
            }`}
          >
            <Table className="h-4.5 w-4.5" /> List Directory
          </button>
          <button
            onClick={() => setViewMode('kanban')}
            className={`flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-semibold transition-all border cursor-pointer ${
              viewMode === 'kanban' 
                ? 'bg-[var(--primary)] text-white border-transparent shadow-lg' 
                : 'text-[var(--text-secondary)] border-transparent hover:bg-black/5'
            }`}
          >
            <LayoutDashboard className="h-4.5 w-4.5" /> Kanban Pipeline
          </button>
        </div>

        <div className="text-sm text-[var(--text-secondary)] font-medium">
          Found <span className="font-bold text-[var(--text-primary)] text-base">{filteredCandidates.length}</span> candidates
        </div>
      </div>

      {/* Main Split-Panel Layout */}
      <div className="flex flex-1 gap-8 overflow-hidden min-h-0">
        
        {/* Left Sidebar: Faceted Navigation */}
        <div className="faceted-sidebar">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-bold text-lg flex items-center gap-2.5 text-[var(--text-primary)]">
              <SlidersHorizontal className="h-5 w-5 text-[var(--primary)]" />
              Faceted Navigation
            </h3>
            <button 
              onClick={resetFilters}
              className="text-xs text-[var(--primary)] hover:text-[var(--primary)] font-semibold transition-colors cursor-pointer"
            >
              Reset Filters
            </button>
          </div>

          {/* 1. Search Mode Toggle + Search Bar */}
          <div className="mb-8">
            {/* Mode pill switcher */}
            <div className="flex items-center gap-1 p-1 bg-black/[0.04] rounded-[var(--radius-md)] mb-3 border border-[var(--border-light)]">
              <button
                onClick={() => switchMode('quick')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-[var(--radius-sm)] text-xs font-bold transition-all cursor-pointer ${
                  searchMode === 'quick'
                    ? 'bg-white shadow text-[var(--text-primary)] border border-[var(--border-light)]'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                <Search className="h-3.5 w-3.5" /> Quick Filter
              </button>
              <button
                onClick={() => switchMode('magic')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-[var(--radius-sm)] text-xs font-bold transition-all cursor-pointer ${
                  searchMode === 'magic'
                    ? 'bg-[var(--primary)] shadow text-white'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5" /> Magic Search
              </button>
            </div>

            {searchMode === 'quick' ? (
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4.5 w-4.5 text-[var(--text-muted)]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="e.g. React OR Oil"
                  className="w-full bg-black/[0.015] border border-[var(--border-light)] rounded-[var(--radius-md)] pr-4 py-3 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]"
                  style={{ paddingLeft: '44px' }}
                />
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="relative">
                  {magicLoading
                    ? <Loader2 className="absolute left-4 top-1/2 -translate-y-1/2 h-4.5 w-4.5 text-[var(--primary)] animate-spin" />
                    : <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-4.5 w-4.5 text-[var(--primary)]" />
                  }
                  <input
                    type="text"
                    value={magicQuery}
                    onChange={e => handleMagicQueryChange(e.target.value)}
                    placeholder="Describe your ideal candidate..."
                    className="w-full bg-[var(--primary)]/5 border border-[var(--primary)]/30 rounded-[var(--radius-md)] pr-4 py-3 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] placeholder:text-[var(--primary)]/50"
                    style={{ paddingLeft: '44px' }}
                  />
                </div>
                {/* Detected signals */}
                {magicSignals && magicQuery.trim() && (
                  <div className="flex flex-wrap gap-1 px-1">
                    {(magicSignals.skills || []).map(s => (
                      <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 font-semibold">{s}</span>
                    ))}
                    {(magicSignals.domains || []).map(d => (
                      <span key={d} className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/20 font-semibold">{d}</span>
                    ))}
                    {(magicSignals.specs || []).map(s => (
                      <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-semibold">{s}</span>
                    ))}
                    {magicSignals.exp_years != null && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">{magicSignals.exp_years}+ yrs</span>
                    )}
                  </div>
                )}
                {magicQuery.trim() && !magicLoading && (
                  <p className="text-[11px] text-[var(--text-muted)] px-1">
                    {magicResults.length > 0 ? `${magicResults.length} candidates ranked by relevance` : 'No matches found — try different keywords'}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* 2. Target Domain Checkboxes */}
          <div className="mb-8 border-t border-[var(--border-light)] pt-6">
            <span className="faceted-section-title">
              Target Domains
            </span>
            <div className="flex flex-col gap-2">
              {DOMAINS.map(domain => (
                <label key={domain} className="filter-checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedDomains.includes(domain)}
                    onChange={() => handleDomainFilter(domain)}
                    className="filter-checkbox-input"
                  />
                  {domain}
                </label>
              ))}
            </div>
          </div>

          {/* 3. Specialization Badges */}
          <div className="mb-8 border-t border-[var(--border-light)] pt-6">
            <span className="faceted-section-title">
              Specialization
            </span>
            <div className="specialization-tags-grid">
              {SPECIALIZATIONS.map(spec => {
                const isActive = selectedSpecs.includes(spec);
                return (
                  <button
                    key={spec}
                    onClick={() => handleSpecFilter(spec)}
                    className={`specialization-tag-btn ${isActive ? 'active' : ''}`}
                  >
                    {spec}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4. Match Score Range Sliders */}
          <div className="mb-2 border-t border-[var(--border-light)] pt-6">
            <span className="faceted-section-title">
              Match Score Boundaries
            </span>
            <div className="slider-container">
              <div className="slider-group">
                <div className="slider-header">
                  <span className="text-xs font-semibold text-[var(--text-secondary)]">Minimum Match</span>
                  <span className="text-sm font-bold text-[var(--primary)]">{minScore}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={minScore}
                  onChange={e => setMinScore(parseInt(e.target.value, 10))}
                  className="weight-slider w-full"
                />
              </div>

              <div className="slider-group">
                <div className="slider-header">
                  <span className="text-xs font-semibold text-[var(--text-secondary)]">Maximum Match</span>
                  <span className="text-sm font-bold text-[var(--primary)]">{maxScore}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={maxScore}
                  onChange={e => setMaxScore(parseInt(e.target.value, 10))}
                  className="weight-slider w-full"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Main Panel: Directory Visualization */}
        <div className={viewMode === 'kanban' ? 'flex-1 min-h-0 overflow-hidden' : 'flex-1 overflow-y-auto min-h-0 pr-1'}>
          {viewMode === 'list' ? (
            /* LIST VIEW GRID */
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
              {filteredCandidates.map(candidate => (
                <div
                  key={candidate.id}
                  onClick={() => setSelectedCandidate(candidate)}
                  className="candidate-card"
                >
                  <div className="flex-1 flex flex-col justify-start">
                    {/* Header: Name, Score */}
                    <div className="candidate-card-header">
                      <div className="flex flex-col">
                        <h4 className="candidate-card-title">
                          {candidate.full_name}
                        </h4>
                        <span className="candidate-card-subtitle">
                          <Briefcase className="h-3.5 w-3.5 text-[var(--primary)]" /> Exp: {candidate.total_experience_years} Years (Rel: {candidate.relevant_experience_years}y)
                        </span>
                      </div>

                      <span className={`score-badge ${getScoreColorClass(candidate.match_score)} w-12 h-12 rounded-full border flex items-center justify-center font-black text-sm flex-shrink-0`}>
                        {candidate.match_score}
                      </span>
                    </div>

                    {/* Magic Search relevance badge */}
                    {searchMode === 'magic' && (candidate as any).relevance_score !== undefined && (
                      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-[var(--primary)] text-white">
                          <Zap className="h-3 w-3" />
                          {(candidate as any).relevance_score}pts relevance
                        </span>
                        {((candidate as any).matched_signals || []).map((sig: string) => (
                          <span key={sig} className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/20 font-semibold">
                            {sig}
                          </span>
                        ))}
                      </div>
                    )}
                    {/* Industry Remarks Summary */}
                    <p className="candidate-card-remarks line-clamp-3">
                      {candidate.industry_remarks}
                    </p>

                    {/* Skill Badges */}
                    <div className="candidate-card-skills">
                      {candidate.skills_matrix.slice(0, 3).map((skill, i) => (
                        <span key={i} className="candidate-card-skill-badge">
                          {skill}
                        </span>
                      ))}
                      {candidate.skills_matrix.length > 3 && (
                        <span className="text-xs text-[var(--text-muted)] font-bold self-center px-1">
                          +{candidate.skills_matrix.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions & Button Bar */}
                  <div>
                    {/* Metadata line */}
                    <div className="candidate-card-footer">
                      <div className="flex items-center gap-2">
                        <span className="text-[var(--text-muted)]">Added {new Date(candidate.created_at).toLocaleDateString()}</span>
                        <span className="text-slate-700 font-bold">•</span>
                        <span className={`status-pill text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider ${getStageColorClass(candidate.current_stage)}`}>
                          {candidate.current_stage}
                        </span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteCandidate(candidate.id);
                        }}
                        className="text-rose-400/80 hover:text-rose-400 p-1.5 hover:bg-rose-500/10 rounded-md transition-colors cursor-pointer"
                        title="Delete Candidate"
                      >
                        <Trash2 className="h-4.5 w-4.5" />
                      </button>
                    </div>

                    {/* Full width button matching Swiss Chalet style */}
                    <button className="candidate-card-btn">
                      View Profile Details
                    </button>
                  </div>
                </div>
              ))}

              {filteredCandidates.length === 0 && (
                <div className="col-span-3 text-center py-16 glass rounded-[var(--radius-lg)] border border-[var(--border-light)] text-sm text-[var(--text-secondary)]">
                  No candidates match the specified filter facets.
                </div>
              )}
            </div>
          ) : (
            /* KANBAN BOARD VIEW */
            <div
              ref={kanbanRef}
              className="flex gap-6 overflow-x-auto pb-6 h-full items-start cursor-ew-resize"
              style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--border-light) transparent' }}
            >
              {STAGES.map(stage => {
                const stageCandidates = filteredCandidates.filter(c => c.current_stage === stage);
                return (
                  <div
                    key={stage}
                    onDragOver={handleDragOver}
                    onDrop={e => handleDrop(e, stage)}
                    className="w-[300px] flex-shrink-0 flex flex-col max-h-full bg-black/[0.015] border border-[var(--border-light)] rounded-[var(--radius-lg)] p-4"
                  >
                    {/* Column Header */}
                    <div className="flex items-center justify-between mb-4 border-b border-[var(--border-light)] pb-3 flex-shrink-0">
                      <span className="font-bold text-xs text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          stage === 'Shortlist' || stage === 'Hired' ? 'bg-emerald-400' :
                          stage === 'Rejected' ? 'bg-rose-400' : 'bg-[var(--primary)]'
                        }`} />
                        {stage}
                      </span>
                      <span className="text-xs bg-black/5 border border-black/5 px-2.5 py-0.5 rounded-full text-[var(--text-secondary)] font-bold">
                        {stageCandidates.length}
                      </span>
                    </div>

                    {/* Column Cards Container */}
                    <div className="flex-1 flex flex-col gap-3 overflow-y-auto min-h-0 pr-0.5">
                      {stageCandidates.map(candidate => (
                        <div
                           key={candidate.id}
                           draggable
                           onDragStart={e => handleDragStart(e, candidate.id)}
                           onClick={() => setSelectedCandidate(candidate)}
                           className="bg-[var(--bg-surface)] border border-[var(--border-light)] hover:border-[var(--primary)] rounded-[var(--radius-md)] p-4 cursor-grab active:cursor-grabbing transition-all hover:-translate-y-0.5 shadow-md flex flex-col gap-3"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <span className="text-sm font-bold text-[var(--text-primary)] truncate max-w-[150px]" title={candidate.full_name}>
                              {candidate.full_name}
                            </span>
                            <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getScoreColorClass(candidate.match_score)}`}>
                              {candidate.match_score}%
                            </span>
                          </div>

                          <p className="text-xs text-[var(--text-secondary)] leading-relaxed line-clamp-2">
                            {candidate.industry_remarks}
                          </p>

                          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] border-t border-[var(--border-light)] pt-2.5">
                            <span>Exp: {candidate.total_experience_years}y</span>
                            <span className="font-bold text-[var(--text-secondary)]">Rel: {candidate.relevant_experience_years}y</span>
                          </div>
                        </div>
                      ))}

                      {stageCandidates.length === 0 && (
                        <div className="text-center py-8 text-xs text-[var(--text-muted)] border border-dashed border-black/10 rounded-[var(--radius-md)]">
                          Drag CV cards here
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Sliding Side Panel Drawer for Profile Details */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Drawer Backdrop Overlay */}
          <div 
            onClick={() => setSelectedCandidate(null)}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
          />
          
          {/* Main Drawer Panel */}
          <div className="relative w-full max-w-[540px] h-full bg-[var(--bg-surface)] border-l border-[var(--border-light)] shadow-2xl flex flex-col justify-between z-10 animate-fade-in">
            
            {/* Header */}
            <div className="p-6 border-b border-[var(--border-light)] flex items-center justify-between flex-shrink-0 bg-black/[0.01]">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-full bg-[var(--primary-gradient)] flex items-center justify-center font-bold text-white text-xl">
                  {selectedCandidate.full_name.charAt(0)}
                </div>
                <div className="flex flex-col">
                  <h3 className="font-bold text-lg text-[var(--text-primary)]">{selectedCandidate.full_name}</h3>
                  <span className={`status-pill text-xs self-start px-2.5 py-0.5 rounded-full mt-1.5 ${getStageColorClass(selectedCandidate.current_stage)}`}>
                    {selectedCandidate.current_stage}
                  </span>
                </div>
              </div>
              <button 
                onClick={() => setSelectedCandidate(null)}
                className="p-1.5 rounded-full hover:bg-black/5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="p-6 flex-1 overflow-y-auto flex flex-col gap-6">
              
              {/* Score Indicator */}
              <div className="bg-black/[0.015] border border-[var(--border-light)] rounded-[var(--radius-lg)] p-6 flex items-center justify-between gap-4">
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Evaluation Score</span>
                  <span className="text-4xl font-black text-[var(--text-primary)]">{selectedCandidate.match_score}%</span>
                  <span className="text-xs text-[var(--text-muted)]">Fitted for target domain</span>
                </div>
                
                {/* SVG Progress Circle */}
                <div className="relative w-20 h-20">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="40" cy="40" r="34" className="stroke-black/5 fill-none" strokeWidth="5" />
                    <circle 
                      cx="40" cy="40" r="34" 
                      className={`fill-none stroke-current ${
                        selectedCandidate.match_score >= 80 ? 'text-emerald-600' :
                        selectedCandidate.match_score >= 50 ? 'text-amber-600' : 'text-rose-600'
                      }`}
                      strokeWidth="5"
                      strokeDasharray={`${2 * Math.PI * 34}`}
                      strokeDashoffset={`${2 * Math.PI * 34 * (1 - selectedCandidate.match_score / 100)}`}
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-[var(--text-primary)]">
                    MATCH
                  </span>
                </div>
              </div>

              {/* Contact Tokens */}
              <div className="flex flex-col gap-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <User className="h-4 w-4 text-[var(--primary)]" /> Contact Tokens
                </h4>
                <div className="grid grid-cols-1 gap-3 bg-black/[0.01] border border-[var(--border-light)] p-4 rounded-[var(--radius-md)] text-sm">
                  <div className="flex items-center gap-3 text-[var(--text-secondary)]">
                    <Mail className="h-4.5 w-4.5 text-[var(--text-muted)] flex-shrink-0" />
                    <span className="truncate text-[var(--text-primary)]">{selectedCandidate.email}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[var(--text-secondary)]">
                    <Phone className="h-4.5 w-4.5 text-[var(--text-muted)] flex-shrink-0" />
                    <span className="text-[var(--text-primary)]">{selectedCandidate.phone}</span>
                  </div>
                  {selectedCandidate.passport_number && (
                    <div className="flex items-center gap-3 text-[var(--text-secondary)]">
                      <Shield className="h-4.5 w-4.5 text-[var(--text-muted)] flex-shrink-0" />
                      <span className="text-[var(--text-primary)] font-mono">Passport: {selectedCandidate.passport_number}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Download CV â€” only shown when a file was uploaded to backend */}
              {selectedCandidate.cv_file_name && (
                <div className="flex flex-col gap-3">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Download className="h-4 w-4 text-[var(--primary)]" /> Original CV File
                  </h4>
                  <a
                    href={`http://localhost:5000/api/v1/cv/${selectedCandidate.cv_file_name}`}
                    download
                    className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-[var(--radius-md)] border border-[var(--primary)]/40 bg-[var(--primary)]/5 text-[var(--primary)] text-sm font-semibold hover:bg-[var(--primary)]/10 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Download {selectedCandidate.cv_file_name.replace(/^[a-f0-9]{8}_/, '')}
                  </a>
                </div>
              )}

              {/* Experience Alignment */}
              <div className="flex flex-col gap-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-[var(--primary)]" /> Experience Alignment
                </h4>
                <div className="bg-black/[0.01] border border-[var(--border-light)] p-4.5 rounded-[var(--radius-md)] flex flex-col gap-3.5">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--text-secondary)]">Total Workforce:</span>
                    <span className="font-bold text-[var(--text-primary)]">{selectedCandidate.total_experience_years} Years</span>
                  </div>
                  <div className="flex justify-between items-center text-sm border-t border-[var(--border-light)] pt-3">
                    <span className="text-[var(--text-secondary)] font-semibold">Target Domain Match:</span>
                    <span className="font-bold text-[var(--primary)]">{selectedCandidate.relevant_experience_years} Years</span>
                  </div>
                </div>
              </div>

              {/* Context Validation Remarks */}
              <div className="flex flex-col gap-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Award className="h-4.5 w-4.5 text-[var(--primary)]" /> Domain Remarks Summary
                </h4>
                <div className="bg-[var(--primary)]/5 border border-[var(--primary)]/20 text-sm text-[var(--text-secondary)] leading-relaxed p-4.5 rounded-[var(--radius-md)]">
                  {selectedCandidate.industry_remarks}
                </div>
              </div>

              {/* Skills Matrix */}
              <div className="flex flex-col gap-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <SlidersHorizontal className="h-4 w-4 text-[var(--primary)]" /> Extracted Skills Matrix
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedCandidate.skills_matrix.map((skill, i) => (
                    <span key={i} className="text-xs bg-black/5 border border-black/10 px-3.5 py-1.5 rounded-full text-[var(--text-primary)] font-medium">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Specialization Tags */}
              {selectedCandidate.specialization_tags.length > 0 && (
                <div className="flex flex-col gap-3">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Specialization
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedCandidate.specialization_tags.map((tag, i) => (
                      <span key={i} className="text-xs bg-[var(--primary)]/10 border border-[var(--primary)]/30 px-3 py-1.5 rounded text-[var(--primary)] font-bold">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer stage actions */}
            <div className="p-4 pb-6 border-t border-[var(--border-light)] bg-black/[0.01] flex items-center gap-3 flex-shrink-0 overflow-hidden">
              <span className="text-xs font-bold text-slate-400 uppercase w-14">Move:</span>
              <div className="flex-1 flex gap-2 overflow-x-auto py-1.5">
                {STAGES.filter(s => s !== selectedCandidate.current_stage).map(stage => (
                  <button
                    key={stage}
                    onClick={() => {
                      onUpdateCandidateStage(selectedCandidate.id, stage);
                      if (stage === 'Shortlist' || stage === 'Hired') {
                        triggerConfettiBlast();
                      }
                      setSelectedCandidate(prev => prev ? { ...prev, current_stage: stage } : null);
                    }}
                    className="text-xs font-bold px-3 py-1.5 rounded bg-black/5 border border-black/10 hover:border-[var(--primary)] text-[var(--text-primary)] hover:text-[var(--primary)] whitespace-nowrap transition-all cursor-pointer"
                  >
                    {stage}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

