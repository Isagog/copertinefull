'use client';

import { useAuth } from '@/app/context/auth-context';
import { withProtectedRoute } from '@/app/components/auth/ProtectedRoute';

function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white shadow rounded-lg p-6">
          <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
          <div className="space-y-4">
            <div className="border-b pb-4">
              <h2 className="text-lg font-semibold mb-2">User Information</h2>
              <p className="text-gray-600">Email: {user?.email}</p>
              <p className="text-gray-600">
                Account Status: {user?.is_active ? 'Verified' : 'Pending Verification'}
              </p>
              <p className="text-gray-600">
                Last Login: {user?.last_login ? new Date(user.last_login).toLocaleString() : 'N/A'}
              </p>
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-2">Protected Content</h2>
              <p className="text-gray-600">
                This is a protected page that can only be accessed by authenticated users
                with verified email addresses from manifesto.it or isagog.com domains.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default withProtectedRoute(DashboardPage);
