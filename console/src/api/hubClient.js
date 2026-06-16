import axios from 'axios';
import { hubHttpBaseUrl } from './endpoints';

// Use VITE_HUB_API_URL when the static console is hosted separately from the hub.
// Default '/' still supports serving the console from the hub itself.
const hubClient = axios.create({
    baseURL: hubHttpBaseUrl,
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

