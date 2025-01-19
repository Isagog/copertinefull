// app/api/weaviate/route.ts
import { NextRequest } from 'next/server';
import { getWeaviateClient } from '@/app/lib/services/weaviate';

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

        return Response.json({
            data: result.data,
            count: countResult.data.Aggregate.Copertine[0].meta.count
        });
    } catch (error) {
        console.error('Weaviate query error:', error);
        return Response.json({ error: 'Failed to fetch data' }, { status: 500 });
    }
}