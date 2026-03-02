import React, { useState, useEffect, useMemo } from 'react';
import hubClient from '../api/hubClient';
import { RefreshCw, Search, Trash2, TrendingUp, MessageCircle, Clock, Hash, Filter, ArrowUpDown, X } from 'lucide-react';
import { useModal } from '../components/ModalProvider';

function QueryTracker() {
    const modal = useModal();
    const [faqs, setFaqs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterLang, setFilterLang] = useState('all');
    const [sortBy, setSortBy] = useState('count');      // count | recent | oldest
    const [minCount, setMinCount] = useState(0);

    useEffect(() => {
        loadFAQs();
    }, []);

    const loadFAQs = async () => {
        setLoading(true);
        try {
            const res = await hubClient.get('/admin/faq-tracker');
            setFaqs(res.data || []);
        } catch (e) {
            console.error('Failed to load FAQ tracker:', e);
        } finally {
            setLoading(false);
        }
    };

    const deleteFAQ = async (id) => {
        if (!(await modal.confirm('Delete this FAQ entry?'))) return;
        try {
            await hubClient.delete(`/admin/faq-tracker/${id}`);
            setFaqs(prev => prev.filter(f => f.id !== id));
        } catch (e) {
            await modal.alert('Failed to delete entry');
        }
    };

    const clearAll = async () => {
        if (!(await modal.confirm('Clear ALL FAQ tracker entries? This cannot be undone.'))) return;
        try {
            await hubClient.delete('/admin/faq-tracker');
            setFaqs([]);
        } catch (e) {
            await modal.alert('Failed to clear entries');
        }
    };

    const formatTime = (ts) => {
        if (!ts) return '—';
        const d = new Date(ts * 1000);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    const languageLabel = (code) => {
        const map = { en: 'English', tl: 'Tagalog', ceb: 'Cebuano', es: 'Spanish', zh: 'Chinese', ja: 'Japanese', ko: 'Korean', vi: 'Vietnamese' };
        return map[code] || code || '—';
    };

    // Collect unique languages for filter dropdown
    const availableLanguages = useMemo(() => {
        const langs = new Set();
        faqs.forEach(f => { if (f.language) langs.add(f.language); });
        return Array.from(langs).sort();
    }, [faqs]);

    // Apply search, filters, and sort
    const filtered = useMemo(() => {
        let result = faqs;

        // Text search
        if (searchTerm) {
            const q = searchTerm.toLowerCase();
            result = result.filter(f =>
                (f.source_question || '').toLowerCase().includes(q) ||
                (f.question_display || '').toLowerCase().includes(q) ||
                (f.source_answer || '').toLowerCase().includes(q)
            );
        }

        // Language filter
        if (filterLang !== 'all') {
            result = result.filter(f => f.language === filterLang);
        }

        // Min count filter
        if (minCount > 0) {
            result = result.filter(f => f.count >= minCount);
        }

        // Sort
        result = [...result].sort((a, b) => {
            if (sortBy === 'count') return b.count - a.count;
            if (sortBy === 'recent') return (b.last_asked_at || 0) - (a.last_asked_at || 0);
            if (sortBy === 'oldest') return (a.first_asked_at || 0) - (b.first_asked_at || 0);
            return 0;
        });

        return result;
    }, [faqs, searchTerm, filterLang, minCount, sortBy]);

    const totalQueries = faqs.reduce((acc, f) => acc + f.count, 0);
    const topQuestion = faqs.length > 0 ? [...faqs].sort((a, b) => b.count - a.count)[0] : null;
    const hasActiveFilters = searchTerm || filterLang !== 'all' || minCount > 0;

    const clearFilters = () => {
        setSearchTerm('');
        setFilterLang('all');
        setMinCount(0);
        setSortBy('count');
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="page-title">Query Tracker</h1>
                    <p className="text-sm text-muted">Frequently asked questions grouped by answer — different questions that get the same answer are counted together</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={loadFAQs} className="btn" disabled={loading}>
                        <RefreshCw size={16} className={loading ? 'spin' : ''} />
                        Refresh
                    </button>
                    {faqs.length > 0 && (
                        <button onClick={clearAll} className="btn" style={{ color: 'var(--danger)' }}>
                            <Trash2 size={16} />
                            Clear All
                        </button>
                    )}
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid-3">
                <div className="card">
                    <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Hash size={14} /> Unique Answers
                    </div>
                    <div className="stat-value">{faqs.length}</div>
                </div>
                <div className="card">
                    <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <MessageCircle size={14} /> Total Queries
                    </div>
                    <div className="stat-value">{totalQueries}</div>
                </div>
                <div className="card">
                    <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <TrendingUp size={14} /> Most Asked
                    </div>
                    <div className="stat-value" style={{ fontSize: '1rem' }}>
                        {topQuestion
                            ? `"${(topQuestion.source_question || topQuestion.question_display || '').slice(0, 40)}${(topQuestion.source_question || '').length > 40 ? '…' : ''}" (${topQuestion.count}×)`
                            : '—'}
                    </div>
                </div>
            </div>

            {/* Search & Filters */}
            <div className="card" style={{ padding: '0.75rem 1rem' }}>
                {/* Search bar */}
                <div className="flex items-center gap-2" style={{ marginBottom: '0.75rem' }}>
                    <Search size={18} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                    <input
                        className="input"
                        placeholder="Search by question or answer..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        style={{ border: 'none', background: 'transparent', padding: 0, boxShadow: 'none', flex: 1 }}
                    />
                    {searchTerm && (
                        <button onClick={() => setSearchTerm('')} className="btn-icon" style={{ padding: '0.15rem' }}>
                            <X size={14} style={{ color: 'var(--text-muted)' }} />
                        </button>
                    )}
                </div>

                {/* Filter row */}
                <div style={{
                    display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
                    borderTop: '1px solid var(--border)', paddingTop: '0.75rem',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600 }}>
                        <Filter size={14} /> Filters:
                    </div>

                    {/* Language filter */}
                    <select
                        className="input"
                        value={filterLang}
                        onChange={e => setFilterLang(e.target.value)}
                        style={{ width: 'auto', minWidth: '8rem', padding: '0.35rem 0.6rem', fontSize: '0.8rem' }}
                    >
                        <option value="all">All Languages</option>
                        {availableLanguages.map(lang => (
                            <option key={lang} value={lang}>{languageLabel(lang)}</option>
                        ))}
                    </select>

                    {/* Min count filter */}
                    <select
                        className="input"
                        value={minCount}
                        onChange={e => setMinCount(parseInt(e.target.value))}
                        style={{ width: 'auto', minWidth: '8rem', padding: '0.35rem 0.6rem', fontSize: '0.8rem' }}
                    >
                        <option value={0}>Any Count</option>
                        <option value={2}>2+ times</option>
                        <option value={3}>3+ times</option>
                        <option value={5}>5+ times</option>
                        <option value={10}>10+ times</option>
                    </select>

                    {/* Sort */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginLeft: 'auto' }}>
                        <ArrowUpDown size={14} style={{ color: 'var(--text-muted)' }} />
                        <select
                            className="input"
                            value={sortBy}
                            onChange={e => setSortBy(e.target.value)}
                            style={{ width: 'auto', minWidth: '8rem', padding: '0.35rem 0.6rem', fontSize: '0.8rem' }}
                        >
                            <option value="count">Most Asked</option>
                            <option value="recent">Most Recent</option>
                            <option value="oldest">Oldest First</option>
                        </select>
                    </div>

                    {/* Clear filters button */}
                    {hasActiveFilters && (
                        <button onClick={clearFilters} className="btn" style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem' }}>
                            <X size={12} /> Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Results count */}
            {!loading && filtered.length !== faqs.length && (
                <div className="text-sm text-muted" style={{ marginTop: '-0.5rem' }}>
                    Showing {filtered.length} of {faqs.length} entries
                </div>
            )}

            {/* Table */}
            {loading ? (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem', color: 'var(--text-muted)' }} />
                    <p className="text-muted">Loading FAQ data...</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <MessageCircle size={32} style={{ margin: '0 auto 0.75rem', color: 'var(--text-muted)' }} />
                    <p className="text-muted">
                        {hasActiveFilters
                            ? 'No entries match your filters.'
                            : 'No queries tracked yet. Questions from kiosk users will appear here.'}
                    </p>
                    {hasActiveFilters && (
                        <button onClick={clearFilters} className="btn" style={{ marginTop: '0.75rem' }}>
                            Clear Filters
                        </button>
                    )}
                </div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
                                <th style={thStyle}>#</th>
                                <th style={{ ...thStyle, textAlign: 'left' }}>KB Article (Answer)</th>
                                <th style={{ ...thStyle, textAlign: 'left' }}>Last User Query</th>
                                <th style={thStyle}>Times Asked</th>
                                <th style={thStyle}>Language</th>
                                <th style={thStyle}>Last Asked</th>
                                <th style={thStyle}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((faq, idx) => (
                                <tr key={faq.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                    <td style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600, width: '3rem' }}>
                                        {idx + 1}
                                    </td>
                                    <td style={{ ...tdStyle, maxWidth: '20rem' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                                            {faq.source_question || '—'}
                                        </div>
                                        {faq.source_answer && (
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4, whiteSpace: 'pre-wrap', maxHeight: '3rem', overflow: 'hidden' }}>
                                                {faq.source_answer.length > 120 ? faq.source_answer.slice(0, 120) + '…' : faq.source_answer}
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ ...tdStyle, fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', maxWidth: '14rem' }}>
                                        "{faq.question_display || '—'}"
                                    </td>
                                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                                        <span style={{
                                            background: faq.count >= 5 ? 'rgba(66, 165, 245, 0.15)' : 'rgba(158, 158, 158, 0.1)',
                                            color: faq.count >= 5 ? 'var(--primary)' : 'var(--text)',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '999px',
                                            fontWeight: 700,
                                            fontSize: '0.9rem',
                                        }}>
                                            {faq.count}
                                        </span>
                                    </td>
                                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: '0.85rem' }}>
                                        {languageLabel(faq.language)}
                                    </td>
                                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                        <Clock size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                                        {formatTime(faq.last_asked_at)}
                                    </td>
                                    <td style={{ ...tdStyle, textAlign: 'center', width: '2.5rem' }}>
                                        <button
                                            onClick={() => deleteFAQ(faq.id)}
                                            className="btn-icon"
                                            title="Delete entry"
                                            style={{ padding: '0.25rem' }}
                                        >
                                            <Trash2 size={14} style={{ color: 'var(--danger)' }} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const thStyle = {
    padding: '0.75rem 1rem',
    fontSize: '0.75rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: 'var(--text-muted)',
    textAlign: 'center',
};

const tdStyle = {
    padding: '0.75rem 1rem',
    fontSize: '0.875rem',
};

export default QueryTracker;
