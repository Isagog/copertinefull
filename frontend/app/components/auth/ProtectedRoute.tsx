'use client';

import { useAuth } from '@/app/context/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isAuthenticated) {
      // Store the attempted URL to redirect back after login
      sessionStorage.setItem('redirectAfterLogin', pathname);
      router.push('/auth/login');
    } else if (user && !user.is_active) {
      // If user is not verified, redirect to verification page
      router.push('/auth/verify');
    }
  }, [isAuthenticated, user, router, pathname]);

  // Show nothing while checking authentication
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
