import React, { useState, useEffect } from 'react';
import hubClient from '../api/hubClient';
import logoSvg from '../assets/reskiosk-logo.svg';
import KBViewer from './KBViewer';
import { useNavigate } from 'react-router-dom';
import { HelpCircle, TrendingUp, MessageCircle, Hash } from 'lucide-react';

function Dashboard({ setEmergencyMode }) {
    const [stats, setStats] = useState({ kb_version: 0, online: false, article_count: 0, device_id: '' });
    const [loading, setLoading] = useState(true);
    const [isEmergency, setIsEmergency] = useState(false);
    const [faqStats, setFaqStats] = useState({ total: 0, unique: 0, topQuestion: null });
    const navigate = useNavigate();

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [snapRes, netRes, faqRes] = await Promise.all([
                hubClient.get('/kb/snapshot'),
                hubClient.get('/network/info').catch(() => ({ data: {} })),
                hubClient.get('/admin/faq-tracker').catch(() => ({ data: [] }))
            ]);
            const snap = snapRes.data;
            const articles = snap.articles || [];
            const config = snap.structured_config || {};

            setStats({
                kb_version: snap.kb_version,
                online: true,
                article_count: articles.filter(a => a.enabled).length,
                device_id: netRes.data.device_id || ''
            });

            // FAQ stats
            const faqData = faqRes.data || [];
            const totalQueries = faqData.reduce((acc, f) => acc + f.count, 0);
            const sorted = [...faqData].sort((a, b) => b.count - a.count);
            setFaqStats({
                total: totalQueries,
                unique: faqData.length,
                topQuestion: sorted.length > 0 ? sorted[0] : null
            });

            const em = config.emergency_mode === 'active';
            setIsEmergency(em);
            setEmergencyMode(em);

        } catch (e) {
            setStats(s => ({ ...s, online: false }));
        } finally {
            setLoading(false);
        }
    };

    const toggleEmergency = async () => {
        try {
            const newValue = !isEmergency;
            const status = newValue ? 'active' : 'inactive';
            await hubClient.put('/admin/evac', { emergency_mode: status });
            setIsEmergency(newValue);
            setEmergencyMode(newValue);
        } catch (e) {
            alert("Failed to toggle emergency mode");
        }
    };

    if (loading) return <div className="p-8 text-muted">Loading Dashboard...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4 mb-2">
                <img src={logoSvg} alt="ResKiosk" style={{ width: 40, height: 40, borderRadius: 8 }} />
                <div>
                    <h1 className="page-title">Dashboard</h1>
                    <p className="text-sm text-muted">Overview of your ResKiosk Hub</p>
                </div>
            </div>

            <div className="grid-3">
                {/* Hub Status */}
                <div className="card">
                    <div className="stat-label">Hub Status</div>
                    <div className="stat-row">
                        <span className={`status-dot ${stats.online ? 'online' : 'offline'}`}></span>
                        <span className="stat-value" style={{ fontSize: '1.5rem' }}>{stats.online ? 'Online' : 'Offline'}</span>
                    </div>
                </div>

                {/* KB Version */}
                <div className="card">
                    <div className="stat-label">KB Version</div>
                    <div className="stat-value">v{stats.kb_version}</div>
                </div>

                {/* Active Articles */}
                <div className="card">
                    <div className="stat-label">Active Articles</div>
                    <div className="stat-value">{stats.article_count}</div>
                </div>
            </div>

            {/* FAQ Tracker Summary */}
            <div className="card">
                <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
                    <div className="flex items-center gap-2">
                        <HelpCircle size={18} style={{ color: 'var(--primary)' }} />
                        <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Query Tracker</h3>
                    </div>
                    <button className="btn" onClick={() => navigate('/query-tracker')} style={{ fontSize: '0.8rem', padding: '0.3rem 0.75rem' }}>
                        View All →
                    </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                    <div style={{ background: 'var(--bg-secondary)', borderRadius: '0.5rem', padding: '0.75rem 1rem' }}>
                        <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
                            <MessageCircle size={12} /> Total Queries
                        </div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{faqStats.total}</div>
                    </div>
                    <div style={{ background: 'var(--bg-secondary)', borderRadius: '0.5rem', padding: '0.75rem 1rem' }}>
                        <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
                            <Hash size={12} /> Unique Topics
                        </div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{faqStats.unique}</div>
                    </div>
                    <div style={{ background: 'var(--bg-secondary)', borderRadius: '0.5rem', padding: '0.75rem 1rem' }}>
                        <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
                            <TrendingUp size={12} /> Top FAQ
                        </div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                            {faqStats.topQuestion
                                ? `"${(faqStats.topQuestion.source_question || faqStats.topQuestion.question_display || '').slice(0, 35)}${(faqStats.topQuestion.source_question || '').length > 35 ? '…' : ''}" (${faqStats.topQuestion.count}×)`
                                : 'No queries yet'}
                        </div>
                    </div>
                </div>
            </div>

            {/* Device ID */}
            {stats.device_id && (
                <div className="card">
                    <div className="stat-label">Device ID</div>
                    <div className="font-mono text-sm" style={{ wordBreak: 'break-all' }}>{stats.device_id}</div>
                    <p className="text-sm text-muted mt-1">Use this to identify this device (e.g. multi-site or support).</p>
                </div>
            )}

            {/* Emergency Toggle */}
            <div className={`card emergency-card ${isEmergency ? 'active' : ''}`}>
                <div className="flex items-center justify-between">
                    <div>
                        <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--danger)', marginBottom: '0.25rem' }}>
                            Emergency Mode
                        </h3>
                        <p className="text-sm text-muted">Activates header banners on all kiosks.</p>
                    </div>
                    <button
                        onClick={toggleEmergency}
                        className={`btn ${isEmergency ? 'btn-danger' : ''}`}
                    >
                        {isEmergency ? 'DEACTIVATE' : 'ACTIVATE'}
                    </button>
                </div>
            </div>

            <KBViewer />
        </div>
    );
}

export default Dashboard;

