// app/api/search/route.ts
import { NextRequest, NextResponse } from 'next/server';
import type { SearchRequest, SearchResponse } from '@/app/types/search';

export async function POST(request: NextRequest) {
  try {
    const searchParams: SearchRequest = await request.json();

    // Get Weaviate connection details from environment
    const scheme = process.env.WEAVIATE_SCHEME || 'http';
    const host = process.env.WEAVIATE_HOST || 'localhost:8080';
    const collection = process.env.WEAVIATE_COLLECTION || 'Copertine';

    try {
      // TODO: Implement actual search logic with Weaviate client
      const response = await fetch(`${scheme}://${host}/v1/${collection}/objects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchParams.query,
          style: searchParams.style
        }),
      });

      if (!response.ok) {
        throw new Error('Search request failed');
      }

      const data = await response.json();
      
      const searchResponse: SearchResponse = {
        results: data.results,
        total: data.total
      };

      return NextResponse.json(searchResponse);
      
    } catch (error) {
      const errorMessage = `Failed to connect to Weaviate at ${scheme}://${host} (Collection: ${collection}). ${error instanceof Error ? error.message : 'Unknown error'}`;
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

// Optionally add a GET handler if you need it
export async function GET(request: NextRequest) {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405 }
  );
}