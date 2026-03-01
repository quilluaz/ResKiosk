import axios from 'axios';

// Create instance
// Since console is served from the same origin as the API (in prod), we use relative paths.
// In dev (Vite), we might need a proxy or full URL. 
// For now, assuming relative '/' works if served by Hub, 
// OR Vite proxy is set up. 
// BUT "Do not introduce runtime internet" -> Localhub.
// Let's use relative path, assuming production environment or proxy.
const hubClient = axios.create({
    baseURL: '/', // Points to http://localhost:8000/ when served
    timeout: 5000,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Response interceptor for error logger
hubClient.interceptors.response.use(
    respons => respons,
    error => {
        console.error('Hub API Error:', error);
        return Promise.reject(error);
    }
);

export default hubClient;
