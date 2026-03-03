import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import logoSvg from '../assets/reskiosk-logo.svg';

export default function Login() {
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(username.trim(), password);
            // App.jsx will detect the auth state change and redirect
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Invalid username or password.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg, #0f0f0f)',
            padding: '1rem',
        }}>
            <div style={{
                width: '100%',
                maxWidth: '400px',
            }}>
                {/* Logo + Branding */}
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <img src={logoSvg} alt="ResKiosk" style={{ height: 60, marginBottom: '0.75rem' }} />
                    <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--text, #e0e0e0)' }}>
                        ResKiosk Hub
                    </h1>
                    <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted, #888)', fontSize: '0.875rem' }}>
                        Sign in to continue
                    </p>
                </div>

                {/* Card */}
                <div style={{
                    background: 'var(--card-bg, #1a1a1a)',
                    border: '1px solid var(--border, #2a2a2a)',
                    borderRadius: '16px',
                    padding: '2rem',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
                }}>
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Username
                            </label>
                            <input
                                id="login-username"
                                type="text"
                                autoComplete="username"
                                autoFocus
                                value={username}
                                onChange={e => setUsername(e.target.value)}
                                placeholder="Enter your username"
                                required
                                style={inputStyle}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Password
                            </label>
                            <input
                                id="login-password"
                                type="password"
                                autoComplete="current-password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                required
                                style={inputStyle}
                            />
                        </div>

                        {error && (
                            <div style={{
                                background: 'rgba(239,83,80,0.1)',
                                border: '1px solid rgba(239,83,80,0.3)',
                                borderRadius: '8px',
                                padding: '0.75rem 1rem',
                                color: '#ef5350',
                                fontSize: '0.875rem',
                            }}>
                                {error}
                            </div>
                        )}

                        <button
                            id="login-submit"
                            type="submit"
                            disabled={loading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '10px',
                                border: 'none',
                                background: loading ? 'var(--primary-muted, #1e3a5f)' : 'var(--primary, #42a5f5)',
                                color: '#fff',
                                fontSize: '0.95rem',
                                fontWeight: 700,
                                cursor: loading ? 'not-allowed' : 'pointer',
                                transition: 'all 0.2s ease',
                                opacity: loading ? 0.7 : 1,
                                letterSpacing: '0.02em',
                            }}
                        >
                            {loading ? 'Signing in…' : 'Sign In'}
                        </button>
                    </form>
                </div>

                <p style={{ textAlign: 'center', marginTop: '1.5rem', color: 'var(--text-muted, #555)', fontSize: '0.75rem' }}>
                    ResKiosk Hub — Offline-First Disaster Response System
                </p>
            </div>
        </div>
    );
}

const inputStyle = {
    width: '100%',
    padding: '0.65rem 0.875rem',
    borderRadius: '8px',
    border: '1px solid var(--border, #333)',
    background: 'var(--input-bg, #111)',
    color: 'var(--text, #e0e0e0)',
    fontSize: '0.925rem',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
};
