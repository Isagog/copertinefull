// app/api/copertine/route.tsx
import { NextRequest, NextResponse } from 'next/server';
import { copertineCache } from '@app/lib/cache';
import { FASTAPI_URL } from '@/app/lib/constants';

export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0')

        // Get Weaviate connection details from environment
        const scheme = process.env.WEAVIATE_SCHEME || 'http';
        const host = process.env.WEAVIATE_HOST || 'localhost:8080';
        const collection = process.env.WEAVIATE_COLLECTION || 'Copertine';

        try {
            const result = await copertineCache.get(offset);
            
            if (!result) {
                throw new Error('No data received from cache');
            }

            return NextResponse.json({
                data: result.data,
                pagination: result.pagination,
                cached: true
            });
        } catch (error) {
            const errorMessage = `Failed to connect to Weaviate at ${scheme}://${host} (Collection: ${collection}). ${error instanceof Error ? error.message : 'Unknown error'}`;
            console.error(errorMessage);
            return NextResponse.json({ error: errorMessage }, { status: 500 });
        }
    } catch (error) {
        console.error('Error in API route:', error);
        return NextResponse.json(
            { error: 'Internal server error while processing request' },
            { status: 500 }
        );
    }
}
