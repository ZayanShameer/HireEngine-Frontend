import React, { useState, useEffect } from 'react';
import {
  UserPlus, Trash2, RefreshCw, Shield, User, Mail, KeyRound,
  CheckCircle2, AlertCircle, Loader2, Crown, Users, Eye, EyeOff
} from 'lucide-react';

interface UserRecord {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface UserManagementProps {
  apiFetch: import('../lib/apiFetch').ApiFetch;
  currentUserEmail: string;
}

const ROLE_OPTIONS = ['Admin', 'Recruiter', 'Hiring Manager', 'Viewer'];

const ROLE_COLORS: Record<string, string> = {
  Admin:           'bg-[var(--primary-glow)] text-[var(--primary)] border-[var(--primary)]/30',
  Recruiter:       'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Hiring Manager':'bg-sky-50 text-sky-700 border-sky-200',
  Viewer:          'bg-slate-100 text-slate-600 border-slate-200',
};

export function UserManagement({ apiFetch, currentUserEmail }: UserManagementProps) {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Add-user form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('Recruiter');
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiFetch('/api/v1/auth/users');
      if (!res.ok) throw new Error((await res.json()).error || 'Failed to load users');
      const data = await res.json();
      setUsers(data.users);
    } catch (e: any) {
      setError(e.message || 'Could not reach the server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    if (!name.trim() || !email.trim() || !password) {
      setFormError('All fields are required.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFormError('Enter a valid email address.');
      return;
    }
    if (password.length < 6) {
      setFormError('Password must be at least 6 characters.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await apiFetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), email: email.trim().toLowerCase(), password, role }),
      });
      const data = await res.json();
      if (!res.ok) { setFormError(data.error || 'Registration failed.'); return; }
      setFormSuccess(`User "${name.trim()}" added successfully.`);
      setName(''); setEmail(''); setPassword(''); setRole('Recruiter');
      fetchUsers();
      setTimeout(() => setFormSuccess(''), 4000);
    } catch {
      setFormError('Cannot reach the server.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      const res = await apiFetch(`/api/v1/auth/users/${userId}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const d = await res.json();
        alert(d.error || 'Delete failed.');
        return;
      }
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch {
      alert('Cannot reach server to delete user.');
    } finally {
      setDeleteId(null);
    }
  };

  return (
    <div className="animate-fade-in grid grid-cols-1 md:grid-cols-3 gap-8">

      {/* ── Add User Form ── */}
      <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-8 h-fit md:col-span-1">
        <h3 className="font-bold text-lg mb-1 text-[var(--text-primary)] flex items-center gap-2.5">
          <UserPlus className="h-5 w-5 text-[var(--primary)]" />
          Add New User
        </h3>
        <p className="text-xs text-[var(--text-muted)] mb-6">
          Create login credentials for a new team member.
        </p>

        {formError && (
          <div className="flex items-center gap-2 text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-[var(--radius-md)] px-3 py-2.5 mb-4">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
            {formError}
          </div>
        )}
        {formSuccess && (
          <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-[var(--radius-md)] px-3 py-2.5 mb-4">
            <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
            {formSuccess}
          </div>
        )}

        <form onSubmit={handleAddUser} className="flex flex-col gap-4">
          <div>
            <label className="form-label flex items-center gap-1.5">
              <User className="h-3 w-3" /> Full Name
            </label>
            <input
              type="text" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. Sarah Al-Rashidi"
              className="form-input text-sm" disabled={submitting}
            />
          </div>
          <div>
            <label className="form-label flex items-center gap-1.5">
              <Mail className="h-3 w-3" /> Email Address
            </label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="sarah@company.com"
              className="form-input text-sm" disabled={submitting}
            />
          </div>
          <div>
            <label className="form-label flex items-center gap-1.5">
              <KeyRound className="h-3 w-3" /> Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'} value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Min. 6 characters"
                className="form-input text-sm pr-10 w-full" disabled={submitting}
              />
              <button type="button" onClick={() => setShowPassword(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                tabIndex={-1}>
                {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
          <div>
            <label className="form-label flex items-center gap-1.5">
              <Crown className="h-3 w-3" /> Role
            </label>
            <select value={role} onChange={e => setRole(e.target.value)}
              className="form-select text-sm" disabled={submitting}>
              {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <button type="submit" disabled={submitting}
            className="btn btn-primary text-xs w-full font-bold py-3 rounded-full cursor-pointer uppercase tracking-wider mt-1">
            {submitting
              ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Creating…</>
              : <><UserPlus className="h-3.5 w-3.5" /> Create User Account</>}
          </button>
        </form>
      </div>

      {/* ── User List ── */}
      <div className="md:col-span-2 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-[var(--text-primary)] flex items-center gap-2">
            <Users className="h-5 w-5 text-[var(--primary)]" />
            System Users
            <span className="text-[var(--text-muted)] font-normal text-base">({users.length})</span>
          </h3>
          <button onClick={fetchUsers} disabled={loading}
            className="btn btn-secondary text-xs py-1.5 px-3 cursor-pointer flex items-center gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-[var(--radius-md)] px-4 py-3">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-12 flex flex-col items-center gap-3">
            <Loader2 className="h-7 w-7 text-[var(--primary)] animate-spin" />
            <p className="text-sm text-[var(--text-muted)]">Loading users…</p>
          </div>
        ) : users.length === 0 ? (
          <div className="glass border border-[var(--border-light)] rounded-[var(--radius-lg)] p-12 text-center">
            <Users className="h-10 w-10 text-[var(--text-muted)] mx-auto mb-3" />
            <p className="text-sm text-[var(--text-muted)]">No users found.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {users.map(user => {
              const initials = user.name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
              const isCurrentUser = user.email.toLowerCase() === currentUserEmail.toLowerCase();
              const confirmingDelete = deleteId === user.id;
              return (
                <div key={user.id}
                  className={`glass border rounded-[var(--radius-lg)] px-5 py-4 flex items-center gap-4 justify-between transition-colors ${isCurrentUser ? 'border-[var(--primary)]/40 bg-[var(--primary-glow)]' : 'border-[var(--border-light)]'}`}>

                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--primary)] to-[#634b38] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-sm text-[var(--text-primary)] truncate">
                          {user.name}
                        </span>
                        {isCurrentUser && (
                          <span className="text-[10px] font-bold text-[var(--primary)] bg-[var(--primary-glow)] border border-[var(--primary)]/20 px-2 py-0.5 rounded-full">
                            You
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-[var(--text-muted)] truncate block">{user.email}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${ROLE_COLORS[user.role] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                      {user.role === 'Admin' && <Shield className="h-3 w-3 inline mr-0.5 -mt-0.5" />}
                      {user.role}
                    </span>

                    {!isCurrentUser && (
                      confirmingDelete ? (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-rose-600 font-semibold">Delete?</span>
                          <button onClick={() => handleDelete(user.id)}
                            className="text-xs bg-rose-500 text-white px-2.5 py-1 rounded-lg font-bold hover:bg-rose-600 transition-colors cursor-pointer">
                            Yes
                          </button>
                          <button onClick={() => setDeleteId(null)}
                            className="text-xs bg-slate-100 text-[var(--text-secondary)] px-2.5 py-1 rounded-lg font-bold hover:bg-slate-200 transition-colors cursor-pointer">
                            No
                          </button>
                        </div>
                      ) : (
                        <button onClick={() => setDeleteId(user.id)}
                          title={`Remove ${user.name}`}
                          className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
