/**
 * Path: frontend/app/api/auth/register/route.ts
 * Description: Proxy route handler for registration
 * Forwards registration requests to the backend microservice
 */

import { NextResponse } from 'next/server';
import { API } from '@/app/lib/config/constants';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${API.BACKEND_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
      credentials: 'include',
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Registration proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
