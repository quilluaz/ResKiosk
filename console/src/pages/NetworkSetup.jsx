import React, { useState, useEffect } from 'react';
import hubClient from '../api/hubClient';
import { QRCodeSVG } from 'qrcode.react';
import { Copy, RefreshCw } from 'lucide-react';

function NetworkSetup() {
    const [netInfo, setNetInfo] = useState({ ip: '...', port: 8000 });
    const [config, setConfig] = useState({ network_mode: 'router', ip_override: '', port: 8000 });
    const [peers, setPeers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const fetchInfo = async () => {
        try {
            const res = await hubClient.get('/network/info');
            setNetInfo(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const fetchConfig = async () => {
        try {
            const res = await hubClient.get('/network/config');
            setConfig(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const fetchPeers = async () => {
        try {
            const res = await hubClient.get('/federation/peers');
            setPeers(res.data.peers || []);
        } catch (e) {
            console.error(e);
        }
    };

    const loadData = async () => {
        setLoading(true);
        await Promise.all([fetchInfo(), fetchConfig(), fetchPeers()]);
        setLoading(false);
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleSave = async () => {
        try {
            setSaving(true);
            await hubClient.put('/network/config', config);
            alert('Network settings saved successfully');
            fetchInfo();
        } catch (e) {
            alert('Failed to save settings: ' + (e.response?.data?.detail || e.message));
        } finally {
            setSaving(false);
        }
    };

    const hubUrl = `http://${netInfo.ip}:${netInfo.port}`;

    if (loading) return <div className="p-8 text-muted">Loading network settings...</div>;

    return (
        <div className="space-y-6">
            <h1 className="page-title">Network Setup</h1>

            <div className="grid-2">
                {/* Hub URL Card */}
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
                    <p className="text-sm mt-2" style={{ color: 'var(--primary)' }}>Enter this URL in Kiosk setup.</p>
                </div>

                {/* QR Code */}
                <div className="card qr-card">
                    <h3>Scan to Connect</h3>
                    <div className="p-4 bg-white rounded border" style={{ display: 'inline-block' }}>
                        <QRCodeSVG value={hubUrl} size={150} />
                    </div>
                </div>
            </div>

            {/* Network Configuration */}
            <div className="card space-y-4">
                <h3 className="section-title">Configuration</h3>

                <div className="form-group">
                    <label>Network Mode</label>
                    <select
                        className="input"
                        style={{ maxWidth: '24rem' }}
                        value={config.network_mode}
                        onChange={(e) => setConfig({ ...config, network_mode: e.target.value })}
                    >
                        <option value="router">Using existing Wi-Fi (Recommended)</option>
                        <option value="hotspot">Hub Hosting Hotspot (Standalone)</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>Static IP Override (Optional)</label>
                    <input
                        className="input"
                        style={{ maxWidth: '24rem' }}
                        placeholder="e.g. 192.168.1.100"
                        value={config.ip_override}
                        onChange={(e) => setConfig({ ...config, ip_override: e.target.value })}
                    />
                    <p className="form-hint">Leave empty to use automatic detection.</p>
                </div>

                <div className="form-group">
                    <label>Server Port</label>
                    <input
                        type="number"
                        className="input"
                        style={{ maxWidth: '24rem' }}
                        placeholder="8000"
                        value={config.port}
                        onChange={(e) => setConfig({ ...config, port: parseInt(e.target.value) || 8000 })}
                    />
                </div>

                <button
                    className="btn btn-primary"
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Saving...' : 'Save Network Settings'}
                </button>
            </div>

            {/* Federation Hub Peers */}
            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="section-title" style={{ border: 'none', margin: 0, padding: 0 }}>
                        Federated Hub Peers ({peers.length})
                    </h3>
                    <button className="btn btn-sm" onClick={fetchPeers}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
                <div style={{ overflow: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Hub ID</th>
                                <th>Hub Name</th>
                                <th>Base URL</th>
                                <th>Last Sync</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {peers.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="empty-state">
                                        No other hubs discovered on the network.
                                    </td>
                                </tr>
                            ) : (
                                peers.map((peer) => (
                                    <tr key={peer.peer_hub_id}>
                                        <td style={{ fontWeight: 500 }}>{peer.peer_hub_id}</td>
                                        <td>{peer.peer_name}</td>
                                        <td className="font-mono text-sm">{peer.base_url}</td>
                                        <td className="text-sm text-muted">
                                            {peer.last_sync_at ? new Date(peer.last_sync_at * 1000).toLocaleTimeString() : 'Never'}
                                        </td>
                                        <td>
                                            <span className="flex items-center gap-2">
                                                <span className={`status-dot ${peer.status === 'online' ? 'online' : 'offline'}`}></span>
                                                <span className="text-sm">{peer.status}</span>
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Connected Kiosks */}
            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="section-title" style={{ border: 'none', margin: 0, padding: 0 }}>
                        Connected Kiosks ({netInfo.connected_kiosks || 0})
                    </h3>
                    <button className="btn btn-sm" onClick={fetchInfo}>
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
                                        <td>{kiosk.kiosk_name || kiosk.kiosk_id}</td>
                                        <td className="font-mono text-sm">{kiosk.ip}</td>
                                        <td className="text-sm text-muted">{new Date(kiosk.last_seen + 'Z').toLocaleTimeString()}</td>
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
