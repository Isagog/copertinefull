/**
 * Path: frontend/app/api/auth/reset-password-request/route.ts
 * Description: Proxy route handler for password reset requests
 * Forwards password reset requests to the backend microservice
 */

import { NextResponse } from 'next/server';
import { API } from '@/app/lib/config/constants';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${API.BACKEND_URL}/auth/reset-password-request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Password reset request proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
