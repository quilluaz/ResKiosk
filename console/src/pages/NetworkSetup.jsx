import React, { useEffect, useMemo, useState } from 'react';
import hubClient from '../api/hubClient';
import { QRCodeSVG } from 'qrcode.react';
import { Copy, Pencil, RefreshCw } from 'lucide-react';

function NetworkSetup() {
    const [netInfo, setNetInfo] = useState({ ip: '...', port: 8000 });
    const [loading, setLoading] = useState(true);
    const [editingKioskId, setEditingKioskId] = useState(null);
    const [draftKioskName, setDraftKioskName] = useState('');
    const [savingKioskName, setSavingKioskName] = useState(false);

    const fetchInfo = async () => {
        try {
            setLoading(true);
            const res = await hubClient.get('/network/info');
            setNetInfo(res.data || {});
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInfo();
        const interval = setInterval(fetchInfo, 10000);
        return () => clearInterval(interval);
    }, []);

    const hubUrl = useMemo(() => `http://${netInfo.ip}:${netInfo.port}`, [netInfo.ip, netInfo.port]);

    const startEditKioskName = (kiosk) => {
        setEditingKioskId(kiosk.kiosk_id);
        setDraftKioskName((kiosk.kiosk_name || kiosk.kiosk_id || '').trim());
    };

    const cancelEditKioskName = () => {
        setEditingKioskId(null);
        setDraftKioskName('');
    };

    const saveKioskName = async (kioskId) => {
        const next = draftKioskName.trim();
        if (!next) return;
        try {
            setSavingKioskName(true);
            await hubClient.post('/network/kiosk/name', {
                kiosk_id: kioskId,
                kiosk_name: next,
            });
            await fetchInfo();
            setEditingKioskId(null);
            setDraftKioskName('');
        } catch (e) {
            console.error(e);
            alert(e?.response?.data?.message || 'Failed to update kiosk name.');
        } finally {
            setSavingKioskName(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center gap-4">
                <h1 className="page-title">Network Setup</h1>
            </div>

            <div className="grid-2">
                <div className="hub-url-card">
                    <h3>Hub URL</h3>
                    <div className="hub-url-display">
                        <code>{hubUrl}</code>
                        <button
                            className="btn btn-sm"
                            onClick={() => navigator.clipboard.writeText(hubUrl)}
                            title="Copy to clipboard"
                        >
                            <Copy size={16} />
                        </button>
                    </div>
                    <p className="text-sm mt-2" style={{ color: 'var(--primary)' }}>
                        Enter this URL in Kiosk setup.
                    </p>
                </div>

                <div className="card qr-card">
                    <h3>Scan to Connect</h3>
                    <div className="p-4 rounded border" style={{ display: 'inline-block', backgroundColor: 'white', borderColor: 'white' }}>
                        <QRCodeSVG value={hubUrl} size={150} />
                    </div>
                </div>
            </div>


            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="section-title" style={{ border: 'none', margin: 0, padding: 0 }}>
                        Connected Kiosks ({netInfo.connected_kiosks || 0})
                    </h3>
                    <button className="btn btn-sm" onClick={fetchInfo} disabled={loading}>
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
                            {(!netInfo.kiosks_list || netInfo.kiosks_list.length === 0) ? (
                                <tr>
                                    <td colSpan="5" className="empty-state">
                                        No kiosks connected yet.
                                    </td>
                                </tr>
                            ) : (
                                netInfo.kiosks_list.map((kiosk) => (
                                    <tr key={kiosk.kiosk_id}>
                                        <td style={{ fontWeight: 500 }}>{kiosk.kiosk_id}</td>
                                        <td className="kiosk-name-cell">
                                            {editingKioskId === kiosk.kiosk_id ? (
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        className="input"
                                                        value={draftKioskName}
                                                        onChange={(e) => setDraftKioskName(e.target.value)}
                                                        autoFocus
                                                        maxLength={80}
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Enter') saveKioskName(kiosk.kiosk_id);
                                                            if (e.key === 'Escape') cancelEditKioskName();
                                                        }}
                                                        style={{ maxWidth: '16rem', height: '2rem' }}
                                                    />
                                                    <button
                                                        className="btn btn-sm btn-primary"
                                                        disabled={savingKioskName || !draftKioskName.trim()}
                                                        onClick={() => saveKioskName(kiosk.kiosk_id)}
                                                    >
                                                        Save
                                                    </button>
                                                    <button
                                                        className="btn btn-sm"
                                                        disabled={savingKioskName}
                                                        onClick={cancelEditKioskName}
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            ) : (
                                                <div
                                                    className="kiosk-name-display"
                                                    onClick={() => startEditKioskName(kiosk)}
                                                    title="Edit kiosk name"
                                                    role="button"
                                                    tabIndex={0}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter' || e.key === ' ') {
                                                            e.preventDefault();
                                                            startEditKioskName(kiosk);
                                                        }
                                                    }}
                                                >
                                                    <span>{kiosk.kiosk_name || kiosk.kiosk_id}</span>
                                                    <Pencil size={13} className="kiosk-name-pencil" />
                                                </div>
                                            )}
                                        </td>
                                        <td className="font-mono text-sm">{kiosk.ip}</td>
                                        <td className="text-sm text-muted">{new Date(`${kiosk.last_seen}Z`).toLocaleTimeString()}</td>
                                        <td>
                                            <span className="flex items-center gap-2">
                                                <span className={`status-dot ${kiosk.status === 'online' ? 'online' : 'offline'}`}></span>
                                                <span className="text-sm">{kiosk.status}</span>
                                            </span>
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

export default NetworkSetup;
