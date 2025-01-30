// app/lib/config/constants.ts
export const API = {
    BACKEND_URL: process.env.COP_BACKEND_URL || 'http://localhost:8000',
    WEAVIATE_SCHEME: process.env.WEAVIATE_SCHEME || 'http',
    WEAVIATE_HOST: process.env.WEAVIATE_HOST || 'localhost:8080'
} as const;

// Log environment variables in development
if (process.env.NODE_ENV === 'development') {
    console.log('[constants] Environment variables:', {
        COP_BACKEND_URL: process.env.COP_BACKEND_URL,
        NODE_ENV: process.env.NODE_ENV,
        APP_URL: process.env.NEXT_PUBLIC_APP_URL
    });
}

export const PAGINATION = {
    ITEMS_PER_PAGE: 30,
    PREFETCH_PAGES: 15
} as const;

export const CACHE = {
    UPDATE_HOUR: process.env.CACHE_UPDATE_HOUR ? parseInt(process.env.CACHE_UPDATE_HOUR) : 5,
    UPDATE_MINUTE: process.env.CACHE_UPDATE_MINUTE ? parseInt(process.env.CACHE_UPDATE_MINUTE) : 10
} as const;
