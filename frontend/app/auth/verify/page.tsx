'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

export default function VerifyEmailPage() {
  const [status, setStatus] = useState<'waiting' | 'verifying' | 'success' | 'error'>('waiting');
  const [message, setMessage] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    
    // If no token, just show the waiting message
    if (!token) {
      setStatus('waiting');
      setMessage('Please check your email for the verification link.');
      return;
    }

    // If we have a token, attempt verification
    const verifyEmail = async () => {
      setStatus('verifying');
      try {
        const response = await fetch('http://localhost:8000/auth/verify-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ token }),
        });

        const data = await response.json();

        if (response.ok) {
          setStatus('success');
          setMessage('Email verified successfully! You will be redirected to login.');
          setTimeout(() => {
            router.push('/auth/login');
          }, 3000);
        } else {
          setStatus('error');
          setMessage(data.detail || 'Verification failed');
        }
      } catch (error) {
        setStatus('error');
        setMessage('An error occurred during verification');
      }
    };

    verifyEmail();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          {status === 'waiting' && (
            <>
              <h2 className="text-2xl font-semibold text-gray-900">Email Verification Required</h2>
              <p className="mt-2 text-gray-600">
                Please check your email for the verification link. Click the link in the email to verify your account.
              </p>
              <div className="mt-4">
                <Link
                  href="/auth/login"
                  className="text-blue-600 hover:text-blue-500"
                >
                  Return to login
                </Link>
              </div>
            </>
          )}
          
          {status === 'verifying' && (
            <>
              <h2 className="text-2xl font-semibold text-gray-900">Verifying your email...</h2>
              <p className="mt-2 text-gray-600">Please wait while we verify your email address.</p>
            </>
          )}
          
          {status === 'success' && (
            <>
              <h2 className="text-2xl font-semibold text-green-600">Email Verified!</h2>
              <p className="mt-2 text-gray-600">{message}</p>
              <Link
                href="/auth/login"
                className="mt-4 inline-block text-blue-600 hover:text-blue-500"
              >
                Go to login
              </Link>
            </>
          )}
          
          {status === 'error' && (
            <>
              <h2 className="text-2xl font-semibold text-red-600">Verification Failed</h2>
              <p className="mt-2 text-gray-600">{message}</p>
              <Link
                href="/auth/login"
                className="mt-4 inline-block text-blue-600 hover:text-blue-500"
              >
                Return to login
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
