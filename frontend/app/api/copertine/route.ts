import { NextRequest, NextResponse } from 'next/server';
import { copertineCache } from '@/app/lib/services/cache';
import { API } from '@/app/lib/config/constants';
import weaviate from 'weaviate-ts-client';

export const revalidate = 0;

export async function GET(request: NextRequest) {
    try {
        console.log('API route hit:', request.url);
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0');
        const limit = parseInt(searchParams.get('limit') || '3600');
        const query = searchParams.get('q');

        // If there's a search query, forward to FastAPI
        if (query) {
            const backendUrl = process.env.FASTAPI_URL || API.FASTAPI_URL;
            console.log('Using backend URL:', backendUrl);
            console.log('Environment:', {
                NODE_ENV: process.env.NODE_ENV,
                FASTAPI_URL: process.env.FASTAPI_URL,
                BACKEND_URL: backendUrl
            });
            
            console.log('Forwarding search to FastAPI:', `${backendUrl}/search?q=${encodeURIComponent(query)}`);
            const searchResponse = await fetch(`${backendUrl}/search?q=${encodeURIComponent(query)}`, {
                headers: {
                    'Accept': 'application/json'
                }
            });

            console.log('FastAPI response status:', searchResponse.status);
            console.log('FastAPI response headers:', Object.fromEntries(searchResponse.headers.entries()));
            
            // Check content type
            const contentType = searchResponse.headers.get('content-type');
            if (!contentType?.includes('application/json')) {
                console.error('Unexpected content type:', contentType);
                const textResponse = await searchResponse.text();
                console.error('Raw non-JSON response:', textResponse);
                throw new Error(`Unexpected content type: ${contentType}`);
            }

            if (!searchResponse.ok) {
                const errorText = await searchResponse.text();
                console.error('Search API failed:', searchResponse.status, errorText);
                throw new Error(`Search API request failed: ${searchResponse.status} ${errorText}`);
            }

            const searchResults = await searchResponse.json();
            return NextResponse.json(searchResults);
        }

        // Otherwise, get from cache/Weaviate
        const scheme = process.env.WEAVIATE_SCHEME || 'http';
        const host = process.env.WEAVIATE_HOST || 'localhost:8080';
        const collection = process.env.WEAVIATE_COLLECTION || 'Copertine';

        try {
            // Try to get from cache first
            const cachedResult = await copertineCache.get(offset);
            if (cachedResult) {
                console.log('Returning cached result');
                return NextResponse.json({
                    data: cachedResult.data,
                    pagination: cachedResult.pagination,
                    cached: true
                });
            }

            // If not in cache, query Weaviate directly
            const client = weaviate.client({
                scheme: scheme,
                host: host,
            });

            // Get total count first
            const countResult = await client.graphql
                .aggregate()
                .withClassName(collection)
                .withFields('meta { count }')
                .do();

            const totalItems = countResult.data.Aggregate.Copertine[0].meta.count;

            // Then get the actual data
            const result = await client.graphql
                .get()
                .withClassName(collection)
                .withFields('filename extracted_caption kickerStr date isoDate')
                .withLimit(limit)
                .withOffset(offset)
                .withSort([{ path: ['isoDate'], order: 'desc' }])
                .do();

            if (!result.data.Get[collection]) {
                throw new Error('No data received from Weaviate');
            }

            const copertineData = result.data.Get[collection];

            // Structure the response
            const response = {
                data: copertineData,
                pagination: {
                    total: totalItems,
                    offset: offset,
                    limit: limit,
                    hasMore: offset + limit < totalItems
                },
                cached: false
            };

            // Store in cache for future requests
            await copertineCache.set(offset, {
                ...response,
                timestamp: Date.now()
            });

            return NextResponse.json(response);

        } catch (error) {
            console.error('Weaviate or cache error:', error);
            const errorMessage = `Failed to connect to Weaviate at ${scheme}://${host} (Collection: ${collection}). ${error instanceof Error ? error.message : 'Unknown error'}`;
            return NextResponse.json({ 
                error: errorMessage,
                details: error instanceof Error ? error.stack : undefined
            }, { status: 500 });
        }
    } catch (error) {
        console.error('API route error:', error);
        return NextResponse.json(
            { 
                error: 'Internal server error while processing request',
                details: error instanceof Error ? error.message : 'Unknown error'
            },
            { status: 500 }
        );
    }
}
