export const isMockingEnabled =
    import.meta.env.VITE_USE_MSW === 'true' ||
    (import.meta.env.PROD && import.meta.env.VITE_USE_MSW !== 'false');
