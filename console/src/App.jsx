import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, Link, useLocation, useNavigate, Navigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, Wifi, WifiOff, Terminal, Phone, MessageSquare, Moon, Sun, AlertTriangle, X, LogOut, User as UserIcon } from 'lucide-react';
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
import Login from './pages/Login';

function App() {
    const [user, setUser] = useState(null);
    const [authLoading, setAuthLoading] = useState(true);
    const [emergencyMode, setEmergencyMode] = useState(false);
    const [activeAlertCount, setActiveAlertCount] = useState(0);
    const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
    const [serialConnected, setSerialConnected] = useState(null);
    const [serialDismissed, setSerialDismissed] = useState(false);
    const prevSerialConnected = useRef(null);
    const location = useLocation();
    const navigate = useNavigate();

    // ── Auth Check ────────────────────────────────────────────────────────
    const checkAuth = async () => {
        try {
            const res = await hubClient.get('/auth/me');
            setUser(res.data.user);
        } catch (e) {
            setUser(null);
        } finally {
            setAuthLoading(false);
        }
    };

    const handleLogout = async () => {
        try {
            await hubClient.post('/auth/logout');
            setUser(null);
            navigate('/login');
        } catch (e) {
            console.error("Logout failed", e);
        }
    };

    useEffect(() => {
        checkAuth();
    }, []);

    // ── Serial / LoRa status polling ──────────────────────────────────────
    useEffect(() => {
        if (!user) return;
        const checkSerial = async () => {
            try {
                const res = await hubClient.get('/lora/status');
                const connected = !!res.data.connected;
                setSerialConnected(connected);
                if (prevSerialConnected.current === true && !connected) {
                    setSerialDismissed(false);
                }
                prevSerialConnected.current = connected;
            } catch (e) { }
        };
        checkSerial();
        const interval = setInterval(checkSerial, 5000);
        return () => clearInterval(interval);
    }, [user]);

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
        localStorage.setItem('theme', darkMode ? 'dark' : 'light');
    }, [darkMode]);

    const isTruthy = (v) => {
        if (v === true) return true;
        if (typeof v === 'string') {
            const s = v.trim().toLowerCase();
            return s === 'true' || s === '1' || s === 'yes';
        }
        if (typeof v === 'number') return v === 1;
        return false;
    };

    useEffect(() => {
        if (!user) return;
        const checkStatus = async () => {
            try {
                // Admin ping is protected, but we are logged in now
                await hubClient.get('/admin/ping');
                const snap = await hubClient.get('/kb/snapshot');
                if (snap.data.structured_config && isTruthy(snap.data.structured_config.emergency_mode)) {
                    setEmergencyMode(true);
                } else {
                    setEmergencyMode(false);
                }
            } catch (e) {
                if (e.response?.status === 401) setUser(null); // Session expired
            }
        };
        checkStatus();
        const interval = setInterval(checkStatus, 10000);
        return () => clearInterval(interval);
    }, [user]);

    useEffect(() => {
        if (!user) return;
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
    }, [user]);

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

    if (authLoading) {
        return <div className="app-shell flex items-center justify-center">
            <div className="text-muted">Loading ResKiosk...</div>
        </div>;
    }

    if (!user && location.pathname !== '/login') {
        return <Navigate to="/login" replace />;
    }

    if (location.pathname === '/login') {
        return <Login onLoginSuccess={(u) => { setUser(u); navigate('/'); }} />;
    }

    return (
        <div className="app-shell">
            {emergencyMode && (
                <div className="banner-emergency">
                    ⚠ EMERGENCY MODE ACTIVE
                </div>
            )}
            {activeAlertCount > 0 && (
                <div className="banner-emergency" style={{ backgroundColor: '#b71c1c' }}>
                    <span className="pulse-dot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: '#fff', marginRight: 8, animation: 'pulse 1s ease-in-out infinite' }}></span>
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

                    <div className="mt-auto space-y-1 p-3">
                        <div className="flex items-center gap-3 px-3 py-2 text-sm text-muted mb-2">
                            <UserIcon size={16} />
                            <span className="truncate">{user?.fname || user?.email}</span>
                        </div>
                        <button className="theme-toggle w-full" onClick={() => setDarkMode(d => !d)}>
                            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                            <span>{darkMode ? 'Light' : 'Night'}</span>
                        </button>
                        <button className="theme-toggle w-full text-danger" onClick={handleLogout}>
                            <LogOut size={16} />
                            <span>Logout</span>
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
                        <Route path="/login" element={<Navigate to="/" replace />} />
                    </Routes>
                </main>
            </div>

            {/* Serial Disconnected Modal */}
            {serialConnected === false && !serialDismissed && (
                <div className="modal-overlay">
                    <div className="modal-content max-w-md">
                        <div className="modal-header border-danger/10 bg-danger/5">
                            <div className="flex items-center gap-3">
                                <div className="icon-circle bg-danger/10 text-danger">
                                    <WifiOff size={18} />
                                </div>
                                <h2 className="text-danger font-bold">Serial Device Disconnected</h2>
                            </div>
                            <button onClick={() => setSerialDismissed(true)} className="text-muted hover:text-white">
                                <X size={18} />
                            </button>
                        </div>
                        <div className="p-6">
                            <div className="alert-box bg-danger/5 border-danger/10 mb-4">
                                <AlertTriangle size={20} className="text-warning flex-shrink-0" />
                                <div className="text-sm">
                                    <strong>No ESP+LoRa device is connected.</strong>
                                    <br />
                                    Inter-hub communication is unavailable.
                                </div>
                            </div>
                            <div className="flex justify-end gap-3">
                                <button onClick={() => setSerialDismissed(true)} className="btn btn-muted btn-sm">Dismiss</button>
                                <button onClick={() => { setSerialDismissed(true); navigate('/messages'); }} className="btn btn-primary btn-sm flex items-center gap-2">
                                    <Wifi size={14} /> Hub Messages
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
