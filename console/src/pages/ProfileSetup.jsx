import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import hubClient from '../api/hubClient';
import logoSvg from '../assets/reskiosk-logo.svg';
import { UserCircle2 } from 'lucide-react';

export default function ProfileSetup() {
    const { user, updateUser, logout } = useAuth();
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!firstName.trim()) return setError('First name is required.');
        if (!lastName.trim()) return setError('Last name is required.');
        if (newPassword.length < 6) return setError('Password must be at least 6 characters.');
        if (newPassword !== confirmPassword) return setError('Passwords do not match.');

        setLoading(true);
        try {
            const res = await hubClient.post('/auth/setup', {
                first_name: firstName.trim(),
                last_name: lastName.trim(),
                new_password: newPassword,
            });
            updateUser({ ...res.data, is_first_login: false });
            // App.jsx will re-render and show the main layout
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Setup failed. Please try again.';
            setError(msg);
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
            <div style={{ width: '100%', maxWidth: '440px' }}>
                {/* Logo */}
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <img src={logoSvg} alt="ResKiosk" style={{ height: 56, marginBottom: '0.75rem' }} />
                    <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text, #e0e0e0)' }}>
                        Welcome to ResKiosk Hub
                    </h1>
                    <p style={{ margin: '0.4rem 0 0', color: 'var(--text-muted, #888)', fontSize: '0.875rem' }}>
                        Complete your profile to get started
                    </p>
                </div>

                {/* Card */}
                <div style={{
                    background: 'var(--card-bg, #1a1a1a)',
                    border: '1px solid var(--border, #2a2a2a)',
                    borderRadius: '16px',
                    overflow: 'hidden',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
                }}>
                    {/* Header strip */}
                    <div style={{
                        background: 'linear-gradient(135deg, rgba(66,165,245,0.15), rgba(66,165,245,0.05))',
                        borderBottom: '1px solid var(--border, #2a2a2a)',
                        padding: '1.25rem 2rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                    }}>
                        <div style={{
                            width: 40, height: 40, borderRadius: '50%',
                            background: 'rgba(66,165,245,0.15)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <UserCircle2 size={22} style={{ color: 'var(--primary, #42a5f5)' }} />
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--text, #e0e0e0)', fontSize: '0.95rem' }}>
                                First-time Setup
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted, #888)' }}>
                                Logged in as <strong style={{ color: 'var(--primary, #42a5f5)' }}>{user?.username}</strong>
                            </div>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} style={{ padding: '1.75rem 2rem', display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                        {/* Name row */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                            <div>
                                <label style={labelStyle}>First Name</label>
                                <input
                                    id="setup-firstname"
                                    type="text"
                                    value={firstName}
                                    onChange={e => setFirstName(e.target.value)}
                                    placeholder="Juan"
                                    autoFocus
                                    required
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={labelStyle}>Last Name</label>
                                <input
                                    id="setup-lastname"
                                    type="text"
                                    value={lastName}
                                    onChange={e => setLastName(e.target.value)}
                                    placeholder="dela Cruz"
                                    required
                                    style={inputStyle}
                                />
                            </div>
                        </div>

                        <div>
                            <label style={labelStyle}>New Password</label>
                            <input
                                id="setup-password"
                                type="password"
                                value={newPassword}
                                onChange={e => setNewPassword(e.target.value)}
                                placeholder="At least 6 characters"
                                required
                                style={inputStyle}
                            />
                        </div>

                        <div>
                            <label style={labelStyle}>Confirm Password</label>
                            <input
                                id="setup-confirm-password"
                                type="password"
                                value={confirmPassword}
                                onChange={e => setConfirmPassword(e.target.value)}
                                placeholder="Re-enter password"
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

                        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
                            <button
                                type="button"
                                onClick={logout}
                                style={{
                                    flex: '0 0 auto',
                                    padding: '0.7rem 1.25rem',
                                    borderRadius: '10px',
                                    border: '1px solid var(--border, #333)',
                                    background: 'transparent',
                                    color: 'var(--text-muted, #888)',
                                    fontSize: '0.875rem',
                                    cursor: 'pointer',
                                }}
                            >
                                Back
                            </button>
                            <button
                                id="setup-submit"
                                type="submit"
                                disabled={loading}
                                style={{
                                    flex: 1,
                                    padding: '0.7rem',
                                    borderRadius: '10px',
                                    border: 'none',
                                    background: loading ? 'var(--primary-muted, #1e3a5f)' : 'var(--primary, #42a5f5)',
                                    color: '#fff',
                                    fontSize: '0.925rem',
                                    fontWeight: 700,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    opacity: loading ? 0.7 : 1,
                                    transition: 'all 0.2s ease',
                                }}
                            >
                                {loading ? 'Saving…' : 'Save & Continue'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

const labelStyle = {
    display: 'block',
    marginBottom: '0.35rem',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: 'var(--text-muted, #888)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const inputStyle = {
    width: '100%',
    padding: '0.65rem 0.875rem',
    borderRadius: '8px',
    border: '1px solid var(--border, #333)',
    background: 'var(--input-bg, #111)',
    color: 'var(--text, #e0e0e0)',
    fontSize: '0.9rem',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
};
