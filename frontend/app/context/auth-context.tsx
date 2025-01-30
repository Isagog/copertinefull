'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  is_active: boolean;
  last_login: string | null;
}

interface AuthContextType {
  user: User | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  token: string | null;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
  token: null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    // Check for token in localStorage on mount
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsInitialized(true);
    }
  }, []);

  const fetchUser = async (authToken: string) => {
    try {
      const response = await fetch('http://localhost:8000/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Accept': 'application/json',
        },
        credentials: 'include',
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // If token is invalid, logout
        await handleLogout();
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      await handleLogout();
    } finally {
      setIsInitialized(true);
    }
  };

  const handleLogout = async () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    
    try {
      // Remove token cookie
      await fetch('/api/auth/remove-token', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Error removing token:', error);
    }
  };

  const login = async (newToken: string) => {
    try {
      // Set token in HTTP-only cookie
      await fetch('/api/auth/set-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ token: newToken }),
      });

      setToken(newToken);
      localStorage.setItem('token', newToken);
      await fetchUser(newToken);
    } catch (error) {
      console.error('Error setting token:', error);
      await handleLogout();
    }
  };

  // Don't render children until we've checked authentication
  if (!isInitialized) {
    return null;
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout: handleLogout,
        isAuthenticated: !!user,
        token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
