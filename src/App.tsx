import React, { useState, useEffect, useCallback } from 'react';
import { 
  Building2, Users, FileUp, ClipboardList, BarChart3, Plus, 
  MapPin, Database, Layers, CheckCircle2, ArrowRight, Trash2,
  AlertTriangle, TrendingUp, Clock, Target, LogOut, UserCog,
  Key, Lock, X as XIcon, AlertCircle, Pencil, Moon, Sun
} from 'lucide-react';
import { Requisition, Candidate, HiringStage, TargetDomain } from './types';
import { BulkUploadQueue } from './components/BulkUploadQueue';
import { CandidateDirectory } from './components/CandidateDirectory';
import { ExcelExporter } from './components/ExcelExporter';
import { LoginPage } from './components/LoginPage';
import { UserManagement } from './components/UserManagement';
import { createApiFetch } from './lib/apiFetch';

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

// ── Dark mode hook ────────────────────────────────────────────────
function useTheme() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    const stored = localStorage.getItem('hireengine_theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('hireengine_theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  const toggle = useCallback(() => setIsDark(d => !d), []);
  return { isDark, toggle };
}

const STAGES: HiringStage[] = ['Screening', 'Shortlist', 'Interviewing', 'Offered', 'Hired', 'Rejected'];

function App() {
  // ── Theme ─────────────────────────────────────────────────────
  const { isDark, toggle: toggleTheme } = useTheme();
  const [authToken, setAuthToken] = useState<string | null>(() => localStorage.getItem('hireengine_token'));
  const [authUser, setAuthUser] = useState<{ name: string; role: string; email: string; tenant_id?: string; is_super_admin?: boolean } | null>(() => {
    try { return JSON.parse(localStorage.getItem('hireengine_user') || 'null'); } catch { return null; }
  });

  // ── Custom Routing ───────────────────────────────────────────
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = useCallback((path: string) => {
    if (window.location.pathname !== path) {
      window.history.pushState(null, '', path);
      setCurrentPath(path);
    }
  }, []);

  const handleLogin = (token: string, user: { name: string; role: string; email: string }) => {
    localStorage.setItem('hireengine_token', token);
    localStorage.setItem('hireengine_user', JSON.stringify(user));
    setAuthToken(token);
    setAuthUser(user);
    navigate('/dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('hireengine_token');
    localStorage.removeItem('hireengine_user');
    setAuthToken(null);
    setAuthUser(null);
    navigate('/login');
  };

  // Hook definitions completed, authentication check moved below to satisfy Hook order rules
  // ─────────────────────────────────────────────────────────────

  const isAuthenticated = !!(authToken && authUser);

  useEffect(() => {
    if (!isAuthenticated) {
      if (currentPath !== '/login') {
        navigate('/login');
      }
    } else {
      if (currentPath === '/' || currentPath === '/login' || !currentPath.startsWith('/dashboard')) {
        navigate('/dashboard');
      }
    }
  }, [isAuthenticated, currentPath, navigate]);

  const activeTab = React.useMemo(() => {
    if (currentPath.startsWith('/dashboard/screener')) return 'screener';
    if (currentPath.startsWith('/dashboard/directory')) return 'directory';
    if (currentPath.startsWith('/dashboard/requisitions')) return 'requisitions';
    if (currentPath.startsWith('/dashboard/users')) return 'users';
    return 'dashboard';
  }, [currentPath]);

  // Directory filter — set by clicking metric cards or pipeline rows in the dashboard
  const [directoryFilter, setDirectoryFilter] = React.useState<{ status?: string; filter?: string } | null>(null);

  const setActiveTab = useCallback((tab: 'dashboard' | 'screener' | 'directory' | 'requisitions' | 'users') => {
    if (tab === 'dashboard') {
      navigate('/dashboard');
    } else {
      navigate(`/dashboard/${tab}`);
    }
    // Clear directory filter when switching away from directory
    if (tab !== 'directory') setDirectoryFilter(null);
  }, [navigate, setDirectoryFilter]);

  /** Navigate to the Talent Directory with an optional pre-applied filter. */
  const navigateToDirectory = useCallback((filter?: { status?: string; filter?: string } | null) => {
    setDirectoryFilter(filter ?? null);
    navigate('/dashboard/directory');
  }, [navigate, setDirectoryFilter]);

  // Create authenticated apiFetch helper that auto-logs out on 401
  const apiFetch = React.useMemo(() => {
    return authToken ? createApiFetch(authToken, handleLogout) : null;
  }, [authToken]);

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters.');
      return;
    }
    if (!apiFetch) return;
    setChangingPassword(true);
    try {
      const res = await apiFetch('/api/v1/auth/change-password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      });
      const data = await res.json();
      if (!res.ok) {
        setPasswordError(data.error || 'Failed to change password.');
      } else {
        setPasswordSuccess('Password successfully updated!');
        setOldPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setTimeout(() => {
          setShowPasswordModal(false);
          setPasswordSuccess('');
        }, 1500);
      }
    } catch (err) {
      setPasswordError('Network error while changing password.');
    } finally {
      setChangingPassword(false);
    }
  };

  // Persisted UI state
  const [activeReqId, setActiveReqId] = useLocalStorage<number>('hireengine_active_req', 101);

  // Backend database state
  const [requisitions, setRequisitions] = useState<Requisition[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  // Fetch initial data from backend database (must send auth token for tenant scoping)
  useEffect(() => {
    if (!authToken || !apiFetch) return;
    setDataLoading(true);
    Promise.all([
      apiFetch('/api/v1/requisitions').then(res => res.json()),
      apiFetch('/api/v1/candidates').then(res => res.json())
    ])
      .then(([reqData, candData]) => {
        if (Array.isArray(reqData)) setRequisitions(reqData);
        if (Array.isArray(candData)) setCandidates(candData);
      })
      .catch(() => {
        console.error('Failed to load initial database state.');
      })
      .finally(() => {
        setDataLoading(false);
      });
  }, [authToken, apiFetch]);

  // Persisted upload queue â€” in-flight items are reset to 'failed' on reload
  const [queue, setQueue] = useLocalStorage<import('./types').QueueItem[]>('hireengine_queue', []);
  // Reset any stuck in-progress items from a previous session and scrub stale malformed records
  const queueInitialized = React.useRef(false);
  React.useEffect(() => {
    if (!queueInitialized.current) {
      queueInitialized.current = true;
      // Generic section-header strings that the old name parser incorrectly captured
      const GARBLED_NAMES = new Set([
        'PERSONAL DETAILS', 'PERSONAL INFORMATION', 'PROFESSIONAL SUMMARY', 'CAREER SUMMARY',
        'ELECTRICAL ENGINEER', 'MECHANICAL ENGINEER', 'CIVIL ENGINEER', 'PROCESS ENGINEER',
        'PROFESSIONAL PROFILE', 'CURRICULUM VITAE', 'CONTACT DETAILS', 'ABOUT ME',
        'CAREER OBJECTIVE', 'OBJECTIVE', 'SUMMARY', 'PROFILE', 'INTRODUCTION',
        'FULL NAME', 'NAME', 'CANDIDATE', 'APPLICANT',
      ]);
      setQueue(prev => prev
        .filter(item => {
          // Drop stale completed items whose name is a garbled CV section header
          if (item.status === 'completed' && item.parsedData?.full_name) {
            const n = item.parsedData.full_name.trim().toUpperCase();
            if (GARBLED_NAMES.has(n)) return false;
          }
          return true;
        })
        .map(item =>
          ['pending', 'extracting', 'scoring'].includes(item.status)
            ? { ...item, status: 'failed' as const, error: 'Interrupted by page refresh' }
            : item
        )
      );
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Toast state
  const [toasts, setToasts] = useState<{ id: string; message: string; type: 'success' | 'info' | 'warning' | 'error' }[]>([]);

  // Clear all confirm modal
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // Requisition delete confirm modal
  const [deleteReqTarget, setDeleteReqTarget] = useState<Requisition | null>(null);

  // Requisition edit modal state
  const [editReqTarget, setEditReqTarget] = useState<Requisition | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editDomain, setEditDomain] = useState<TargetDomain | ''>('');
  const [editDesc, setEditDesc] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  const openEditReq = (req: Requisition) => {
    setEditReqTarget(req);
    setEditTitle(req.job_title);
    setEditLocation(req.location);
    setEditDomain(req.target_domain as TargetDomain);
    setEditDesc(req.job_description_text);
  };

  const closeEditReq = () => {
    setEditReqTarget(null);
    setEditTitle('');
    setEditLocation('');
    setEditDomain('');
    setEditDesc('');
  };

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
  const [newDomain, setNewDomain] = useState<TargetDomain | ''>('');
  const [newDesc, setNewDesc] = useState('');

  const handleCreateRequisition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDesc.trim()) {
      addToast('Please provide a Job Title and Job Description.', 'error');
      return;
    }
    if (!apiFetch) return;
    try {
      const res = await apiFetch('/api/v1/requisitions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: newTitle.trim(),
          location: newLocation.trim() || 'Not specified',
          target_domain: (newDomain as TargetDomain) || 'Engineering Services',
          job_description_text: newDesc.trim()
        })
      });
      if (!res.ok) throw new Error('Failed to create requisition');
      const newReq: Requisition = await res.json();
      setRequisitions(prev => [newReq, ...prev]);
      setActiveReqId(newReq.id);
      addToast(`Job requisition "${newReq.job_title}" created & set as active.`, 'success');
      setNewTitle('');
      setNewLocation('');
      setNewDomain('');
      setNewDesc('');
    } catch (err) {
      addToast('Failed to create job requisition on server.', 'error');
    }
  };

  const handleDeleteRequisition = async (reqId: number) => {
    const req = requisitions.find(r => r.id === reqId);
    const cascadeCount = candidates.filter(c => c.requisition_id === reqId).length;
    if (!apiFetch) return;
    try {
      await apiFetch(`/api/v1/requisitions/${reqId}`, { method: 'DELETE' });
      setCandidates(prev => prev.filter(c => c.requisition_id !== reqId));
      setRequisitions(prev => prev.filter(r => r.id !== reqId));
      addToast(`"${req?.job_title}" deleted. ${cascadeCount > 0 ? `${cascadeCount} associated candidate(s) removed.` : ''}`, 'warning');
    } catch (err) {
      addToast('Failed to delete requisition on server.', 'error');
    }
  };

  const handleUpdateRequisition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editReqTarget || !editTitle.trim() || !editDesc.trim()) return;
    setEditSaving(true);
    if (!apiFetch) return;
    try {
      const res = await apiFetch(`/api/v1/requisitions/${editReqTarget.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: editTitle.trim(),
          location: editLocation.trim() || 'Not specified',
          target_domain: editDomain || editReqTarget.target_domain,
          job_description_text: editDesc.trim()
        })
      });
      if (!res.ok) throw new Error('Failed to update requisition');
      const updated: Requisition = await res.json();
      setRequisitions(prev => prev.map(r => r.id === updated.id ? updated : r));
      addToast(`Requisition "${updated.job_title}" updated successfully.`, 'success');
      closeEditReq();
    } catch (err) {
      addToast('Failed to update requisition on server.', 'error');
    } finally {
      setEditSaving(false);
    }
  };

  // Candidate actions
  const handleUpdateCandidateStage = async (id: number, stage: HiringStage) => {
    setCandidates(prev => prev.map(c => c.id === id ? { ...c, current_stage: stage } : c));
    const cand = candidates.find(c => c.id === id);
    addToast(`${cand?.full_name} moved to "${stage}".`, 'info');
    if (!apiFetch) return;
    try {
      await apiFetch(`/api/v1/candidates/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_stage: stage })
      });
    } catch (err) {
      addToast('Failed to save stage change to server.', 'error');
    }
  };

  const handleDeleteCandidate = async (id: number) => {
    setCandidates(prev => prev.filter(c => c.id !== id));
    addToast('Candidate record deleted.', 'warning');
    if (!apiFetch) return;
    try {
      await apiFetch(`/api/v1/candidates/${id}`, { method: 'DELETE' });
    } catch (err) {
      addToast('Failed to delete candidate on server.', 'error');
    }
  };

  const handleCandidatesParsed = async (newCandidates: Candidate[], isRescreen: boolean = false) => {
    if (!apiFetch) return;
    try {
      for (const cand of newCandidates) {
        await apiFetch('/api/v1/candidates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cand)
        });
      }
      const res = await apiFetch('/api/v1/candidates');
      const updated: Candidate[] = await res.json();
      setCandidates(updated);
      addToast(
        isRescreen 
          ? `Re-screened ${newCandidates.length} candidate(s) against active requisition.`
          : `Successfully screened ${newCandidates.length} candidate CV(s).`, 
        'success'
      );
    } catch (err) {
      addToast('Error saving candidates to server.', 'error');
    }
  };

  const handleClearAllCandidates = async () => {
    if (!apiFetch) return;
    try {
      await apiFetch(`/api/v1/candidates/clear?req_id=${activeReqId}`, { method: 'DELETE' });
      setCandidates(prev => prev.filter(c => c.requisition_id !== activeReqId));
      setShowClearConfirm(false);
      addToast('All candidate records cleared from the active requisition.', 'warning');
    } catch (err) {
      addToast('Failed to clear candidates on server.', 'error');
    }
  };

  // Dashboard calculations â€” real data
  // Dashboard calculations â€” scoped to the active requisition
  const activeCandidates = candidates.filter(c => c.requisition_id === activeReqId);
  const totalCVs = activeCandidates.length;
  const avgScore = totalCVs > 0 ? Math.round(activeCandidates.reduce((sum, c) => sum + c.match_score, 0) / totalCVs) : 0;
  const shortlistedCount = activeCandidates.filter(c => c.current_stage === 'Shortlist' || c.current_stage === 'Hired' || c.current_stage === 'Offered' || c.current_stage === 'Interviewing').length;
  const pendingScreen = activeCandidates.filter(c => c.current_stage === 'Screening').length;
  const rejectedCount = activeCandidates.filter(c => c.current_stage === 'Rejected').length;

  const oneWeekAgo = new Date(Date.now() - 86400000 * 7).toISOString();
  const newThisWeek = activeCandidates.filter(c => c.created_at >= oneWeekAgo).length;

  const domainStats = activeCandidates.reduce((acc, c) => {
    const reqObj = requisitions.find(r => r.id === c.requisition_id);
    const domainName = reqObj?.target_domain || 'General';
    acc[domainName] = (acc[domainName] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const stageStats = STAGES.reduce((acc, stage) => {
    acc[stage] = activeCandidates.filter(c => c.current_stage === stage).length;
    return acc;
  }, {} as Record<HiringStage, number>);

  const highMatchCount = activeCandidates.filter(c => c.match_score >= 80).length;

  // Show login page if not authenticated
  if (!isAuthenticated) {
    if (currentPath === '/login') {
      return <LoginPage onLogin={handleLogin} />;
    }
    return <div className="flex h-screen w-screen items-center justify-center bg-[var(--bg-app)] text-[var(--text-muted)] text-sm">Redirecting to login...</div>;
  }

  // Redirecting state to prevent flash of layout on root landing or login page when authenticated
  if (currentPath === '/' || currentPath === '/login') {
    return <div className="flex h-screen w-screen items-center justify-center bg-[var(--bg-app)] text-[var(--text-muted)] text-sm">Redirecting to dashboard...</div>;
  }

  return (
    <div 
      className="app-container"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => e.preventDefault()}
    >
      
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

      {/* Delete Requisition Confirm Modal */}
      {deleteReqTarget && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setDeleteReqTarget(null)} />
          <div className="relative bg-[var(--bg-surface)] border border-[var(--border-light)] rounded-[var(--radius-lg)] p-8 max-w-sm w-full mx-4 shadow-2xl animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-rose-500/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-rose-500" />
              </div>
              <div>
                <h3 className="font-bold text-base text-[var(--text-primary)]">Delete Requisition?</h3>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-6 leading-relaxed">
              This will permanently delete <strong>"{deleteReqTarget.job_title}"</strong> and <strong>{candidates.filter(c => c.requisition_id === deleteReqTarget.id).length}</strong> associated candidate(s).
            </p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteReqTarget(null)} className="flex-1 btn btn-secondary text-sm py-2.5 cursor-pointer">Cancel</button>
              <button
                onClick={() => { handleDeleteRequisition(deleteReqTarget.id); setDeleteReqTarget(null); }}
                className="flex-1 btn text-sm py-2.5 cursor-pointer bg-rose-500 text-white hover:bg-rose-600 border-transparent"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Requisition Modal */}
      {editReqTarget && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeEditReq} />
          <div className="relative bg-[var(--bg-surface)] border border-[var(--border-light)] rounded-[var(--radius-lg)] w-full max-w-lg mx-4 shadow-2xl animate-fade-in overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-7 py-5 border-b border-[var(--border-light)] bg-black/[0.01]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-[var(--primary)]/10">
                  <Pencil className="h-4 w-4 text-[var(--primary)]" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-[var(--text-primary)]">Edit Requisition</h3>
                  <p className="text-xs text-[var(--text-muted)]">Update job details and description</p>
                </div>
              </div>
              <button type="button" onClick={closeEditReq} className="p-1.5 rounded-full hover:bg-black/5 text-[var(--text-muted)] cursor-pointer transition-colors">
                <XIcon className="h-5 w-5" />
              </button>
            </div>
            {/* Modal Body */}
            <form onSubmit={handleUpdateRequisition} className="p-7 flex flex-col gap-5">
              <div>
                <label className="form-label">Job Title</label>
                <input
                  type="text" required value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  placeholder="e.g. Lead Refinery Superintendent"
                  className="form-input text-sm"
                />
              </div>
              <div>
                <label className="form-label">Location <span className="text-[var(--text-muted)] font-normal">(optional)</span></label>
                <input
                  type="text" value={editLocation}
                  onChange={e => setEditLocation(e.target.value)}
                  placeholder="e.g. Houston, US"
                  className="form-input text-sm"
                />
              </div>
              <div>
                <label className="form-label">Industry Domain</label>
                <select value={editDomain} onChange={e => setEditDomain(e.target.value as TargetDomain)} className="form-select text-sm">
                  <option value="Oil &amp; Gas">Oil &amp; Gas</option>
                  <option value="Petrochemical">Petrochemical</option>
                  <option value="Construction &amp; Infrastructure">Construction &amp; Infrastructure</option>
                  <option value="Energy">Energy</option>
                  <option value="Hospitality">Hospitality</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Facilities Management">Facilities Management</option>
                  <option value="Maritime &amp; Shipping">Maritime &amp; Shipping</option>
                  <option value="Power Plants">Power Plants</option>
                  <option value="Engineering Services">Engineering Services</option>
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="EPC">EPC</option>
                </select>
              </div>
              <div>
                <label className="form-label">Job Description <span className="text-[var(--primary)] font-semibold text-[10px]">(primary matching signal)</span></label>
                <textarea
                  required rows={5} value={editDesc}
                  onChange={e => setEditDesc(e.target.value)}
                  placeholder="Paste the full job description here..."
                  className="form-textarea text-sm"
                />
              </div>
              <div className="flex gap-3 pt-1 border-t border-[var(--border-light)]">
                <button type="button" onClick={closeEditReq} className="flex-1 btn btn-secondary text-sm py-2.5 cursor-pointer">Cancel</button>
                <button
                  type="submit"
                  disabled={editSaving || !editTitle.trim() || !editDesc.trim()}
                  className="flex-1 btn btn-primary text-sm py-2.5 cursor-pointer disabled:opacity-50"
                >
                  {editSaving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Left Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo select-none">
            <span className="logo-icon">⚡</span>
            Hirengine AI
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
          {authUser.role === 'Admin' && (
            <button onClick={() => setActiveTab('users')} className={`nav-item ${activeTab === 'users' ? 'active' : ''}`}>
              <UserCog className="h-4 w-4" /> User Management
            </button>
          )}

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
          <div className="user-avatar">
            {authUser.name.split(' ').map((n: string) => n[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div className="user-info" style={{ flex: 1, minWidth: 0 }}>
            <span className="user-name" title={authUser.name}>{authUser.name}</span>
            <span className="user-role">{authUser.role}</span>
          </div>
          <button
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="flex-shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors cursor-pointer"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark
              ? <Sun className="h-4 w-4" />
              : <Moon className="h-4 w-4" />}
          </button>
          <button
            onClick={() => {
              setPasswordError('');
              setPasswordSuccess('');
              setOldPassword('');
              setNewPassword('');
              setConfirmPassword('');
              setShowPasswordModal(true);
            }}
            title="Change Password"
            className="flex-shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors cursor-pointer"
            aria-label="Change Password"
          >
            <Key className="h-4 w-4" />
          </button>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="flex-shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer"
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
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
            {activeTab === 'users' && 'User Management'}
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

          {/* â”€â”€ TAB 1: DASHBOARD â”€â”€ */}
          {activeTab === 'dashboard' && (
            <div className="animate-fade-in">

              {candidates.length === 0 ? (
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
                    <div
                      className="stat-card glass primary cursor-pointer hover:border-[var(--primary)]/50 hover:shadow-lg transition-all duration-200"
                      onClick={() => navigateToDirectory()}
                      title="View all candidates"
                    >
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

                    <div
                      className="stat-card glass warning cursor-pointer hover:border-amber-300/60 hover:shadow-lg transition-all duration-200"
                      onClick={() => navigateToDirectory({ filter: 'active' })}
                      title="View active pipeline candidates"
                    >
                      <div className="stat-header">
                        <span>In Active Pipeline</span>
                        <div className="stat-icon-wrapper"><Users className="h-4 w-4" /></div>
                      </div>
                      <div className="stat-value">{shortlistedCount}</div>
                      <div className="stat-footer">
                        <span>{highMatchCount} high-match (80%+)</span>
                      </div>
                    </div>

                    <div
                      className="stat-card glass info cursor-pointer hover:border-sky-300/60 hover:shadow-lg transition-all duration-200"
                      onClick={() => navigateToDirectory({ status: 'screening' })}
                      title="View candidates pending screening"
                    >
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
                          const stageBg: Record<HiringStage, string> = {
                            'Screening': 'hover:bg-slate-50',
                            'Shortlist': 'hover:bg-emerald-50/60',
                            'Interviewing': 'hover:bg-sky-50/60',
                            'Offered': 'hover:bg-[var(--primary-glow)]',
                            'Hired': 'hover:bg-teal-50/60',
                            'Rejected': 'hover:bg-rose-50/60',
                          };
                          return (
                            <div
                              key={stage}
                              className={`flex items-center gap-3 px-2 py-1.5 rounded-lg cursor-pointer transition-colors duration-150 ${stageBg[stage]} group`}
                              onClick={() => navigateToDirectory({ status: stage.toLowerCase() })}
                              title={`View ${stage} candidates`}
                            >
                              <span className="text-xs font-semibold text-[var(--text-secondary)] w-24 flex-shrink-0 group-hover:text-[var(--text-primary)] transition-colors">{stage}</span>
                              <div className="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-700 ${stageColor[stage]}`} style={{ width: `${pct}%` }} />
                              </div>
                              <span className="text-xs font-bold text-[var(--text-primary)] w-6 text-right">{count}</span>
                              <ArrowRight className="h-3 w-3 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
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
                          { label: 'High Match (80-100)', count: activeCandidates.filter(c => c.match_score >= 80).length, color: 'bg-emerald-500' },
                          { label: 'Mid Match (50-79)', count: activeCandidates.filter(c => c.match_score >= 50 && c.match_score < 80).length, color: 'bg-amber-500' },
                          { label: 'Low Match (0-49)', count: activeCandidates.filter(c => c.match_score < 50).length, color: 'bg-rose-400' },
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
                            activeCandidates.forEach(c => c.skills_matrix.forEach(s => { skillMap[s] = (skillMap[s] || 0) + 1; }));
                            return Object.entries(skillMap).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([skill, count]) => (
                              <span key={skill} className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/20">
                                {skill} <span className="opacity-60">Ã—{count}</span>
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
          {activeTab === 'screener' && apiFetch && (
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
                  queue={queue}
                  setQueue={setQueue}
                  apiFetch={apiFetch}
                />
              </div>
            </div>
          )}

          {/* ── TAB 3: DIRECTORY ── */}
          {activeTab === 'directory' && apiFetch && (
            <div className="h-full overflow-hidden">
              <CandidateDirectory 
                candidates={candidates}
                requisitions={requisitions}
                onUpdateCandidateStage={handleUpdateCandidateStage}
                onDeleteCandidate={handleDeleteCandidate}
                onNavigateToScreener={() => setActiveTab('screener')}
                initialFilter={directoryFilter}
                apiFetch={apiFetch}
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
                    <label className="form-label">Location <span className="text-[var(--text-muted)] font-normal">(optional)</span></label>
                    <input
                      type="text" value={newLocation}
                      onChange={e => setNewLocation(e.target.value)}
                      placeholder="e.g. Houston, US"
                      className="form-input text-sm"
                    />
                  </div>
                  <div>
                    <label className="form-label">Industry Domain <span className="text-[var(--text-muted)] font-normal">(optional)</span></label>
                    <select value={newDomain} onChange={e => setNewDomain(e.target.value as any)} className="form-select text-sm">
                      <option value="">Auto-detect from Job Description</option>
                      <option value="Oil & Gas">Oil & Gas</option>
                      <option value="Petrochemical">Petrochemical</option>
                      <option value="Construction & Infrastructure">Construction & Infrastructure</option>
                      <option value="Energy">Energy</option>
                      <option value="Hospitality">Hospitality</option>
                      <option value="Healthcare">Healthcare</option>
                      <option value="Facilities Management">Facilities Management</option>
                      <option value="Maritime & Shipping">Maritime & Shipping</option>
                      <option value="Power Plants">Power Plants</option>
                      <option value="Engineering Services">Engineering Services</option>
                      <option value="Manufacturing">Manufacturing</option>
                      <option value="EPC">EPC</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Job Description <span className="text-[var(--primary)] font-semibold text-[10px]">(primary matching signal)</span></label>
                    <textarea
                      required rows={6} value={newDesc}
                      onChange={e => setNewDesc(e.target.value)}
                      placeholder="Paste the full job description here. Candidate match scores are calculated primarily by aligning CV content against these keywords and requirements..."
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
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => openEditReq(req)}
                                className="text-[var(--text-muted)] hover:text-[var(--primary)] p-1.5 hover:bg-[var(--primary)]/10 rounded-md transition-colors cursor-pointer"
                                title="Edit Requisition"
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => setDeleteReqTarget(req)}
                                className="text-rose-400/70 hover:text-rose-500 p-1.5 hover:bg-rose-50 rounded-md transition-colors cursor-pointer"
                                title="Delete Requisition"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── TAB 5: USER MANAGEMENT ── */}
          {activeTab === 'users' && authUser.role === 'Admin' && apiFetch && (
            <UserManagement
              apiFetch={apiFetch}
              currentUserEmail={authUser.email}
            />
          )}

        </div>
      </main>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white rounded-[var(--radius-lg)] shadow-xl border border-slate-200 w-full max-w-md overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                  <Key className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-slate-800">Change Password</h3>
                  <p className="text-xs text-slate-500">Update security credentials for your account</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowPasswordModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <XIcon className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleChangePassword} className="p-5 flex flex-col gap-4">
              {passwordError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-xs font-semibold text-rose-600">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{passwordError}</span>
                </div>
              )}
              {passwordSuccess && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-xs font-semibold text-emerald-600">
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                  <span>{passwordSuccess}</span>
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase">Current Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={oldPassword}
                    onChange={e => setOldPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-[var(--primary)]"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase">New Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-[var(--primary)]"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase">Confirm New Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-[var(--primary)]"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 mt-2">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold border border-slate-300 text-slate-600 hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={changingPassword || !oldPassword || !newPassword || !confirmPassword}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-white hover:bg-[var(--primary)]/90 disabled:opacity-50 cursor-pointer"
                >
                  {changingPassword ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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


