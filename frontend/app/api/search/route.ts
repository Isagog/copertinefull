// app/api/search/route.ts
import { NextRequest, NextResponse } from 'next/server';
import type { SearchRequest, SearchResponse } from '@/app/types/search';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8008';

export async function POST(request: NextRequest) {
  try {
    const searchParams: SearchRequest = await request.json();
    console.log('Search request received:', searchParams);
    
    // Create URL with search parameters
    const url = new URL(`${FASTAPI_URL}/api/v1/copertine`);
    url.searchParams.append('search', searchParams.query);
    url.searchParams.append('mode', searchParams.mode);
    
    console.log('Calling FastAPI URL:', url.toString());

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
        next: { revalidate: 0 },
      });

      const data = await response.json();
      
      // Log the raw response
      console.log('Raw FastAPI response:', data);

      if (!response.ok) {
        console.error('FastAPI request failed:', response.status, response.statusText);
        throw new Error(`Search request failed: ${response.statusText}`);
      }

      if (!Array.isArray(data)) {
        console.error('Unexpected response format:', data);
        throw new Error('Unexpected response format from search service');
      }

      console.log('FastAPI response received:', {
        resultCount: data.length,
        sampleResults: data.slice(0, 2)
      });

      // If we get an empty array, we should return it as valid empty results
      // rather than falling back to the full list
      const searchResponse: SearchResponse = {
        results: data,
        total: data.length
      };

      return NextResponse.json(searchResponse);
      
    } catch (error) {
      const errorMessage = `Failed to fetch from FastAPI backend at ${FASTAPI_URL}. ${error instanceof Error ? error.message : 'Unknown error'}`;
      console.error('Search API error details:', {
        error,
        message: errorMessage,
        url: url.toString()
      });
      return NextResponse.json({ error: errorMessage }, { status: 500 });
    }
  } catch (error) {
    console.error('Error in search API route:', error);
    return NextResponse.json(
      { error: 'Internal server error while processing search request' },
      { status: 500 }
    );
  }
}
