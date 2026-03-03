import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import hubClient from '../api/hubClient';
import { RefreshCw } from 'lucide-react';
import { useModal } from '../components/ModalProvider';

function EmergencyCalls() {
    const modal = useModal();
    const [alerts, setAlerts] = useState([]);
    const [historyAlerts, setHistoryAlerts] = useState([]);
    const [kiosks, setKiosks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingKiosk, setEditingKiosk] = useState(null);
    const [editName, setEditName] = useState('');
    const [tab, setTab] = useState('active');
    const [sseDisconnected, setSseDisconnected] = useState(false);
    const [showDismissed, setShowDismissed] = useState(false);
    const [showResolved, setShowResolved] = useState(false);
    const playedAlertIdsRef = useRef(new Set());
    const pendingAlertIdsRef = useRef(new Set());
    const alertAudioRef = useRef(null);
    const audioUnlockedRef = useRef(false);

    const [historyFilters, setHistoryFilters] = useState({
        kiosk_id: '',
        tier: '',
        from: '',
        to: '',
    });

    const fetchActive = useCallback(async () => {
        try {
            const res = await hubClient.get('/emergency/active');
            const rows = res.data.alerts || [];
            setAlerts(rows);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const attemptPlayAlertSound = useCallback(async () => {
        const srcCandidates = ['/emergencycallalert.mp3', '/console/emergencycallalert.mp3'];
        const audio = alertAudioRef.current || new Audio();
        alertAudioRef.current = audio;
        audio.preload = 'auto';
        audio.muted = false;
        audio.volume = 1.0;
        audio.loop = false;
        audio.currentTime = 0;

        for (const src of srcCandidates) {
            try {
                audio.src = src;
                await audio.play();
                return true;
            } catch (err) {
                // try next src
            }
        }
        return false;
    }, []);

    const playNewAlertSound = useCallback(async (alertId) => {
        if (alertId == null) return;
        const normalizedId = String(alertId);
        if (playedAlertIdsRef.current.has(normalizedId)) return;
        const played = await attemptPlayAlertSound();
        if (played) {
            playedAlertIdsRef.current.add(normalizedId);
            pendingAlertIdsRef.current.delete(normalizedId);
        } else {
            pendingAlertIdsRef.current.add(normalizedId);
        }
    }, [attemptPlayAlertSound]);

    useEffect(() => {
        const unlockAudio = async () => {
            const audio = alertAudioRef.current || new Audio('/emergencycallalert.mp3');
            alertAudioRef.current = audio;
            audio.muted = true;
            audio.volume = 0;
            try {
                await audio.play();
                audio.pause();
                audio.currentTime = 0;
                audioUnlockedRef.current = true;
            } catch (err) {
                // leave listeners attached; try again on next user interaction
            } finally {
                audio.muted = false;
                audio.volume = 1.0;
            }

            if (audioUnlockedRef.current && pendingAlertIdsRef.current.size > 0) {
                const pendingIds = Array.from(pendingAlertIdsRef.current);
                for (const id of pendingIds) {
                    const played = await attemptPlayAlertSound();
                    if (played) {
                        playedAlertIdsRef.current.add(id);
                        pendingAlertIdsRef.current.delete(id);
                    }
                }
            }

            if (!audioUnlockedRef.current) return;
            document.removeEventListener('pointerdown', unlockAudio);
            document.removeEventListener('keydown', unlockAudio);
        };
        document.addEventListener('pointerdown', unlockAudio, { passive: true });
        document.addEventListener('keydown', unlockAudio);
        return () => {
            document.removeEventListener('pointerdown', unlockAudio);
            document.removeEventListener('keydown', unlockAudio);
        };
    }, [attemptPlayAlertSound]);

    const fetchHistory = useCallback(async () => {
        try {
            const params = {};
            if (historyFilters.kiosk_id) params.kiosk_id = historyFilters.kiosk_id;
            if (historyFilters.tier) params.tier = parseInt(historyFilters.tier, 10);
            if (historyFilters.from) params.ts_from = Date.parse(historyFilters.from);
            if (historyFilters.to) params.ts_to = Date.parse(historyFilters.to);
            const res = await hubClient.get('/emergency/history', { params });
            setHistoryAlerts(res.data.alerts || []);
        } catch (e) {
            console.error(e);
        }
    }, [historyFilters]);

    const fetchNetwork = useCallback(async () => {
        try {
            const res = await hubClient.get('/network/info');
            setKiosks(res.data.kiosks_list || []);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const load = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchActive(), fetchNetwork()]);
        setLoading(false);
    }, [fetchActive, fetchNetwork]);

    useEffect(() => {
        load();
    }, [load]);

    // SSE for new alerts (auto-reconnect with backoff)
    useEffect(() => {
        let evtSource;
        let retry = 1000;
        let stopped = false;

        const connect = () => {
            if (stopped) return;
            evtSource = new EventSource('/emergency/stream');
            evtSource.onopen = () => {
                setSseDisconnected(false);
                retry = 1000;
                fetchActive();
            };
            evtSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.type === 'EMERGENCY_ALERT') {
                        void playNewAlertSound(data.id ?? data.alert_id);
                        setAlerts(prev => [data, ...prev]);
                    } else if (
                        data.type === 'EMERGENCY_ACKNOWLEDGED' ||
                        data.type === 'EMERGENCY_RESPONDING' ||
                        data.type === 'EMERGENCY_RESOLVED' ||
                        data.type === 'EMERGENCY_DISMISSED'
                    ) {
                        setAlerts(prev => prev.map(a => a.id === data.id ? data : a));
                    }
                } catch (err) {}
            };
            evtSource.onerror = () => {
                setSseDisconnected(true);
                evtSource.close();
                setTimeout(() => {
                    retry = Math.min(retry * 2, 30000);
                    connect();
                }, retry);
            };
        };

        connect();
        return () => {
            stopped = true;
            if (evtSource) evtSource.close();
        };
    }, [fetchActive]);

    const acknowledgeAlert = async (alertId) => {
        try {
            await hubClient.patch(`/emergency/${alertId}/acknowledge`);
        } catch (e) {
            await modal.alert('Failed to acknowledge');
        }
    };

    const respondingAlert = async (alertId) => {
        try {
            await hubClient.patch(`/emergency/${alertId}/responding`);
        } catch (e) {
            await modal.alert('Failed to mark responding');
        }
    };

    const resolveAlert = async (alertId) => {
        try {
            const notes = await modal.prompt('Resolution notes (optional):', '');
            if (notes === null) return;
            const resolvedBy = await modal.prompt('Resolved by (name):', '');
            if (resolvedBy === null) return;
            await hubClient.post(`/emergency/${alertId}/resolve`, {
                resolution_notes: notes || null,
                resolved_by: resolvedBy || null,
            });
            setAlerts(prev => prev.filter(a => a.id !== alertId));
        } catch (e) {
            await modal.alert('Failed to mark resolved');
        }
    };

    const formatTimeAgo = (ts) => {
        if (!ts) return '—';
        const diffMs = Date.now() - ts;
        const mins = Math.floor(diffMs / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins} min ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours} hr ago`;
        const days = Math.floor(hours / 24);
        return `${days} day${days === 1 ? '' : 's'} ago`;
    };

    const formatDuration = (start, end) => {
        if (!start || !end) return '—';
        const diffMs = end - start;
        const mins = Math.floor(diffMs / 60000);
        if (mins < 1) return '<1 min';
        if (mins < 60) return `${mins} min`;
        const hours = Math.floor(mins / 60);
        const rem = mins % 60;
        return `${hours}h ${rem}m`;
    };

    const getTierChipStyle = (tier) => {
        if ((tier || 1) === 1) {
            return { background: '#b71c1c', color: '#fff', border: '1px solid #e57373' };
        }
        return { background: '#8a6d1a', color: '#fff', border: '1px solid #d4b14a' };
    };

    const getStatusChipStyle = (status) => {
        const s = (status || 'ACTIVE').toUpperCase();
        if (s === 'ACTIVE') return { background: 'rgba(183, 28, 28, 0.16)', color: '#ffb4b4', border: '1px solid rgba(255, 120, 120, 0.35)' };
        if (s === 'ACKNOWLEDGED') return { background: 'rgba(255, 179, 0, 0.14)', color: '#ffd166', border: '1px solid rgba(255, 209, 102, 0.35)' };
        if (s === 'RESPONDING') return { background: 'rgba(79, 195, 247, 0.14)', color: '#9fe8ff', border: '1px solid rgba(120, 220, 255, 0.35)' };
        if (s === 'DISMISSED') return { background: 'rgba(158, 158, 158, 0.2)', color: '#d6d6d6', border: '1px solid rgba(200, 200, 200, 0.25)' };
        if (s === 'RESOLVED') return { background: 'rgba(102, 187, 106, 0.16)', color: '#b9f6ca', border: '1px solid rgba(165, 214, 167, 0.35)' };
        return { background: 'rgba(160, 160, 160, 0.16)', color: '#e0e0e0', border: '1px solid rgba(180, 180, 180, 0.3)' };
    };

    const getAlertCardStyle = (alert) => {
        const status = (alert?.status || 'ACTIVE').toUpperCase();
        if (status === 'ACTIVE') {
            return {
                border: '1px solid rgba(255, 84, 84, 0.42)',
                background: 'linear-gradient(180deg, rgba(140, 22, 22, 0.38), rgba(90, 16, 16, 0.22))',
                boxShadow: '0 0 0 1px rgba(183, 28, 28, 0.2), 0 8px 24px rgba(0,0,0,0.25)',
            };
        }
        if (status === 'RESPONDING') {
            return {
                border: '1px solid rgba(120, 220, 255, 0.35)',
                background: 'linear-gradient(180deg, rgba(16, 51, 72, 0.36), rgba(12, 37, 55, 0.2))',
                boxShadow: '0 0 0 1px rgba(79, 195, 247, 0.18), 0 8px 20px rgba(0,0,0,0.2)',
            };
        }
        if (status === 'ACKNOWLEDGED') {
            return {
                border: '1px solid rgba(255, 209, 102, 0.32)',
                background: 'linear-gradient(180deg, rgba(92, 72, 22, 0.34), rgba(58, 45, 14, 0.2))',
            };
        }
        return {
            border: '1px solid rgba(160, 160, 160, 0.28)',
            background: 'linear-gradient(180deg, rgba(70, 70, 70, 0.22), rgba(46, 46, 46, 0.16))',
        };
    };

    const actionBtnStyle = {
        width: '170px',
        fontWeight: 700,
        borderRadius: 10,
        padding: '0.55rem 0.85rem',
        border: '1px solid transparent',
        letterSpacing: '0.01em',
    };

    const btnPrimary = {
        ...actionBtnStyle,
        background: 'linear-gradient(180deg, #ff7a1a, #e05e00)',
        color: '#fff',
        borderColor: 'rgba(255, 190, 120, 0.45)',
        boxShadow: '0 6px 18px rgba(224, 94, 0, 0.35)',
    };

    const btnSecondary = {
        ...actionBtnStyle,
        background: 'rgba(255, 255, 255, 0.06)',
        color: '#e8e8e8',
        borderColor: 'rgba(255, 255, 255, 0.18)',
    };

    const btnSuccess = {
        ...actionBtnStyle,
        background: 'linear-gradient(180deg, #2e8f4b, #256f3a)',
        color: '#fff',
        borderColor: 'rgba(149, 242, 178, 0.4)',
        boxShadow: '0 6px 18px rgba(46, 143, 75, 0.32)',
    };

    const exportHistoryCsv = () => {
        if (!historyAlerts.length) return;
        const headers = [
            'id',
            'kiosk',
            'tier',
            'timestamp',
            'language',
            'transcript',
            'responding_at',
            'resolved_at',
            'response_time',
            'resolution_time',
            'resolved_by',
            'resolution_notes'
        ];
        const rows = historyAlerts.map(a => {
            const responseTime = formatDuration(a.timestamp, a.responding_at);
            const resolutionTime = formatDuration(a.timestamp, a.resolved_at);
            return [
                a.id,
                a.kiosk_name || a.kiosk_location || a.kiosk_id || '',
                a.tier || 1,
                a.timestamp ? new Date(a.timestamp).toISOString() : '',
                a.language || 'en',
                (a.transcript || '').replace(/\n/g, ' '),
                a.responding_at ? new Date(a.responding_at).toISOString() : '',
                a.resolved_at ? new Date(a.resolved_at).toISOString() : '',
                responseTime,
                resolutionTime,
                a.resolved_by || '',
                (a.resolution_notes || '').replace(/\n/g, ' ')
            ];
        });
        const csv = [headers, ...rows]
            .map(row => row.map(v => `"${String(v).replace(/\"/g, '""')}"`).join(','))
            .join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'emergency_history.csv';
        link.click();
        URL.revokeObjectURL(url);
    };

    const saveKioskName = async (kioskId) => {
        if (editingKiosk !== kioskId || editName.trim() === '') {
            setEditingKiosk(null);
            return;
        }
        try {
            await hubClient.post('/network/kiosk/name', {
                kiosk_id: kioskId,
                kiosk_name: editName.trim(),
            });
            setKiosks(prev => prev.map(k => k.kiosk_id === kioskId ? { ...k, kiosk_name: editName.trim() } : k));
            setEditingKiosk(null);
            setEditName('');
        } catch (e) {
            await modal.alert('Failed to update name');
        }
    };

    const sortedAlerts = useMemo(() => {
        return [...alerts].sort((a, b) => {
            const tierA = a.tier || 1;
            const tierB = b.tier || 1;
            if (tierA !== tierB) return tierA - tierB;
            return (b.timestamp || 0) - (a.timestamp || 0);
        });
    }, [alerts]);

    const visibleAlerts = useMemo(() => {
        return sortedAlerts.filter((a) => {
            const status = (a.status || 'ACTIVE').toUpperCase();
            if (status === 'DISMISSED' && !showDismissed) return false;
            if (status === 'RESOLVED' && !showResolved) return false;
            return true;
        });
    }, [sortedAlerts, showDismissed, showResolved]);

    if (loading) return <div className="p-8 text-muted">Loading...</div>;

    return (
        <div className="space-y-6">
            <h1 className="page-title">Emergency Calls</h1>
            {sseDisconnected && (
                <div className="card" style={{ background: 'rgba(110, 82, 15, 0.35)', color: '#ffe082', border: '1px solid rgba(255, 224, 130, 0.25)' }}>
                    Live alert feed disconnected — reconnecting.
                </div>
            )}
            <div className="flex gap-2">
                <button className={`btn btn-sm ${tab === 'active' ? '' : 'btn-muted'}`} onClick={() => setTab('active')}>
                    Active
                </button>
                <button className={`btn btn-sm ${tab === 'history' ? '' : 'btn-muted'}`} onClick={() => { setTab('history'); fetchHistory(); }}>
                    History
                </button>
            </div>

            {tab === 'active' && (
            <div className="card">
                <h3 className="section-title">Active Emergency Alerts ({visibleAlerts.length})</h3>
                {visibleAlerts.length === 0 ? (
                    <p className="text-muted">No alerts for the selected filter.</p>
                ) : (
                    <div className="space-y-4">
                        {visibleAlerts.map((a) => (
                            <div
                                key={a.id}
                                className="p-4 rounded border"
                                style={getAlertCardStyle(a)}
                            >
                                <div className="flex justify-between items-start gap-4">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <div className="font-semibold text-lg" style={{ color: '#ffd9d9' }}>
                                                {a.kiosk_name || a.kiosk_location || 'Unknown kiosk'}
                                            </div>
                                            <span className="badge" style={getTierChipStyle(a.tier)}>
                                                {(a.tier || 1) === 1 ? 'CRITICAL' : 'CONFIRMED'}
                                            </span>
                                            <span className="badge" style={getStatusChipStyle(a.status)}>
                                                {a.status || 'ACTIVE'}
                                            </span>
                                        </div>
                                        <div className="text-xs mt-1" style={{ color: '#9aa0a6' }}>
                                            Kiosk ID: {a.kiosk_id || 'unknown'}
                                            {a.kiosk_location ? ` | Location: ${a.kiosk_location}` : ''}
                                        </div>
                                        <div className="text-sm mt-1" style={{ color: '#bfbfbf' }}>
                                            {new Date(a.timestamp).toLocaleString()} | {formatTimeAgo(a.timestamp)}
                                        </div>
                                        <div className="text-xs mt-1" style={{ color: '#9aa0a6' }}>
                                            Tier: {a.tier || 1} | Lang: {a.language || 'en'}
                                        </div>

                                        {a.transcript && (
                                            <p className="mt-2" style={{ color: '#f0f0f0' }}>{a.transcript}</p>
                                        )}
                                        {a.dismissed_by_kiosk === 1 && (
                                            <div className="text-xs mt-2" style={{ color: '#9aa0a6' }}>User dismissed at kiosk.</div>
                                        )}
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        {a.status === 'ACTIVE' && (
                                            <button style={btnPrimary} onClick={() => acknowledgeAlert(a.id)}>
                                                Acknowledge Alert
                                            </button>
                                        )}
                                        {a.status === 'ACKNOWLEDGED' && (
                                            <>
                                                <button style={btnPrimary} onClick={() => respondingAlert(a.id)}>
                                                    Mark Responding
                                                </button>
                                                <button style={btnSecondary} onClick={() => resolveAlert(a.id)}>
                                                    Resolve Alert
                                                </button>
                                            </>
                                        )}
                                        {a.status === 'RESPONDING' && (
                                            <button style={btnSuccess} onClick={() => resolveAlert(a.id)}>
                                                Resolve Alert
                                            </button>
                                        )}
                                        {a.status === 'DISMISSED' && (
                                            <button style={btnSecondary} onClick={() => resolveAlert(a.id)}>
                                                Resolve Dismissed Alert
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                <div className="flex flex-wrap gap-2 mt-4">
                    <button
                        className={`btn btn-sm ${!showDismissed ? '' : 'btn-muted'}`}
                        onClick={() => setShowDismissed(v => !v)}
                    >
                        {showDismissed ? 'Hide Dismissed' : 'Show Dismissed'}
                    </button>
                    <button
                        className={`btn btn-sm ${!showResolved ? '' : 'btn-muted'}`}
                        onClick={() => setShowResolved(v => !v)}
                    >
                        {showResolved ? 'Hide Resolved' : 'Show Resolved'}
                    </button>
                </div>
            </div>
            )}

            {tab === 'history' && (
            <div className="card">
                <h3 className="section-title">Alert History</h3>
                <div
                    className="mb-4"
                    style={{
                        display: 'grid',
                        gridTemplateColumns: '2fr 1fr 2fr 2fr auto auto',
                        gap: 10,
                        alignItems: 'center',
                    }}
                >
                    <input className="input" placeholder="Kiosk ID" value={historyFilters.kiosk_id} onChange={e => setHistoryFilters({ ...historyFilters, kiosk_id: e.target.value })} />
                    <input className="input" placeholder="Tier" value={historyFilters.tier} onChange={e => setHistoryFilters({ ...historyFilters, tier: e.target.value })} />
                    <input className="input" placeholder="From (ISO date)" value={historyFilters.from} onChange={e => setHistoryFilters({ ...historyFilters, from: e.target.value })} />
                    <input className="input" placeholder="To (ISO date)" value={historyFilters.to} onChange={e => setHistoryFilters({ ...historyFilters, to: e.target.value })} />
                    <button className="btn btn-sm" style={{ minWidth: 88 }} onClick={fetchHistory}>Apply</button>
                    <button className="btn btn-sm" style={{ minWidth: 110 }} onClick={exportHistoryCsv}>Export CSV</button>
                </div>
                {historyAlerts.length === 0 ? (
                    <p className="text-muted">No resolved alerts.</p>
                ) : (
                    <div style={{ overflow: 'auto', border: '1px solid var(--line)', borderRadius: 10 }}>
                        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
                            <thead>
                                <tr>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Kiosk</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Tier</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Time</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Language</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Transcript</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Response Time</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Resolution Time</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Resolved By</th>
                                    <th style={{ textAlign: 'left', padding: '12px 10px' }}>Notes</th>
                                </tr>
                            </thead>
                            <tbody>
                                {historyAlerts.map((a) => (
                                    <tr key={a.id}>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>{a.kiosk_name || a.kiosk_location || a.kiosk_id}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>{a.tier || 1}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>{new Date(a.timestamp).toLocaleString()}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>{a.language || 'en'}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top', maxWidth: 340 }}>{(a.transcript || '').slice(0, 120)}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>{formatDuration(a.timestamp, a.responding_at)}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>{formatDuration(a.timestamp, a.resolved_at)}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>{a.resolved_by || '-'}</td>
                                        <td style={{ padding: '12px 10px', verticalAlign: 'top', maxWidth: 260 }}>{a.resolution_notes || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
            )}

            {/* Connected Kiosks with editable name */}
            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="section-title" style={{ border: 'none', margin: 0, padding: 0 }}>
                        Connected Kiosks ({kiosks.length})
                    </h3>
                    <button className="btn btn-sm" onClick={load}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
                <div style={{ overflow: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Kiosk ID</th>
                                <th>Kiosk Name</th>
                                <th>IP Address</th>
                                <th>Last Seen</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {kiosks.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="empty-state">No kiosks connected yet.</td>
                                </tr>
                            ) : (
                                kiosks.map((k) => (
                                    <tr key={k.kiosk_id}>
                                        <td className="font-mono text-sm">{k.kiosk_id}</td>
                                        <td>
                                            {editingKiosk === k.kiosk_id ? (
                                                <input
                                                    className="input"
                                                    style={{ width: '100%', minWidth: 120 }}
                                                    value={editName}
                                                    onChange={(e) => setEditName(e.target.value)}
                                                    onBlur={() => saveKioskName(k.kiosk_id)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') saveKioskName(k.kiosk_id);
                                                        if (e.key === 'Escape') { setEditingKiosk(null); setEditName(''); }
                                                    }}
                                                    autoFocus
                                                />
                                            ) : (
                                                <span
                                                    className="cursor-pointer hover:underline"
                                                    onClick={() => {
                                                        setEditingKiosk(k.kiosk_id);
                                                        setEditName(k.kiosk_name || k.kiosk_id);
                                                    }}
                                                    title="Click to edit"
                                                >
                                                    {k.kiosk_name || k.kiosk_id}
                                                </span>
                                            )}
                                        </td>
                                        <td className="font-mono text-sm">{k.ip || '—'}</td>
                                        <td className="text-sm text-muted">
                                            {k.last_seen ? new Date(k.last_seen + 'Z').toLocaleTimeString() : '—'}
                                        </td>
                                        <td>
                                            <span className={`status-dot ${k.status === 'online' ? 'online' : 'offline'}`}></span>
                                            <span className="text-sm ml-1">{k.status || 'online'}</span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default EmergencyCalls;
