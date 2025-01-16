// app/lib/services/cache.ts
import { CopertineEntry, PaginationInfo } from '@/app/types/copertine';
import { getWeaviateClient } from './weaviate';
import { WeaviateGetResponse } from '@/app/types/weaviate';
import { PAGINATION, CACHE } from '../config/constants';

interface CacheEntry {
    data: CopertineEntry[];
    pagination: PaginationInfo;
    timestamp: number;
}

interface PageCache {
    [key: number]: CacheEntry;
}

interface WeaviateCopertineItem {
    captionStr: string;
    editionDateIsoStr: string;
    editionId: string;
    editionImageFnStr: string;
    kickerStr: string;
    testataName: string;
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
        const todayUpdate = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate(),
            CACHE.UPDATE_HOUR,
            CACHE.UPDATE_MINUTE
        );

        const cacheDate = new Date(this.lastCacheRefresh);
        const cacheUpdateTime = new Date(
            cacheDate.getFullYear(),
            cacheDate.getMonth(),
            cacheDate.getDate(),
            CACHE.UPDATE_HOUR,
            0  // Minutes set to 0 for the actual update time
        );

        return now >= todayUpdate && this.lastCacheRefresh < cacheUpdateTime;
    }

    private async fetchPageData(offset: number): Promise<CacheEntry> {
        const client = getWeaviateClient();
        
        const result = await client.graphql
            .get()
            .withClassName('Copertine')
            .withFields(`
                captionStr
                editionDateIsoStr
                editionId
                editionImageFnStr
                kickerStr
                testataName
            `)
            .withSort([{ 
                path: ["editionDateIsoStr"], 
                order: "desc" 
            }])
            .withLimit(PAGINATION.ITEMS_PER_PAGE)
            .withOffset(offset)
            .do() as WeaviateGetResponse;

        const countResult = await client.graphql
            .aggregate()
            .withClassName('Copertine')
            .withFields('meta { count }')
            .do();

        const totalCount = countResult.data.Aggregate.Copertine[0].meta.count;

        const mappedData: CopertineEntry[] = result.data.Get.Copertine.map((item: WeaviateCopertineItem) => ({
            extracted_caption: item.captionStr,
            kickerStr: item.kickerStr,
            date: new Date(item.editionDateIsoStr).toLocaleDateString('it-IT'),
            filename: item.editionImageFnStr,
            isoDate: item.editionDateIsoStr
        }));

        return {
            data: mappedData,
            pagination: {
                total: totalCount,
                offset,
                limit: PAGINATION.ITEMS_PER_PAGE,
                hasMore: offset + PAGINATION.ITEMS_PER_PAGE < totalCount
            },
            timestamp: Date.now()
        };
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