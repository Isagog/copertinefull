// app/api/copertine/route.tsx
import { NextRequest, NextResponse } from 'next/server';
import { getWeaviateClient } from '@app/lib/weaviate';
import { CopertineEntry } from '@app/types/copertine';
import { WeaviateItem, WeaviateGetResponse } from '@app/types/weaviate';
import { copertineCache } from '@app/lib/cache';

export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0');
        const limit = parseInt(searchParams.get('limit') || '50');

        // Check cache first
        const cachedData = copertineCache.get(offset);
        if (cachedData) {
            return NextResponse.json({
                data: cachedData.data,
                pagination: cachedData.pagination,
                cached: true // Optional: for debugging
            });
        }

        const client = getWeaviateClient();
        
        // Fetch fresh data
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
            .withLimit(limit)
            .withOffset(offset)
            .do() as WeaviateGetResponse;

        if (!result.data.Get.Copertine) {
            return NextResponse.json({ error: 'No data found' }, { status: 404 });
        }

        // Get total count for pagination
        const countResult = await client.graphql
            .aggregate()
            .withClassName('Copertine')
            .withFields('meta { count }')
            .do();

        const totalCount = countResult.data.Aggregate.Copertine[0].meta.count;

        const mappedData: CopertineEntry[] = result.data.Get.Copertine.map((item: WeaviateItem) => ({
            extracted_caption: item.captionStr,
            kickerStr: item.kickerStr,
            date: new Date(item.editionDateIsoStr).toLocaleDateString('it-IT'),
            filename: item.editionImageFnStr,
            isoDate: item.editionDateIsoStr
        }));

        const responseData = {
            data: mappedData,
            pagination: {
                total: totalCount,
                offset,
                limit,
                hasMore: offset + limit < totalCount
            }
        };

        // Cache the response
        copertineCache.set(offset, {
            data: mappedData,
            pagination: responseData.pagination,
            timestamp: Date.now()
        });

        return NextResponse.json(responseData);
    } catch (error) {
        console.error('Error fetching data from Weaviate:', error);
        return NextResponse.json(
            { error: 'Failed to fetch data' },
            { status: 500 }
        );
    }
}