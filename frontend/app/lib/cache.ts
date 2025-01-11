// app/lib/cache.ts
import { CopertineEntry, PaginationInfo } from '@/app/types/copertine';
import { getWeaviateClient } from '@/app/lib/weaviate';
import { WeaviateGetResponse } from '@/app/types/weaviate';
import { 
    COPERTINEPERPAGE,
    PREFETCH_PAGES,
    CACHE_INVALIDATION_HOUR,
    CACHE_INVALIDATION_MINUTE,
    CACHE_REFRESH_HOUR,
    CACHE_REFRESH_MINUTE
} from '@/app/constants';

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
    private prefetchPromise: Promise<void> | null = null;

    private constructor() {
        // Start background prefetch when cache is instantiated
        this.startBackgroundPrefetch();
    }

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
            CACHE_INVALIDATION_HOUR,
            CACHE_INVALIDATION_MINUTE
        );
        const refreshTime = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate(),
            CACHE_REFRESH_HOUR,
            CACHE_REFRESH_MINUTE
        );

        return now >= invalidationTime && now <= refreshTime;
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
            .withLimit(COPERTINEPERPAGE)
            .withOffset(offset)
            .do() as WeaviateGetResponse;

        // Get total count
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
                limit: COPERTINEPERPAGE,
                hasMore: offset + COPERTINEPERPAGE < totalCount
            },
            timestamp: Date.now()
        };
    }

    private async startBackgroundPrefetch(): Promise<void> {
        if (this.prefetchPromise) return;

        this.prefetchPromise = (async () => {
            console.log('Starting background prefetch...');
            try {
                // Prefetch pages sequentially to avoid overwhelming Weaviate
                for (let i = 0; i < PREFETCH_PAGES; i++) {
                    const offset = i * COPERTINEPERPAGE;
                    if (!this.isValid(offset)) {
                        const data = await this.fetchPageData(offset);
                        this.set(offset, data);
                        console.log(`Prefetched page ${i + 1}/${PREFETCH_PAGES}`);
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

        if (this.shouldInvalidateCache()) {
            return false;
        }

        const now = new Date();
        const cacheDate = new Date(cacheEntry.timestamp);
        if (cacheDate.getDate() !== now.getDate() ||
            cacheDate.getMonth() !== now.getMonth() ||
            cacheDate.getFullYear() !== now.getFullYear()) {
            return false;
        }

        return true;
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
    }

    clear(): void {
        this.cache = {};
        // Restart background prefetch after clearing
        this.startBackgroundPrefetch();
    }
}

export const copertineCache = CopertineCache.getInstance();