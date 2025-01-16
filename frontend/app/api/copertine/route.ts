// app/api/copertine/route.tsx
import { NextRequest, NextResponse } from 'next/server';
import { copertineCache } from '@/app/lib/services/cache';
import { API } from '@/app/lib/config/constants';

export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0');
        const query = searchParams.get('q');

        // If there's a search query, forward to FastAPI
        if (query) {
            const searchResponse = await fetch(`${API.FASTAPI_URL}/search?q=${encodeURIComponent(query)}`);
            if (!searchResponse.ok) {
                throw new Error('Search API request failed');
            }
            const searchResults = await searchResponse.json();
            return NextResponse.json(searchResults);
        }

        // Otherwise, get from cache/Weaviate
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