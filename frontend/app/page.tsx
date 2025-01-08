// app/page.tsx
'use client';

import React from 'react';
import { ArrowUpDown } from 'lucide-react';
import CopertinaCard from './components/copertina/CopertinaCard';
import type { CopertineEntry } from './types/copertine';

type SortField = 'date' | 'extracted_caption';
type SortDirection = 'asc' | 'desc';

export default function Home() {
  const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
  const [sortField, setSortField] = React.useState<SortField>('date');
  const [sortDirection, setSortDirection] = React.useState<SortDirection>('desc');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchCopertine = React.useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/copertine');
      if (!response.ok) throw new Error('Failed to fetch data');
      const data = await response.json();
      setCopertine(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchCopertine();
  }, [fetchCopertine]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(current => current === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedCopertine = React.useMemo(() => {
    return [...copertine].sort((a, b) => {
      const modifier = sortDirection === 'asc' ? 1 : -1;
      if (sortField === 'date') {
        return (new Date(a.date) > new Date(b.date) ? 1 : -1) * modifier;
      }
      return (a[sortField].localeCompare(b[sortField])) * modifier;
    });
  }, [copertine, sortField, sortDirection]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Search Section (Placeholder) */}
      <section className="border-b border-gray-200 dark:border-gray-800">
        <div className="container mx-auto px-4 py-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
            <p className="text-center text-gray-600 dark:text-gray-400">
              Sezione di ricerca in sviluppo
            </p>
          </div>
        </div>
      </section>

      {/* Results Section */}
      <section className="container mx-auto px-4 py-6">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}
        
        {isLoading ? (
          <div className="flex justify-center items-center min-h-[400px]">
            <div className="text-lg text-gray-600 dark:text-gray-400">Caricamento...</div>
          </div>
        ) : (
          <div>
            {/* Sort Controls */}
            <div className="flex gap-4 mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
              <button 
                onClick={() => handleSort('date')}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Data {sortField === 'date' && <ArrowUpDown className="h-4 w-4" />}
              </button>
              <button 
                onClick={() => handleSort('extracted_caption')}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Didascalia {sortField === 'extracted_caption' && <ArrowUpDown className="h-4 w-4" />}
              </button>
            </div>

            {/* Cards Grid */}
            <div className="space-y-6">
              {sortedCopertine.map((copertina) => (
                <CopertinaCard key={copertina.filename} copertina={copertina} />
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}