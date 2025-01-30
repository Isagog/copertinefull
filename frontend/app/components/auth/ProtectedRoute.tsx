'use client';

import { useAuth } from '@/app/context/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, user, isInitialized } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Wait for auth to be initialized
    if (!isInitialized) return;

    console.log('ProtectedRoute auth state:', { isAuthenticated, user, pathname });

    // Remove /copertine prefix from pathname for storage
    const pathWithoutPrefix = pathname.replace('/copertine', '');
    
    if (!isAuthenticated) {
      // Store the attempted URL to redirect back after login
      sessionStorage.setItem('redirectAfterLogin', pathWithoutPrefix);
      console.log('Not authenticated, redirecting to login. Stored redirect:', pathWithoutPrefix);
      router.push('/copertine/auth/login');
      return;
    }

    if (user && !user.is_active) {
      // If user is not verified, redirect to verification page
      console.log('User not verified, redirecting to verify page');
      router.push('/copertine/auth/verify');
      return;
    }

    console.log('User authenticated and active:', { user });
  }, [isAuthenticated, user, router, pathname, isInitialized]);

  // Don't render anything until auth is initialized
  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Don't render if not authenticated
  if (!isAuthenticated || (user && !user.is_active)) {
    return null;
  }

  return <>{children}</>;
}

export function withProtectedRoute<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  return function WithProtectedRoute(props: P) {
    return (
      <ProtectedRoute>
        <WrappedComponent {...props} />
      </ProtectedRoute>
    );
  };
}
