// Path: frontend/middleware.ts
// Description: Global middleware for handling authentication and routing

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// List of public paths that don't require authentication
const publicPaths = [
  '/copertine/auth/login',
  '/copertine/auth/register',
  '/copertine/auth/verify',
  '/copertine/auth/reset-password',
  '/copertine/auth/reset-password/confirm',
];

// List of paths that should bypass the middleware completely
const bypassPaths = [
  '/_next',
  '/favicon.ico',
  '/api',
  '/copertine/api',  // Add this to bypass middleware for API routes with basePath
  '/public',
  '/manifesto_logo.svg',
];

// Debug middleware configuration
console.log('[middleware] Configuration:', {
  bypassPaths,
  publicPaths,
  matcher: '/((?!_next/static|_next/image|favicon.ico).*)'
});

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Bypass middleware for static assets and API routes
  const shouldBypass = bypassPaths.some(path => pathname.startsWith(path));
  if (shouldBypass) {
    console.log('[middleware] Bypassing middleware for:', pathname);
    return NextResponse.next();
  }

  // Check for auth token
  const token = request.cookies.get('token')?.value;

  // Log all requests
  console.log('[middleware] Request:', {
    pathname,
    hasToken: !!token,
    isPublicPath: publicPaths.includes(pathname),
    isBypassPath: bypassPaths.some(path => pathname.startsWith(path))
  });

  // Handle root path and /copertine
  if (pathname === '/' || pathname === '/copertine') {
    console.log('[middleware] Handling root or /copertine path:', pathname);
    console.log('[middleware] Token present:', !!token);
    
    if (!token) {
      const loginUrl = new URL('/copertine/auth/login', request.url);
      console.log('[middleware] No token, redirecting to:', loginUrl.toString());
      return NextResponse.redirect(loginUrl);
    }
    if (pathname === '/') {
      const copertineUrl = new URL('/copertine', request.url);
      console.log('[middleware] Root path, redirecting to:', copertineUrl.toString());
      return NextResponse.redirect(copertineUrl);
    }
    console.log('[middleware] Proceeding with authenticated request');
    return NextResponse.next();
  }

  // If it's a public path
  if (publicPaths.includes(pathname)) {
    console.log('[middleware] Public path:', pathname);
    // If user is authenticated and trying to access auth pages, redirect to home
    if (token) {
      const homeUrl = new URL('/copertine', request.url);
      console.log('[middleware] Authenticated user on public path, redirecting to:', homeUrl.toString());
      return NextResponse.redirect(homeUrl);
    }
    console.log('[middleware] Allowing access to public path');
    return NextResponse.next();
  }

  // If no token and not on a public path, redirect to login
  if (!token) {
    console.log('[middleware] No token on protected path:', pathname);
    const loginUrl = new URL('/copertine/auth/login', request.url);
    // Store the attempted URL for redirect after login
    if (!pathname.startsWith('/copertine/auth/')) {
      loginUrl.searchParams.set('callbackUrl', pathname);
    }
    console.log('[middleware] Redirecting to login with callback:', loginUrl.toString());
    return NextResponse.redirect(loginUrl);
  }

  console.log('[middleware] Proceeding with request:', pathname);
  return NextResponse.next();
}

// Configure middleware to run on specific paths
export const config = {
  matcher: [
    /*
     * Match all paths except static assets
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
