const rawHubUrl = import.meta.env.VITE_HUB_API_URL?.trim();

export const hubHttpBaseUrl = rawHubUrl
    ? rawHubUrl.replace(/\/+$/, '')
    : '/';

export function hubUrl(path = '') {
    if (!path) return hubHttpBaseUrl;
    if (/^https?:\/\//i.test(path)) return path;

    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    if (hubHttpBaseUrl === '/') return normalizedPath;

    return `${hubHttpBaseUrl}${normalizedPath}`;
}

export function hubRealtimeUrl(path) {
    const absolute = hubUrl(path);
    if (absolute.startsWith('https://')) return absolute.replace(/^https:/, 'wss:');
    if (absolute.startsWith('http://')) return absolute.replace(/^http:/, 'ws:');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${absolute}`;
}
