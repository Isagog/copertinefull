/**
 * Path: frontend/app/auth/verify/page.tsx
 * Description: Email verification page component
 * Handles email verification token validation and user feedback
 */

import { Metadata } from 'next';
import EmailVerification from '@/app/components/auth/EmailVerification';

export const metadata: Metadata = {
  title: 'Verify Email - Il Manifesto',
  description: 'Verify your email address for Il Manifesto',
};

export default function VerifyPage({
  searchParams,
}: {
  searchParams: { token?: string };
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-md mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <EmailVerification token={searchParams.token} />
      </div>
    </div>
  );
}
