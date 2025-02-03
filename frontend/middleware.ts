import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// Create a matcher for public routes
const publicRoutes = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)']);

// Export the middleware
export default clerkMiddleware((auth, req) => {
  if (!publicRoutes(req)) {
    return auth.protect();
  }
  return null;
});

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
    '/',
    '/(api|trpc)(.*)'
  ],
};