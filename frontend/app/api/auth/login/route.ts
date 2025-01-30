/**
 * Path: frontend/app/api/auth/login/route.ts
 * Description: Proxy route handler for login
 * Forwards login requests to the backend microservice
 */

import { NextResponse } from 'next/server';
import { API } from '@app/lib/config/constants';

export async function POST(request: Request) {
  console.log('[/api/auth/login] Handling login request');
  console.log('[/api/auth/login] Backend URL:', API.BACKEND_URL);
  console.log('[/api/auth/login] Request headers:', {
    contentType: request.headers.get('content-type'),
    accept: request.headers.get('accept'),
  });
  
  try {
    const body = await request.json();
    console.log('[/api/auth/login] Request body:', { email: body.email });
    
    const url = new URL('/auth/login', API.BACKEND_URL).toString();
    console.log('[/api/auth/login] Forwarding to backend:', url);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      credentials: 'include',
    });

    console.log('[/api/auth/login] Backend response status:', response.status);
    const responseText = await response.text();
    console.log('[/api/auth/login] Backend response:', responseText);

    try {
      const data = JSON.parse(responseText);
      console.log('[/api/auth/login] Successfully parsed response:', { status: response.status });
      
      if (response.ok) {
        console.log('[/api/auth/login] Login successful');
        return NextResponse.json(data);
      } else {
        console.error('[/api/auth/login] Login failed:', data);
        return NextResponse.json(data, { status: response.status });
      }
    } catch (parseError) {
      console.error('[/api/auth/login] Failed to parse response:', parseError);
      return NextResponse.json(
        { error: 'Invalid response from backend' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('[/api/auth/login] Request error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
