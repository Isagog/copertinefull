/**
 * Path: frontend/app/components/auth/LoginForm.tsx
 * Description: Login form component with email/password authentication
 * Client component that handles login form submission and redirects
 */

'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@app/hooks/useAuth';
import Link from 'next/link';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      console.log('[LoginForm] Submitting login form');
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      console.log('[LoginForm] Login response status:', response.status);
      const responseText = await response.text();
      console.log('[LoginForm] Login response:', responseText);

      if (!response.ok) {
        try {
          const data = JSON.parse(responseText);
          throw new Error(data.detail || 'Failed to sign in');
        } catch (parseError) {
          throw new Error(responseText || 'Failed to sign in');
        }
      }

      try {
        const data = JSON.parse(responseText);
        console.log('[LoginForm] Successfully parsed response');
        
        console.log('[LoginForm] Setting auth token');
        await login(data.access_token);
        
        // Get callback URL from query parameters
        const callbackUrl = searchParams.get('callbackUrl');
        console.log('[LoginForm] Callback URL:', callbackUrl);

        // Redirect to callback URL or default page
        const redirectUrl = callbackUrl ? decodeURIComponent(callbackUrl) : '/copertine';
        console.log('[LoginForm] Redirecting to:', redirectUrl);
        router.push(redirectUrl);
      } catch (parseError) {
        console.error('[LoginForm] Failed to parse response:', parseError);
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('[LoginForm] Login error:', err);
      setError(err instanceof Error ? err.message : 'Failed to sign in. Please check your credentials and try again.');
      console.error('[LoginForm] Login error details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
          Sign in to your account
        </h1>
        <p className="mt-2 text-sm text-center text-gray-600 dark:text-gray-400">
          Or{' '}
          <Link
            href="/copertine/auth/register"
            className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
          >
            create a new account
          </Link>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-3 text-sm text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/50 rounded-md">
            {error}
          </div>
        )}

        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm">
            <Link
              href="/copertine/auth/reset-password"
              className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Forgot your password?
            </Link>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
