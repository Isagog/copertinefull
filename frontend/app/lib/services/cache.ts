// app/lib/services/cache.ts
import { CopertineEntry, PaginationInfo } from '@/app/types/copertine';
import { PAGINATION, CACHE } from '../config/constants';

interface CacheEntry {
    data: CopertineEntry[];
    pagination: PaginationInfo;
    timestamp: number;
}

interface PageCache {
    [key: number]: CacheEntry;
}

interface ApiResponse {
    data: CopertineEntry[];
    pagination: {
        total: number;
        offset: number;
        limit: number;
        hasMore: boolean;
    };
}

class CopertineCache {
    private static instance: CopertineCache;
    private cache: PageCache = {};
    private lastCacheRefresh: Date | null = null;
    private prefetchPromise: Promise<void> | null = null;

    private constructor() {
        this.startBackgroundPrefetch();
    }

    static getInstance(): CopertineCache {
        if (!CopertineCache.instance) {
            CopertineCache.instance = new CopertineCache();
        }
        return CopertineCache.instance;
    }

    private shouldInvalidateCache(): boolean {
        if (!this.lastCacheRefresh) return true;
      
        const now = new Date();
        const cacheDate = new Date(this.lastCacheRefresh);
      
        if (now.getDate() !== cacheDate.getDate()) {
            if (now.getHours() >= CACHE.UPDATE_HOUR) {
                return true;
            }
        }
      
        return false;
    }

    private async fetchPageData(offset: number): Promise<CacheEntry> {
        try {
            const baseUrl = typeof window === 'undefined' 
                ? (process.env.NODE_ENV === 'production'
                    ? process.env.NEXT_PUBLIC_BASE_URL || 'https://dev.isagog.com/copertine'
                    : 'http://localhost:3000')
                : '';  // Client-side (relative URL is fine)
                
            const apiUrl = `${baseUrl}/api/copertine?offset=${offset}&limit=${PAGINATION.ITEMS_PER_PAGE}`;
            console.log('Requesting URL:', apiUrl);

            const response = await fetch(apiUrl);
            console.log('Response status:', response.status);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, message: ${JSON.stringify(errorData)}`);
            }

            const result = await response.json() as ApiResponse;
            console.log('Received data:', result);

            return {
                data: result.data,
                pagination: result.pagination,
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error('Error fetching page data:', error);
            throw error;
        }
    }

    private async startBackgroundPrefetch(): Promise<void> {
        if (this.prefetchPromise) return;

        this.prefetchPromise = (async () => {
            console.log('Starting background prefetch...');
            try {
                for (let i = 0; i < PAGINATION.PREFETCH_PAGES; i++) {
                    const offset = i * PAGINATION.ITEMS_PER_PAGE;
                    if (!this.isValid(offset)) {
                        const data = await this.fetchPageData(offset);
                        this.set(offset, data);
                        console.log(`Prefetched page ${i + 1}/${PAGINATION.PREFETCH_PAGES}`);
                        this.lastCacheRefresh = new Date();
                    }
                }
                console.log('Background prefetch completed');
            } catch (error) {
                console.error('Error during background prefetch:', error);
            } finally {
                this.prefetchPromise = null;
            }
        })();
    }

    isValid(offset: number): boolean {
        const cacheEntry = this.cache[offset];
        if (!cacheEntry) return false;
        return !this.shouldInvalidateCache();
    }

    async get(offset: number): Promise<CacheEntry | null> {
        if (!this.isValid(offset)) {
            try {
                const data = await this.fetchPageData(offset);
                this.set(offset, data);
                return data;
            } catch (error) {
                console.error('Error fetching page data:', error);
                return null;
            }
        }
        return this.cache[offset];
    }

    set(offset: number, entry: CacheEntry): void {
        this.cache[offset] = {
            ...entry,
            timestamp: Date.now()
        };
        this.lastCacheRefresh = new Date();
    }

    clear(): void {
        this.cache = {};
        this.lastCacheRefresh = null;
        this.startBackgroundPrefetch();
    }
}

export const copertineCache = CopertineCache.getInstance();