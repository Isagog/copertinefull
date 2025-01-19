// app/api/copertine/route.ts
import { NextRequest } from 'next/server';
import { getWeaviateClient } from '@/app/lib/services/weaviate';

// Add interface for Weaviate response item
interface WeaviateCopertineItem {
    captionStr: string;
    editionDateIsoStr: string;
    editionId: string;
    editionImageFnStr: string;
    kickerStr: string;
    testataName: string;
}

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const offset = parseInt(searchParams.get('offset') || '0');
    const limit = parseInt(searchParams.get('limit') || '30');

    try {
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
            .do();

        const countResult = await client.graphql
            .aggregate()
            .withClassName('Copertine')
            .withFields('meta { count }')
            .do();

        // Transform the data for the frontend with proper typing
        const mappedData = result.data.Get.Copertine.map((item: WeaviateCopertineItem) => ({
            extracted_caption: item.captionStr,
            kickerStr: item.kickerStr,
            date: new Date(item.editionDateIsoStr).toLocaleDateString('it-IT'),
            filename: item.editionImageFnStr,
            isoDate: item.editionDateIsoStr
        }));

        return Response.json({
            data: mappedData,
            pagination: {
                total: countResult.data.Aggregate.Copertine[0].meta.count,
                offset,
                limit,
                hasMore: offset + limit < countResult.data.Aggregate.Copertine[0].meta.count
            }
        });
    } catch (error) {
        console.error('Failed to connect to Weaviate:', error);
        return Response.json({ error: 'Failed to fetch data' }, { status: 500 });
    }
}