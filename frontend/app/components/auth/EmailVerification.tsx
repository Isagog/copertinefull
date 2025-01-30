/**
 * Path: frontend/app/components/auth/EmailVerification.tsx
 * Description: Email verification component
 * Client component that handles email verification token validation
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { API } from '@/app/lib/config/constants';

interface EmailVerificationProps {
  token?: string;
}

export default function EmailVerification({ token }: EmailVerificationProps) {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');
  const router = useRouter();

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link. Please check your email and try again.');
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch('/api/auth/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          throw new Error('Verification failed');
        }

        setStatus('success');
        setMessage('Email verified successfully! Redirecting to login...');
        
        // Redirect to login after successful verification
        setTimeout(() => {
          router.push('/copertine/auth/login');
        }, 2000);
      } catch (error) {
        setStatus('error');
        setMessage('Failed to verify email. Please try again or contact support.');
      }
    };

    verifyEmail();
  }, [token, router]);

  return (
    <div className="text-center">
      <h1 className="text-2xl font-bold mb-4">Email Verification</h1>
      <div
        className={`p-4 rounded-md ${
          status === 'loading'
            ? 'bg-blue-50 text-blue-700'
            : status === 'success'
            ? 'bg-green-50 text-green-700'
            : 'bg-red-50 text-red-700'
        }`}
      >
        <p>{message}</p>
      </div>
      {status === 'error' && (
        <button
          onClick={() => router.push('/copertine/auth/login')}
          className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Return to Login
        </button>
      )}
    </div>
  );
}
