// app/api/search/route.ts
import { NextRequest, NextResponse } from 'next/server';
import type { SearchRequest, SearchResponse } from '@/app/types/search';
import { API } from '@/app/lib/config/constants';

export async function POST(request: NextRequest) {
  try {
    const searchParams: SearchRequest = await request.json();
    console.log('Search request received:', searchParams);
    
    // Create URL with search parameters
    const backendUrl = process.env.FASTAPI_URL || API.FASTAPI_URL;
    console.log('Using backend URL:', backendUrl);
    
    const url = new URL(`${backendUrl}/api/v1/copertine`);
    url.searchParams.append('search', searchParams.query);
    url.searchParams.append('mode', searchParams.mode);
    
    console.log('Calling FastAPI URL:', url.toString());
    console.log('Environment:', {
      NODE_ENV: process.env.NODE_ENV,
      FASTAPI_URL: API.FASTAPI_URL,
      NEXT_PUBLIC_FASTAPI_URL: process.env.NEXT_PUBLIC_FASTAPI_URL
    });

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        cache: 'no-store',
        next: { revalidate: 0 },
      });

      console.log('FastAPI response status:', response.status);
      console.log('FastAPI response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('FastAPI error response:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText
        });
        throw new Error(`FastAPI request failed: ${response.status} ${response.statusText}\n${errorText}`);
      }

      // Check content type
      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        console.error('Unexpected content type:', contentType);
        const textResponse = await response.text();
        console.error('Raw non-JSON response:', textResponse);
        throw new Error(`Unexpected content type: ${contentType}`);
      }

      const data = await response.json();
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
      const errorMessage = `Failed to fetch from FastAPI backend at ${API.FASTAPI_URL}. ${error instanceof Error ? error.message : 'Unknown error'}`;
      console.error('Search API error details:', {
        error,
        message: errorMessage,
        url: url.toString()
      });
      return NextResponse.json({ error: errorMessage }, { status: 500 });
    }
  } catch (err) {
    console.error('Error in search API route:', err);
    return NextResponse.json(
      { error: 'Internal server error while processing search request' },
      { status: 500 }
    );
  }
}
