// app/lib/cache.ts
import { CopertineEntry, PaginationInfo } from '@/app/types/copertine';

interface CacheEntry {
    data: CopertineEntry[];
    pagination: PaginationInfo;
    timestamp: number;
}

interface PageCache {
    [key: number]: CacheEntry;
}

class CopertineCache {
    private static instance: CopertineCache;
    private cache: PageCache = {};

    private constructor() {}

    static getInstance(): CopertineCache {
        if (!CopertineCache.instance) {
            CopertineCache.instance = new CopertineCache();
        }
        return CopertineCache.instance;
    }

    private shouldInvalidateCache(): boolean {
        const now = new Date();
        const invalidationTime = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate(),
            3, // 3 AM
            45 // 45 minutes
        );
        const refreshTime = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate(),
            4, // 4 AM
            30 // 30 minutes
        );

        // If we're between invalidation and refresh time, the cache should be invalid
        return now >= invalidationTime && now <= refreshTime;
    }

    isValid(offset: number): boolean {
        const cacheEntry = this.cache[offset];
        if (!cacheEntry) return false;

        // Check if we're in the invalidation window
        if (this.shouldInvalidateCache()) {
            return false;
        }

        // Check if the cache entry is from a previous day
        const now = new Date();
        const cacheDate = new Date(cacheEntry.timestamp);
        if (cacheDate.getDate() !== now.getDate() ||
            cacheDate.getMonth() !== now.getMonth() ||
            cacheDate.getFullYear() !== now.getFullYear()) {
            return false;
        }

        return true;
    }

    get(offset: number): CacheEntry | null {
        if (!this.isValid(offset)) {
            return null;
        }
        return this.cache[offset];
    }

    set(offset: number, entry: CacheEntry): void {
        this.cache[offset] = {
            ...entry,
            timestamp: Date.now()
        };
    }

    clear(): void {
        this.cache = {};
    }
}

export const copertineCache = CopertineCache.getInstance();