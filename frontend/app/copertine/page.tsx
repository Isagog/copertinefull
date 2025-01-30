import { Suspense } from 'react';
import CopertineList from './components/CopertineList';
import Loading from './loading';

export const metadata = {
  title: 'Copertine - Il Manifesto',
  description: 'Browse Il Manifesto covers archive',
};

export default function CopertinePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Suspense fallback={<Loading />}>
          <CopertineList />
        </Suspense>
      </div>
    </div>
  );
}
