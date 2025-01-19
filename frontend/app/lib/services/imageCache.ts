// app/lib/services/imageCache.ts
import { CACHE, PAGINATION } from '../config/constants';
import { copertineCache } from './cache';

class ImagePathCache {
   private static instance: ImagePathCache;
   private cache: Map<string, string> = new Map();
   private lastCacheRefresh: Date | null = null;
   private prefetchedPages: Set<number> = new Set();
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

   async prefetchNextPage(currentOffset: number) {
       const nextPageOffset = currentOffset + PAGINATION.ITEMS_PER_PAGE;
       
       // If we've already prefetched this page, skip
       if (this.prefetchedPages.has(nextPageOffset)) return;

       try {
           // Get the next page data from existing cache
           const nextPageData = await copertineCache.get(nextPageOffset);
           if (nextPageData) {
               // Prefetch each image in the next page
               nextPageData.data.forEach(copertina => {
                   const path = `/images/${copertina.filename}`;
                   // Create a hidden Image to trigger the browser to load it
                   if (typeof window !== 'undefined') {
                       const img = new Image();
                       img.src = path;
                   }
                   this.cache.set(copertina.filename, path);
               });
               this.prefetchedPages.add(nextPageOffset);
               this.saveToStorage();
           }
       } catch (error) {
           console.error('Error prefetching next page images:', error);
       }
   }

   getImagePath(filename: string, currentOffset?: number): string {
       if (this.shouldInvalidateCache()) {
           // Only clear if we actually find a new image
           const path = `/images/${filename}`;
           if (!this.cache.has(filename)) {
               this.cache.clear();
               this.prefetchedPages.clear();
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

       // If we know the current offset, trigger prefetch of next page
       if (currentOffset !== undefined) {
           this.prefetchNextPage(currentOffset);
       }
       
       return path;
   }
}

export const imagePathCache = ImagePathCache.getInstance();