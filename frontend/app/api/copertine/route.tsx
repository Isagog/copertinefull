// app/api/copertine/route.tsx
import { NextRequest, NextResponse } from 'next/server';
import { getWeaviateClient } from '@app/lib/weaviate';
import { CopertineEntry } from '@app/types/copertine';
import { WeaviateItem, WeaviateGetResponse } from '@app/types/weaviate';

export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0');
        const limit = parseInt(searchParams.get('limit') || '50');

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
            isoDate: item.editionDateIsoStr // Adding this for proper sorting
        }));

        return NextResponse.json({
            data: mappedData,
            pagination: {
                total: totalCount,
                offset,
                limit,
                hasMore: offset + limit < totalCount
            }
        });
    } catch (error) {
        console.error('Error fetching data from Weaviate:', error);
        return NextResponse.json(
            { error: 'Failed to fetch data' },
            { status: 500 }
        );
    }
}