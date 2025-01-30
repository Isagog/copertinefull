import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

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
      maxAge: 30 * 60 // 30 minutes
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to set token' },
      { status: 500 }
    );
  }
}
