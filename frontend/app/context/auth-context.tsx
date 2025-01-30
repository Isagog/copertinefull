'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { API } from '@app/lib/config/constants';
import type { User, AuthContextType } from '@app/types/auth';

export const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {},
  logout: async () => {},
  isAuthenticated: false,
  token: null,
  isInitialized: false,
});

function useAuthState() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const router = useRouter();

  const fetchUser = async (authToken: string) => {
    try {
      console.log('[AuthProvider] Fetching user data with token length:', authToken?.length);
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Accept': 'application/json',
        },
        credentials: 'include',
      });
      
      console.log('[AuthProvider] /me response status:', response.status);
      const responseText = await response.text();
      console.log('[AuthProvider] /me response text:', responseText);

      if (response.ok) {
        try {
          const userData = JSON.parse(responseText);
          console.log('[AuthProvider] User data parsed:', userData);
          setUser(userData);
        } catch (parseError) {
          console.error('[AuthProvider] Failed to parse user data:', parseError);
          await handleLogout();
        }
      } else {
        console.error('[AuthProvider] Failed to fetch user:', responseText);
        // If token is invalid, logout
        await handleLogout();
      }
    } catch (error) {
      console.error('[AuthProvider] Network error fetching user:', error);
      await handleLogout();
    }
  };

  const handleLogout = async () => {
    if (typeof window === 'undefined') {
      console.log('[AuthProvider] Server-side, skipping logout');
      return;
    }
    
    console.log('[AuthProvider] Starting logout process');
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    
    try {
      console.log('[AuthProvider] Removing token cookie');
      const response = await fetch('/api/auth/remove-token', {
        method: 'POST',
        credentials: 'include',
      });
      
      console.log('[AuthProvider] Remove token response:', response.status);
      
      console.log('[AuthProvider] Redirecting to login page');
      window.location.href = '/copertine/auth/login';
    } catch (error) {
      console.error('[AuthProvider] Error during logout:', error);
    }
  };

  const login = async (newToken: string) => {
    if (typeof window === 'undefined') {
      console.log('[AuthProvider] Server-side, skipping login');
      return;
    }
    
    try {
      console.log('[AuthProvider] Starting login with token length:', newToken?.length);
      
      // First set the token in the auth context and localStorage
      console.log('[AuthProvider] Updating local state');
      setToken(newToken);
      localStorage.setItem('token', newToken);

      // Then set the HTTP-only cookie via API
      console.log('[AuthProvider] Setting token cookie');
      const cookieResponse = await fetch('/api/auth/set-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ token: newToken }),
      });
      
      if (!cookieResponse.ok) {
        throw new Error('Failed to set token cookie');
      }
      
      console.log('[AuthProvider] Set token cookie response:', cookieResponse.status);
      
      // Finally fetch user data
      console.log('[AuthProvider] Fetching user data');
      await fetchUser(newToken);

      // Force a page reload to ensure middleware picks up the new cookie
      console.log('[AuthProvider] Reloading page to apply new auth state');
      window.location.href = '/copertine';
    } catch (error) {
      console.error('[AuthProvider] Error during login:', error);
      await handleLogout();
    }
  };

  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      if (typeof window === 'undefined') {
        console.log('[AuthProvider] Server-side, skipping initialization');
        if (mounted) setIsInitialized(true);
        return;
      }

      try {
        console.log('[AuthProvider] Starting auth initialization');
        const storedToken = localStorage.getItem('token');
        if (storedToken && mounted) {
          console.log('[AuthProvider] Found stored token');
          setToken(storedToken);
          await fetchUser(storedToken);
        } else {
          console.log('[AuthProvider] No stored token found');
        }
      } catch (error) {
        console.error('[AuthProvider] Error initializing auth:', error);
        if (mounted) await handleLogout();
      } finally {
        if (mounted) {
          console.log('[AuthProvider] Setting initialized state');
          setIsInitialized(true);
        }
      }
    };

    initialize();

    return () => {
      mounted = false;
    };
  }, []);

  return {
    user,
    token,
    isInitialized,
    login,
    logout: handleLogout,
    isAuthenticated: !!user,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  console.log('[AuthProvider] Rendering provider');
  const auth = useAuthState();

  console.log('[AuthProvider] Current auth state:', {
    isInitialized: auth.isInitialized,
    hasToken: !!auth.token,
    isAuthenticated: auth.isAuthenticated
  });

  return (
    <AuthContext.Provider value={auth}>
      {!auth.isInitialized ? (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
