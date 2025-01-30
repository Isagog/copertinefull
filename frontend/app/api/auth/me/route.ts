/**
 * Path: frontend/app/api/auth/me/route.ts
 * Description: Proxy route handler for getting current user data
 * Forwards user data requests to the backend microservice
 */

import { NextResponse } from 'next/server';
import { API } from '@app/lib/config/constants';

export async function GET(request: Request) {
  console.log('[/api/auth/me] Handling request');
  
  try {
    // Get the authorization header from the incoming request
    const authHeader = request.headers.get('Authorization');
    console.log('[/api/auth/me] Auth header present:', !!authHeader);
    
    if (!authHeader) {
      console.log('[/api/auth/me] Missing auth header');
      return NextResponse.json(
        { error: 'Authorization header is required' },
        { status: 401 }
      );
    }

    const url = new URL('/auth/me', API.BACKEND_URL).toString();
    console.log('[/api/auth/me] Forwarding request to backend:', url);
    console.log('[/api/auth/me] Auth header:', authHeader);
    
    const response = await fetch(url, {
      headers: {
        'Authorization': authHeader,
        'Accept': 'application/json',
      },
      credentials: 'include',
    });

    console.log('[/api/auth/me] Backend response status:', response.status);
    const responseText = await response.text();
    console.log('[/api/auth/me] Backend response text:', responseText);

    try {
      const data = JSON.parse(responseText);
      console.log('[/api/auth/me] Successfully parsed response');
      return NextResponse.json(data, { status: response.status });
    } catch (parseError) {
      console.error('[/api/auth/me] Failed to parse response:', parseError);
      return NextResponse.json(
        { error: 'Invalid response from backend' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('[/api/auth/me] Request error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
