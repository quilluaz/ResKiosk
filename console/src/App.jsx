import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, Wifi, WifiOff, Terminal, Phone, MessageSquare, Moon, Sun, AlertTriangle, X } from 'lucide-react';
import hubClient from './api/hubClient';
import logoSvg from './assets/reskiosk-logo.svg';

// Pages
import Dashboard from './pages/Dashboard';
import KBViewer from './pages/KBViewer';
import FAQManager from './pages/FAQManager';
import ShelterConfig from './pages/ShelterConfig';
import NetworkSetup from './pages/NetworkSetup';
import LogsViewer from './pages/LogsViewer';
import EmergencyCalls from './pages/EmergencyCalls';
import HubMessages from './pages/HubMessages';

function App() {
    const [emergencyMode, setEmergencyMode] = useState(false);
    const [activeAlertCount, setActiveAlertCount] = useState(0);
    const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
    const [serialConnected, setSerialConnected] = useState(null); // null = unknown, true/false
    const [serialDismissed, setSerialDismissed] = useState(false);
    const prevSerialConnected = useRef(null);
    const location = useLocation();
    const navigate = useNavigate();

    // ── Serial / LoRa status polling ──────────────────────────────────────
    useEffect(() => {
        const checkSerial = async () => {
            try {
                const res = await hubClient.get('/lora/status');
                const connected = !!res.data.connected;
                setSerialConnected(connected);
                // Re-show modal on new disconnect (was connected, now disconnected)
                if (prevSerialConnected.current === true && !connected) {
                    setSerialDismissed(false);
                }
                prevSerialConnected.current = connected;
            } catch (e) {
                // API unreachable — don't show serial modal (hub itself is down)
            }
        };
        checkSerial();
        const interval = setInterval(checkSerial, 5000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
        localStorage.setItem('theme', darkMode ? 'dark' : 'light');
    }, [darkMode]);

    useEffect(() => {
        const checkStatus = async () => {
            try {
                await hubClient.get('/admin/ping');
                const emergency = await hubClient.get('/admin/emergency_mode');
                setEmergencyMode(!!emergency.data?.active);
            } catch (e) {
                console.error("Status check failed", e);
            }
        };
        checkStatus();
        const interval = setInterval(checkStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const fetchAlerts = async () => {
            try {
                const res = await hubClient.get('/emergency/active');
                const onlyActive = (res.data.alerts || []).filter(
                    (a) => (a?.status || 'ACTIVE').toUpperCase() === 'ACTIVE'
                );
                setActiveAlertCount(onlyActive.length);
            } catch (e) { }
        };
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 5000);
        return () => clearInterval(interval);
    }, []);

    const NavItem = ({ to, icon: Icon, label, highlight }) => {
        const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
        const isExactRoot = to === '/' && location.pathname === '/';
        const active = isActive || isExactRoot;
        return (
            <Link to={to}
                className={`nav-item ${active ? 'active' : ''} ${highlight ? 'highlight' : ''}`}
            >
                <Icon size={18} />
                <span>{label}</span>
            </Link>
        );
    };

    return (
        <div className="app-shell">
            {emergencyMode && (
                <div className="banner-emergency">
                    <AlertTriangle size={18} />
                    <span>EMERGENCY MODE ACTIVE</span>
                </div>
            )}
            {activeAlertCount > 0 && (
                <div className="banner-emergency" style={{ borderBottomColor: 'rgba(255, 150, 0, 0.8)', animation: 'none' }}>
                    <span className="pulse-dot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: '#fff', animation: 'pulse-border 1.5s ease-in-out infinite' }}></span>
                    <strong>{activeAlertCount}</strong> active emergency alert(s) —
                    <Link to="/emergency" style={{ color: '#fff', textDecoration: 'underline', marginLeft: 6 }}>View now</Link>
                </div>
            )}

            <div className="app-layout">
                {/* Sidebar */}
                <aside className="sidebar">
                    <div className="sidebar-header">
                        <div className="sidebar-brand">
                            <img src={logoSvg} alt="ResKiosk" />
                            <h1>ResKiosk Hub</h1>
                        </div>
                    </div>

                    <nav className="sidebar-nav">
                        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" />

                        <NavItem to="/config" icon={Settings} label="Shelter Config" />
                        <NavItem to="/network" icon={Wifi} label="Network Setup" />
                        <NavItem to="/emergency" icon={Phone} label="Emergency Calls" />
                        <NavItem to="/messages" icon={MessageSquare} label="Hub Messages" />
                        <NavItem to="/logs" icon={Terminal} label="Logs" highlight={false} />
                    </nav>

                    <div style={{ padding: '0.75rem' }}>
                        <button className="theme-toggle" onClick={() => setDarkMode(d => !d)}>
                            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                            <span>{darkMode ? 'Light Mode' : 'Night Mode'}</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Dashboard setEmergencyMode={setEmergencyMode} />} />
                        <Route path="/kb" element={<KBViewer />} />

                        <Route path="/faq/:id/edit" element={<FAQManager isNew={false} />} />
                        <Route path="/config" element={<ShelterConfig />} />
                        <Route path="/network" element={<NetworkSetup />} />
                        <Route path="/emergency" element={<EmergencyCalls />} />
                        <Route path="/messages" element={<HubMessages />} />
                        <Route path="/logs" element={<LogsViewer />} />
                    </Routes>
                </main>
            </div>

            {/* Serial Disconnected Modal */}
            {serialConnected === false && !serialDismissed && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 9999,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(0, 0, 0, 0.6)',
                    backdropFilter: 'blur(4px)',
                    animation: 'fadeIn 0.25s ease',
                }}>
                    <div style={{
                        background: 'var(--surface)',
                        backdropFilter: 'blur(24px)',
                        WebkitBackdropFilter: 'blur(24px)',
                        borderRadius: '16px',
                        border: '1px solid rgba(239, 83, 80, 0.5)',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(239,83,80,0.15)',
                        maxWidth: '28rem',
                        width: '90%',
                        overflow: 'hidden',
                        animation: 'slideUp 0.3s ease',
                    }}>
                        {/* Header */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '1rem 1.25rem',
                            borderBottom: '1px solid var(--border, #333)',
                            background: 'rgba(239, 83, 80, 0.08)',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                                <div style={{
                                    width: 36, height: 36, borderRadius: '50%',
                                    background: 'rgba(239, 83, 80, 0.15)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                }}>
                                    <WifiOff size={18} style={{ color: 'var(--danger, #ef5350)' }} />
                                </div>
                                <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--danger, #ef5350)' }}>
                                    Serial Device Disconnected
                                </h2>
                            </div>
                            <button
                                onClick={() => setSerialDismissed(true)}
                                style={{
                                    background: 'transparent', border: 'none', cursor: 'pointer',
                                    padding: '0.25rem', borderRadius: '6px', color: 'var(--text-muted, #999)',
                                }}
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Body */}
                        <div style={{ padding: '1.5rem 1.25rem' }}>
                            <div style={{
                                display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                                background: 'rgba(239, 83, 80, 0.06)',
                                borderRadius: '10px', padding: '1rem',
                                border: '1px solid rgba(239, 83, 80, 0.12)',
                                marginBottom: '1.25rem',
                            }}>
                                <AlertTriangle size={20} style={{ color: '#ffa726', flexShrink: 0, marginTop: 2 }} />
                                <div style={{ fontSize: '0.875rem', lineHeight: 1.6, color: 'var(--text, #e0e0e0)' }}>
                                    <strong>No ESP+LoRa device is connected to this hub.</strong>
                                    <br />
                                    LoRa messaging and inter-hub communication are unavailable until a serial device is connected.
                                </div>
                            </div>

                            <div style={{
                                display: 'flex', gap: '0.75rem', justifyContent: 'flex-end',
                            }}>
                                <button
                                    onClick={() => setSerialDismissed(true)}
                                    style={{
                                        padding: '0.5rem 1rem', borderRadius: '8px',
                                        border: '1px solid var(--border, #444)',
                                        background: 'transparent', color: 'var(--text, #e0e0e0)',
                                        cursor: 'pointer', fontSize: '0.85rem', fontWeight: 500,
                                    }}
                                >
                                    Dismiss
                                </button>
                                <button
                                    onClick={() => { setSerialDismissed(true); navigate('/messages'); }}
                                    style={{
                                        padding: '0.5rem 1rem', borderRadius: '8px',
                                        border: 'none',
                                        background: 'var(--primary, #42a5f5)', color: '#fff',
                                        cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600,
                                        display: 'flex', alignItems: 'center', gap: '0.375rem',
                                    }}
                                >
                                    <Wifi size={14} /> Go to Hub Messages
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
