import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { token } = await request.json();
    
    const response = NextResponse.json({ success: true });
    
    // Set the token in an HTTP-only cookie
    response.cookies.set('token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      // Expire in 30 minutes
      maxAge: 30 * 60
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to set token' },
      { status: 500 }
    );
  }
}
