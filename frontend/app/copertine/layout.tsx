/**
 * Path: frontend/app/copertine/layout.tsx
 * Description: Layout component for the main copertine section
 * Handles auth protection and layout structure for the copertine pages
 */

import { Metadata } from 'next';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import Header from '@/app/components/header/Header';

export const metadata: Metadata = {
  title: 'Copertine - Il Manifesto',
  description: 'Archivio storico delle copertine de Il Manifesto',
};

export default async function CopertineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const hasToken = cookieStore.has('token');

  if (!hasToken) {
    redirect('/copertine/auth/login');
  }

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </div>
    </>
  );
}
