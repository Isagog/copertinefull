import { CACHE } from '../config/constants';

class ImagePathCache {
    private static instance: ImagePathCache;
    private cache: Map<string, string> = new Map();
    private lastCacheRefresh: Date | null = null;

    private constructor() {}  // prevent direct construction

    static getInstance(): ImagePathCache {
        if (!ImagePathCache.instance) {
            ImagePathCache.instance = new ImagePathCache();
        }
        return ImagePathCache.instance;
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
            this.cache.clear();
            this.lastCacheRefresh = new Date();
        }
        
        let path = this.cache.get(filename);
        if (!path) {
            path = `/images/${filename}`;
            this.cache.set(filename, path);
        }
        return path;
    }
}

export const imagePathCache = ImagePathCache.getInstance();