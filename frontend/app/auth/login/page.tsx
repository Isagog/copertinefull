/**
 * Path: frontend/app/auth/login/page.tsx
 * Description: Login page component
 * Server component that renders the login form
 */

import LoginForm from '@app/components/auth/LoginForm';

export const metadata = {
  title: 'Login - Il Manifesto',
  description: 'Sign in to your Il Manifesto account',
};

export default function LoginPage() {
  console.log('[LoginPage] Rendering login page');
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <LoginForm />
      </div>
    </div>
  );
}
