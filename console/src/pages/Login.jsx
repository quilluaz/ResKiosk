import React, { useState } from 'react';
import hubClient from '../api/hubClient';
import { LogIn, AlertCircle } from 'lucide-react';

function Login({ onLoginSuccess }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const res = await hubClient.post('/auth/login', { email, password });
            if (res.data.status === 'ok') {
                onLoginSuccess(res.data.user);
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-[80vh]">
            <div className="card w-full max-w-sm p-8 space-y-6" style={{
                background: 'linear-gradient(180deg, rgba(30,30,50,0.8), rgba(20,20,35,0.95))',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
            }}>
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight text-white mb-2">Admin Login</h2>
                    <p className="text-muted text-sm">Access protected Hub features</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="p-3 rounded-lg flex items-center gap-3 text-sm" style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            color: '#f87171'
                        }}>
                            <AlertCircle size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-muted uppercase tracking-wider">Email Address</label>
                        <input
                            type="email"
                            required
                            className="input w-full"
                            placeholder="admin@reskiosk.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-muted uppercase tracking-wider">Password</label>
                        <input
                            type="password"
                            required
                            className="input w-full"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn btn-primary w-full py-3 flex items-center justify-center gap-2"
                        style={{ marginTop: '1.5rem' }}
                    >
                        {loading ? 'Logging in...' : (
                            <>
                                <LogIn size={18} />
                                <span>Sign In</span>
                            </>
                        )}
                    </button>
                </form>

                <div className="text-center text-xs text-muted pt-4 border-t border-white/5">
                    Default credentials are seeded in <code>seed.py</code>
                </div>
            </div>
        </div>
    );
}

export default Login;
