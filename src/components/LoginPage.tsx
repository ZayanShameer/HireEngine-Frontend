import React, { useState } from 'react';
import { Eye, EyeOff, Loader2, Lock, User, Zap, Shield, AlertCircle } from 'lucide-react';

interface LoginPageProps {
  onLogin: (token: string, user: { name: string; role: string; email: string }) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  const validate = () => {
    const errs: { email?: string; password?: string } = {};
    if (!email.trim()) errs.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Enter a valid email address';
    if (!password) errs.password = 'Password is required';
    else if (password.length < 4) errs.password = 'Password too short';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!validate()) return;

    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:5000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || 'Invalid credentials. Please try again.');
        return;
      }

      onLogin(data.token, data.user);
    } catch {
      setError('Cannot reach the server. Make sure the backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-root">
      {/* Animated background */}
      <div className="login-bg">
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />
        <div className="login-orb-4" />
        <div className="login-grid" />
      </div>

      {/* Card */}
      <div className="login-card-wrapper">
        {/* Brand */}
        <div className="login-brand">
          <div className="login-logo">
            <Zap className="h-6 w-6 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="login-brand-name">HireEngine AI</h1>
            <p className="login-brand-tagline">Enterprise Talent Intelligence Platform</p>
          </div>
        </div>

        <div className="login-card">
          {/* Header */}
          <div className="login-card-header">
            <div className="login-shield-badge">
              <Shield className="h-5 w-5 text-[var(--primary)]" />
            </div>
            <div>
              <h2 className="login-title">Secure Sign In</h2>
              <p className="login-subtitle">Access your recruitment command centre</p>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="login-error-banner">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="login-form" noValidate>
            {/* Email */}
            <div className="login-field">
              <label className="login-label" htmlFor="login-email">
                Email Address
              </label>
              <div className={`login-input-wrapper ${fieldErrors.email ? 'error' : ''}`}>
                <User className="login-input-icon h-4 w-4" />
                <input
                  id="login-email"
                  type="email"
                  autoComplete="username email"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setFieldErrors(p => ({ ...p, email: undefined })); setError(''); }}
                  placeholder="you@company.com"
                  className="login-input"
                  disabled={isLoading}
                />
              </div>
              {fieldErrors.email && <p className="login-field-error">{fieldErrors.email}</p>}
            </div>

            {/* Password */}
            <div className="login-field">
              <label className="login-label" htmlFor="login-password">
                Password
              </label>
              <div className={`login-input-wrapper ${fieldErrors.password ? 'error' : ''}`}>
                <Lock className="login-input-icon h-4 w-4" />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setFieldErrors(p => ({ ...p, password: undefined })); setError(''); }}
                  placeholder="Enter your password"
                  className="login-input pr-10"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="login-eye-toggle"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {fieldErrors.password && <p className="login-field-error">{fieldErrors.password}</p>}
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="login-submit-btn"
              disabled={isLoading}
              id="login-submit"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Authenticating…
                </>
              ) : (
                <>
                  <Shield className="h-4 w-4" />
                  Sign In Securely
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="login-footer-note">
            Protected by JWT authentication. Credentials are managed by your system administrator.
          </p>
        </div>

        <p className="login-copyright">
          © 2026 HireEngine AI · Enterprise Edition
        </p>
      </div>
    </div>
  );
}
