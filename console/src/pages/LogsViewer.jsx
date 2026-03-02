import React, { useState, useEffect, useRef } from 'react';
import { useModal } from '../components/ModalProvider';

const LogsViewer = () => {
    const modal = useModal();
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isShuttingDown, setIsShuttingDown] = useState(false);
    const [isRestarting, setIsRestarting] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        // Use the same host/port the console uses
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let hostUrl = window.location.host;

        // If we are in dev (vite on 5173), connect to FastAPI backend on 8000
        if (window.location.port === '5173') {
            hostUrl = window.location.hostname + ':8000';
        }

        const wsUrl = `${protocol}//${hostUrl}/ws/logs`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            setLogs(prev => {
                const newLogs = [...prev, event.data];
                // Keep max 1000 logs in frontend to prevent memory explosion
                if (newLogs.length > 1000) {
                    return newLogs.slice(newLogs.length - 1000);
                }
                return newLogs;
            });
        };

        ws.onclose = () => {
            setIsConnected(false);
            setLogs(prev => [...prev, '\n[System] Disconnected from log stream. Retrying...']);
        };

        ws.onerror = (error) => {
            console.error("WebSocket error", error);
        };

        return () => {
            ws.close();
        };
    }, []);

    // Intentionally no auto-scroll: keep user position stable while logs stream in.

    const getBaseUrl = () => {
        if (window.location.port === '5173') {
            return `${window.location.protocol}//${window.location.hostname}:8000`;
        }
        return '';
    };

    const handleShutdown = async () => {
        if (!(await modal.confirm('Are you sure you want to turn off ResKiosk Hub? All connected kiosks will lose connectivity.'))) {
            return;
        }

        setIsShuttingDown(true);
        try {
            await fetch(`${getBaseUrl()}/admin/shutdown`, { method: 'POST' });
        } catch (e) {
            // Expected — server dies before response completes
        }
    };

    const handleRestart = async () => {
        if (!(await modal.confirm('Restart the Hub? It will turn off and start again in a few seconds. Reconnect to the console after it comes back.'))) {
            return;
        }

        setIsRestarting(true);
        try {
            const res = await fetch(`${getBaseUrl()}/admin/restart`, { method: 'POST' });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                await modal.alert(data.message || 'Restart not available.');
                setIsRestarting(false);
            }
        } catch (e) {
            // Expected if server dies before response
        }
    };

    return (
        <div className="page-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="page-header" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <h1 className="page-title">
                        System Logs
                        <span style={{
                            marginLeft: '12px',
                            fontSize: '12px',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            background: isConnected ? '#e6f4ea' : '#fce8e6',
                            color: isConnected ? '#1e8e3e' : '#d93025'
                        }}>
                            {isConnected ? 'LIVE' : 'DISCONNECTED'}
                        </span>
                    </h1>
                    <p className="page-subtitle">Real-time terminal output from the Hub server.</p>
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button
                        onClick={handleRestart}
                        disabled={isRestarting || isShuttingDown || !isConnected}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: 'none',
                            background: (isRestarting || isShuttingDown) ? '#999' : '#1a73e8',
                            color: 'white',
                            fontWeight: '600',
                            fontSize: '14px',
                            cursor: (isRestarting || isShuttingDown || !isConnected) ? 'not-allowed' : 'pointer',
                            opacity: !isConnected ? 0.5 : 1,
                            transition: 'all 0.2s ease',
                            whiteSpace: 'nowrap',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.15)'
                        }}
                    >
                        {isRestarting ? 'Restarting...' : '↻ Restart Hub'}
                    </button>
                    <button
                        onClick={handleShutdown}
                        disabled={isShuttingDown || isRestarting || !isConnected}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: 'none',
                            background: isShuttingDown ? '#999' : '#d93025',
                            color: 'white',
                            fontWeight: '600',
                            fontSize: '14px',
                            cursor: isShuttingDown || !isConnected ? 'not-allowed' : 'pointer',
                            opacity: !isConnected ? 0.5 : 1,
                            transition: 'all 0.2s ease',
                            whiteSpace: 'nowrap',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.15)'
                        }}
                    >
                        {isShuttingDown ? 'Shutting down...' : '⏻ Turn Off ResKiosk'}
                    </button>
                </div>
            </div>

            <div style={{
                flex: 1,
                background: '#0c0c0c',
                borderRadius: '8px',
                padding: '16px',
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '13px',
                color: '#cccccc',
                boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)',
                margin: '0',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all'
            }}>
                {logs.map((log, index) => {
                    // Quick coloring for INFO/ERROR/WARNING
                    let color = '#cccccc';
                    if (log.includes('INFO:')) color = '#4caf50'; // Green
                    if (log.includes('WARNING:')) color = '#ffeb3b'; // Yellow
                    if (log.includes('ERROR:')) color = '#f44336'; // Red

                    return (
                        <div key={index} style={{ marginBottom: '2px' }}>
                            <span style={{ color }}>{log.substring(0, log.indexOf(':') + 1)}</span>
                            {log.substring(log.indexOf(':') + 1)}
                        </div>
                    );
                })}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default LogsViewer;
