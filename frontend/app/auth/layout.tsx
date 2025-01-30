/**
 * Path: frontend/app/auth/layout.tsx
 * Description: Layout component for authentication pages
 * Handles auth state and redirects for login, register, and password reset pages
 */

import { Metadata } from 'next';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Authentication - Il Manifesto',
  description: 'Sign in or register for Il Manifesto',
};

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const hasToken = cookieStore.has('token');

  console.log('[AuthLayout] Rendering with token:', hasToken);

  // If user is already authenticated, redirect to main page
  if (hasToken) {
    console.log('[AuthLayout] User has token, redirecting to /copertine');
    redirect('/copertine');
  }

  console.log('[AuthLayout] Rendering auth layout');
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" suppressHydrationWarning>
      <div className="max-w-md mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link href="/copertine" className="inline-block">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
              Il Manifesto
            </h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Archivio storico delle copertine
            </p>
          </Link>
        </div>
        {children}
      </div>
    </div>
  );
}
