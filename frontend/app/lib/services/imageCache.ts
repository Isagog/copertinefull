// app/lib/services/imageCache.ts
import { CACHE } from '../config/constants';

class ImagePathCache {
    private static instance: ImagePathCache;
    private cache: Map<string, string> = new Map();
    private lastCacheRefresh: Date | null = null;
    private STORAGE_KEY = 'image-path-cache';
    private LAST_REFRESH_KEY = 'image-path-cache-last-refresh';

    private constructor() {
        this.loadFromStorage();
    }

    static getInstance(): ImagePathCache {
        if (!ImagePathCache.instance) {
            ImagePathCache.instance = new ImagePathCache();
        }
        return ImagePathCache.instance;
    }

    private loadFromStorage() {
        if (typeof window !== 'undefined') {
            // Load last refresh time
            const storedRefresh = localStorage.getItem(this.LAST_REFRESH_KEY);
            this.lastCacheRefresh = storedRefresh ? new Date(storedRefresh) : null;

            // Load cached paths
            const storedCache = localStorage.getItem(this.STORAGE_KEY);
            if (storedCache) {
                try {
                    const parsed = JSON.parse(storedCache);
                    this.cache = new Map(parsed);
                } catch (e) {
                    console.error('Failed to parse cached image paths');
                    this.cache = new Map();
                }
            }
        }
    }

    private saveToStorage() {
        if (typeof window !== 'undefined') {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(Array.from(this.cache.entries())));
            if (this.lastCacheRefresh) {
                localStorage.setItem(this.LAST_REFRESH_KEY, this.lastCacheRefresh.toISOString());
            }
        }
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

    getImagePath(filename: string): string {
        if (this.shouldInvalidateCache()) {
            // Only clear if we actually find a new image
            const path = `/images/${filename}`;
            if (!this.cache.has(filename)) {
                this.cache.clear();
                this.lastCacheRefresh = new Date();
                this.saveToStorage();
            }
            this.cache.set(filename, path);
            return path;
        }
        
        let path = this.cache.get(filename);
        if (!path) {
            path = `/images/${filename}`;
            this.cache.set(filename, path);
            this.saveToStorage();
        }
        return path;
    }
}

export const imagePathCache = ImagePathCache.getInstance();