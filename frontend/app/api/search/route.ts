// app/api/search/route.ts
import { NextRequest, NextResponse } from 'next/server';
import type { SearchRequest, SearchResponse } from '@/app/types/search';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const searchParams: SearchRequest = await request.json();
    
    // Create URL with search parameters
    const url = new URL(`${FASTAPI_URL}/api/v1/copertine`);
    url.searchParams.append('search', searchParams.query);
    url.searchParams.append('mode', searchParams.mode);  // Using correct property name from type

    try {
      // Call FastAPI endpoint with query parameters
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
        next: { revalidate: 0 },
      });

      if (!response.ok) {
        throw new Error(`Search request failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Transform response to match SearchResponse type
      const searchResponse: SearchResponse = {
        results: data,
        total: data.length
      };

      return NextResponse.json(searchResponse);
      
    } catch (error) {
      const errorMessage = `Failed to fetch from FastAPI backend at ${FASTAPI_URL}. ${error instanceof Error ? error.message : 'Unknown error'}`;
      console.error(errorMessage);
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