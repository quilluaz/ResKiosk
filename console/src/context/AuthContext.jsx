import React, { createContext, useContext, useState, useCallback } from 'react';
import hubClient from '../api/hubClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(() => localStorage.getItem('reskiosk_token'));
    const [user, setUser] = useState(() => {
        const raw = localStorage.getItem('reskiosk_user');
        try { return raw ? JSON.parse(raw) : null; } catch { return null; }
    });

    const login = useCallback(async (username, password) => {
        const res = await hubClient.post('/auth/login', { username, password });
        const { token: newToken, ...userData } = res.data;
        localStorage.setItem('reskiosk_token', newToken);
        localStorage.setItem('reskiosk_user', JSON.stringify(userData));
        setToken(newToken);
        setUser(userData);
        return userData;
    }, []);

    const updateUser = useCallback((updates) => {
        setUser(prev => {
            const next = { ...prev, ...updates };
            localStorage.setItem('reskiosk_user', JSON.stringify(next));
            return next;
        });
    }, []);

    const logout = useCallback(async () => {
        try { await hubClient.post('/auth/logout'); } catch { /* ignore */ }
        localStorage.removeItem('reskiosk_token');
        localStorage.removeItem('reskiosk_user');
        setToken(null);
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ token, user, login, logout, updateUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
