import axios from 'axios';

// Determine base URL: when served by the hub itself '/' works.
// In Vite dev mode (port 5173), proxy is configured in vite.config.js.
const hubClient = axios.create({
    baseURL: '/',
    timeout: 5000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Request interceptor: attach auth token if one is stored
hubClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('reskiosk_token');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor: handle 401 (stale/expired session) and log errors
hubClient.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401 && !error.config.url.includes('/login')) {
            localStorage.removeItem('reskiosk_token');
            localStorage.removeItem('reskiosk_user');
            window.location.reload();
        }
        console.error('Hub API Error:', error);
        return Promise.reject(error);
    }
);

export default hubClient;

