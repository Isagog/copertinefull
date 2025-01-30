/**
 * Path: frontend/app/api/auth/verify/route.ts
 * Description: Proxy route handler for email verification
 * Forwards verification requests to the backend microservice
 */

import { NextResponse } from 'next/server';
import { API } from '@/app/lib/config/constants';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${API.BACKEND_URL}/auth/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Email verification proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
