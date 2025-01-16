// app/lib/config/constants.ts
export const API = {
    FASTAPI_URL: process.env.FASTAPI_URL || 'http://localhost:8008',
    WEAVIATE_SCHEME: process.env.WEAVIATE_SCHEME || 'http',
    WEAVIATE_HOST: process.env.WEAVIATE_HOST || 'localhost:8080'
} as const;

export const PAGINATION = {
    ITEMS_PER_PAGE: 30,
    PREFETCH_PAGES: 15
} as const;

export const CACHE = {
    UPDATE_HOUR: process.env.CACHE_UPDATE_HOUR ? parseInt(process.env.CACHE_UPDATE_HOUR) : 5,
    UPDATE_MINUTE: process.env.CACHE_UPDATE_MINUTE ? parseInt(process.env.CACHE_UPDATE_MINUTE) : 10
} as const;